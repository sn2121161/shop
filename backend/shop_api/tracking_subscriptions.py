"""Durable, once-per-waybill registration and authenticated provider pushes."""
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .database import get_session
from .models import TrackingSubscription
from .security import active_user
from .tracking import TrackingInput, SUPPORTED_COURIERS, STATES

router = APIRouter(prefix="/api/tracking")


def sign(payload, key):
    return base64.b64encode(hashlib.md5((payload + key).encode()).hexdigest().encode()).decode()


def provider_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("/", "-"))
        return parsed.replace(tzinfo=ZoneInfo("Asia/Shanghai")) if parsed.tzinfo is None else parsed
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "物流时间格式无效") from None


def normalize(courier, waybill):
    waybill = re.sub(r"\s", "", waybill).upper()
    if courier not in SUPPORTED_COURIERS or not re.fullmatch(r"[A-Z0-9]{6,30}", waybill):
        raise HTTPException(400, "请选择已接入的快递公司，运单号应为 6–30 位字母或数字")
    return waybill


def serialize(row):
    traces = json.loads(row.traces)
    return {"courier": row.courier, "courierName": SUPPORTED_COURIERS[row.courier],
            "waybill": row.waybill, "status": row.status, "provider": "快递鸟",
            "traces": traces, "subscriptionStatus": row.subscription_status,
            "latestEventAt": traces[0]["time"] if traces else None,
            "updatedAt": row.updated_at, "lastPushAt": row.last_push_at,
            "cached": True, "queriedAt": datetime.now(timezone.utc).isoformat()}


class SubscriptionService:
    def __init__(self, business_id, api_key, request_type="", callback_url=""):
        if request_type not in {"", "1008", "8008"}:
            raise ValueError("KDNIAO_SUBSCRIBE_REQUEST_TYPE must be empty, 1008 or 8008")
        self.business_id, self.api_key = business_id, api_key
        self.request_type, self.callback_url = request_type, callback_url
        if request_type and not self.enabled:
            raise ValueError("启用物流订阅需同时配置 KDNIAO_EBUSINESS_ID、KDNIAO_API_KEY 和有效的 KDNIAO_CALLBACK_URL（http/https，路径为 /api/tracking/webhook）")

    @property
    def enabled(self):
        try:
            callback = urlparse(self.callback_url)
            valid_port = callback.port is None or 1 <= callback.port <= 65535
        except ValueError:
            return False
        return bool(self.business_id and self.api_key and self.request_type and
                    callback.scheme in {"http", "https"} and callback.hostname and valid_port and
                    not callback.username and not callback.password and
                    callback.path == "/api/tracking/webhook" and not callback.query and not callback.fragment)

    def register(self, session, courier, waybill):
        waybill = normalize(courier, waybill)
        if not self.enabled:
            raise HTTPException(503, "物流推送尚未配置完成")
        row = session.scalar(select(TrackingSubscription).where(
            TrackingSubscription.courier == courier, TrackingSubscription.waybill == waybill))
        if row:
            return serialize(row)
        row = TrackingSubscription(courier=courier, waybill=waybill)
        session.add(row)
        try:
            # Commit intent before HTTP: concurrent requests and restarts cannot resubmit.
            session.commit()
        except IntegrityError:
            session.rollback()
            row = session.scalar(select(TrackingSubscription).where(
                TrackingSubscription.courier == courier, TrackingSubscription.waybill == waybill))
            return serialize(row)
        payload = json.dumps({"ShipperCode": courier, "LogisticCode": waybill,
                              "IsNotice": 1}, separators=(",", ":"))
        state = "uncertain"
        try:
            response = httpx.post("https://api.kdniao.com/api/dist", data={
                "EBusinessID": self.business_id, "RequestType": self.request_type,
                "RequestData": payload, "DataSign": sign(payload, self.api_key), "DataType": "2",
            }, timeout=12, follow_redirects=False)
            response.raise_for_status()
            result = response.json()
            if isinstance(result, dict) and isinstance(result.get("Success"), bool):
                state = "active" if result["Success"] else "rejected"
        except (httpx.HTTPError, ValueError):
            pass  # A timeout may already have registered the waybill; never blindly resubmit.
        # A push may have arrived while the subscription HTTP request was running.
        session.expire_all()
        row = session.scalar(select(TrackingSubscription).where(TrackingSubscription.id == row.id).with_for_update())
        if row.subscription_status == "pending":
            row.subscription_status = state
            session.commit()
        return serialize(row)


