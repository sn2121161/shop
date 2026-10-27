"""On-demand queries using the explicitly configured Kdniao product."""
import base64
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from threading import Lock
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .security import active_user
from .database import get_session

PROVIDER_URL = "https://api.kdniao.com/Ebusiness/EbusinessOrderHandle.aspx"
# Couriers integrated by this app. Provider entitlements depend on the account.
COURIERS = [
    ("YTO", "圆通速递", True), ("STO", "申通快递", True),
    ("JTSD", "极兔速递", True), ("HTKY", "百世快递", True),
    ("SF", "顺丰速运", False), ("YD", "韵达快递", False),
    ("ZTO", "中通快递", False), ("EMS", "EMS", False),
]
SUPPORTED_COURIERS = {code: name for code, name, supported in COURIERS if supported}
STATES = {"0": "暂无轨迹", "1": "已揽收", "2": "运输中", "3": "已签收", "4": "问题件"}
LOGGER = logging.getLogger("shop.tracking")


def provider_failure(reason, courier, request_type="1002"):
    """Translate known provider reasons without echoing private provider payloads."""
    text = str(reason or "").casefold()
    if "不匹配" in text and any(word in text for word in ("快递", "运单", "单号")):
        return "courier_mismatch", 400, f"运单号与所选的{SUPPORTED_COURIERS[courier]}不匹配，请核对快递公司和运单号"
    if any(word in text for word in ("签名", "密钥", "apikey", "api key", "appkey", "ebusinessid", "用户id", "商户id", "用户不存在")):
        return "credentials", 503, "物流服务凭证校验失败，请管理员核对快递鸟用户 ID 和 API Key"
    if any(word in text for word in ("到期", "过期", "失效")):
        return "expired", 503, "物流查询服务已过期或失效，请管理员核对服务有效期"
    if any(word in text for word in ("余量", "余额", "额度", "次数", "流量不足", "套餐已用完")):
        return "quota", 503, "物流查询次数或可用额度不足，请等待额度恢复或联系管理员"
    if any(word in text for word in ("权限", "授权", "未开通", "没有可用套餐", "无可用套餐", "套餐不存在", "未购买", "未订购", "不支持此接口")):
        return "permission", 503, f"当前账号没有适用于{SUPPORTED_COURIERS[courier]}查询接口（{request_type}）的可用套餐，请管理员在快递鸟核对所开通的服务及套餐有效期"
    if any(word in text for word in ("手机号", "手机号码", "电话号码", "尾号")):
        return "phone_required", 400, "服务商要求对该运单进行手机号校验，请向商家确认查询要求"
    if any(word in text for word in ("格式", "单号错误", "运单号不正确", "单号不能为空")):
        return "invalid_waybill", 400, "服务商未接受此运单号格式，请核对单号是否完整、是否包含多余字符"
    if any(word in text for word in ("无轨迹", "暂无物流", "暂无轨迹", "无物流信息", "查无", "暂无记录", "未查询到", "单号不存在", "无查询记录")):
        return "no_data", 200, "暂无轨迹"
    return "unknown", 502, "物流服务未能完成查询，请稍后重试；若持续失败，请管理员核查服务返回"


class TrackingInput(BaseModel):
    courier: str = Field(min_length=1, max_length=12)
    waybill: str = Field(min_length=1, max_length=60)