@router.get("/subscription-options")
def options(request: Request):
    return {"enabled": request.app.state.tracking_subscriptions.enabled}


@router.post("/status")
def status(data: TrackingInput, request: Request, user_id: int = Depends(active_user), session=Depends(get_session)):
    del user_id
    result = request.app.state.tracking_subscriptions.register(session, data.courier, data.waybill)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@router.post("/webhook")
async def webhook(request: Request, session=Depends(get_session)):
    service = request.app.state.tracking_subscriptions
    if not service.enabled:
        raise HTTPException(503, "物流推送尚未启用")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 1024 * 1024:
            raise HTTPException(413, "推送内容过大")
    try:
        form = parse_qs(body.decode("utf-8"), strict_parsing=True, max_num_fields=12)
        if any(len(values) != 1 for values in form.values()):
            raise ValueError()
        raw, signature = form["RequestData"][0], form["DataSign"][0]
        # The console sends signed 102 probes even for 1008 subscriptions.
        # Both notification types carry tracking snapshots; subscription product
        # selection does not determine the notification transport type.
        if form.get("RequestType", [None])[0] not in {"101", "102"} or not hmac.compare_digest(sign(raw, service.api_key), signature):
            raise HTTPException(403, "推送签名无效")
        data = json.loads(raw)
        if not isinstance(data, dict) or str(data.get("EBusinessID")) != service.business_id:
            raise HTTPException(403, "推送账号不匹配")
        items = data["Data"]
        push_time = provider_time(data["PushTime"]).astimezone(timezone.utc).isoformat()
        if not isinstance(items, list) or len(items) > 100 or int(data["Count"]) != len(items):
            raise ValueError()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError()
            courier, waybill = item.get("ShipperCode"), item.get("LogisticCode")
            # Console format probes contain sample shipments which were never
            # registered here. Acknowledge them without validating or storing
            # their business fields. Known subscriptions remain strict below.
            if not isinstance(courier, str) or not isinstance(waybill, str):
                continue
            row = session.scalar(select(TrackingSubscription).where(
                TrackingSubscription.courier == courier, TrackingSubscription.waybill == waybill).with_for_update())
            if not row:
                continue
            if not isinstance(item.get("Success"), bool):
                raise ValueError()
            if item.get("EBusinessID") is not None and str(item["EBusinessID"]) != service.business_id:
                raise HTTPException(403, "推送账号不匹配")
            if item["Success"] is not True:
                continue
            traces = item["Traces"]
            if not isinstance(traces, list) or len(traces) > 1000:
                raise ValueError()
            normalized = []
            for trace in traces:
                if not isinstance(trace, dict) or not isinstance(trace.get("AcceptStation"), str):
                    raise ValueError()
                time_value = provider_time(trace["AcceptTime"]).astimezone(ZoneInfo("Asia/Shanghai")).isoformat()
                normalized.append({"time": time_value, "description": trace["AcceptStation"][:4000]})
            # Full snapshots: reject older pushes, and merge to avoid losing newer events.
            if row.push_time and push_time < row.push_time:
                continue
            previous = json.loads(row.traces)
            merged = {(t["time"], t["description"]): t for t in previous + normalized}
            merged = sorted(merged.values(), key=lambda t: t["time"], reverse=True)
            new_status = STATES.get(str(item.get("State")), "状态待确认")
            if previous and (not normalized or max(t["time"] for t in normalized) < previous[0]["time"]):
                new_status = row.status
            if push_time == row.push_time and merged == previous and new_status == row.status:
                continue
            now = datetime.now(timezone.utc).isoformat()
            if merged != previous or new_status != row.status:
                row.updated_at = now
            row.traces = json.dumps(merged, ensure_ascii=False)
            row.status, row.subscription_status = new_status, "active"
            row.push_time, row.last_push_at = push_time, now
        session.commit()  # Acknowledge only after the whole batch is durable.
    except (ValueError, KeyError, TypeError, UnicodeError):
        session.rollback()
        raise HTTPException(400, "推送格式无效") from None
    return {"EBusinessID": service.business_id, "UpdateTime": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S"), "Success": True, "Reason": ""}