class TrackingService:
    def __init__(self, business_id: str, api_key: str, request_type: str = "1002"):
        if request_type not in {"1002", "8002"}:
            raise ValueError("KDNIAO_REQUEST_TYPE must be 1002 or 8002")
        self.business_id = business_id
        self.api_key = api_key
        self.request_type = request_type
        self._lock = Lock()
        self._cache = OrderedDict()
        self._last_request = float("-inf")

    @property
    def enabled(self):
        return bool(self.business_id and self.api_key)

    def query(self, user_id: int, courier: str, waybill: str):
        if courier not in SUPPORTED_COURIERS:
            raise HTTPException(400, "该快递商暂未接入，请选择圆通、申通、极兔或百世")
        normalized = re.sub(r"\s", "", waybill).upper()
        if not re.fullmatch(r"[A-Z0-9]{6,40}", normalized):
            raise HTTPException(400, "运单号应为 6–40 位字母或数字")
        if not self.enabled:
            raise HTTPException(503, "站内物流查询尚未开通，需管理员配置快递鸟用户 ID 和 API Key")

        cache_key = (user_id, courier, normalized)
        # Serialize requests, deduplicate repeat clicks, and bound the short-lived cache.
        with self._lock:
            now = time.monotonic()
            cached = self._cache.get(cache_key)
            if cached and now - cached[0] < 300:
                return {**cached[1], "cached": True}
            if now - self._last_request < 1:
                raise HTTPException(429, "查询过于频繁，请稍后重试")
            self._last_request = now
            payload = json.dumps({"ShipperCode": courier, "LogisticCode": normalized}, separators=(",", ":"))
            digest = hashlib.md5((payload + self.api_key).encode()).hexdigest()
            signature = base64.b64encode(digest.encode()).decode()
            try:
                response = httpx.post(PROVIDER_URL, data={
                    "EBusinessID": self.business_id, "RequestType": self.request_type, "DataType": "2",
                    "RequestData": payload, "DataSign": signature,
                }, timeout=12, follow_redirects=False)
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError):
                raise HTTPException(502, "物流服务暂时不可用，请稍后重试") from None
            if not isinstance(data, dict):
                raise HTTPException(502, "物流服务返回格式异常")
            if not isinstance(data.get("Success"), bool):
                raise HTTPException(502, "物流服务返回格式异常")
            # Failed queries can be input errors or simply have no data. They are
            # not all authorization failures; never echo untrusted raw reasons.
            if data.get("Success") is not True:
                if data.get("Reason") or data.get("Traces") != []:
                    category, status, message = provider_failure(data.get("Reason"), courier, self.request_type)
                    LOGGER.warning("Tracking query rejected: courier=%s category=%s", courier, category)
                    if category == "no_data" and data.get("Traces") in (None, []):
                        data["Traces"] = []
                    else:
                        raise HTTPException(status if status != 200 else 502, message)
            if data.get("ShipperCode", courier) != courier or data.get("LogisticCode", normalized) != normalized:
                raise HTTPException(502, "物流服务返回的运单与本次查询不一致")
            raw_traces = data.get("Traces")
            if not isinstance(raw_traces, list):
                raise HTTPException(502, "物流服务返回的轨迹格式异常")
            traces = []
            for trace in raw_traces:
                if not isinstance(trace, dict) or not isinstance(trace.get("AcceptTime"), str) or not isinstance(trace.get("AcceptStation"), str):
                    raise HTTPException(502, "物流服务返回的轨迹格式异常")
                traces.append({"time": trace["AcceptTime"], "description": trace["AcceptStation"]})
            traces.sort(key=lambda trace: trace["time"].replace("/", "-"), reverse=True)
            result = {
                "courier": courier, "courierName": SUPPORTED_COURIERS[courier], "waybill": normalized,
                "status": STATES.get(str(data.get("State")), "状态待确认") if traces else "暂无轨迹",
                "traces": traces, "provider": "快递鸟",
                "queriedAt": datetime.now(timezone.utc).isoformat(), "cached": False,
            }
            self._cache[cache_key] = (time.monotonic(), result)
            self._cache.move_to_end(cache_key)
            while len(self._cache) > 256:
                self._cache.popitem(last=False)
            return result


tracking_router = APIRouter(prefix="/api/tracking")


@tracking_router.get("/options")
def tracking_options(request: Request):
    return {"provider": "快递鸟", "enabled": request.app.state.tracking.enabled,
            "couriers": [{"code": code, "name": name, "supported": supported} for code, name, supported in COURIERS]}


@tracking_router.post("/query")
def query_tracking(data: TrackingInput, request: Request, user_id: int = Depends(active_user), session=Depends(get_session)):
    subscriptions = request.app.state.tracking_subscriptions
    result = (subscriptions.register(session, data.courier, data.waybill) if subscriptions.enabled
              else request.app.state.tracking.query(user_id, data.courier, data.waybill))
    return JSONResponse(result, headers={"Cache-Control": "no-store"})
