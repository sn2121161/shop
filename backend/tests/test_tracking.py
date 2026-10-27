import base64
import hashlib
import json

from fastapi import HTTPException
import httpx
import pytest

from shop_api.tracking import TrackingService


@pytest.fixture()
def service():
    return TrackingService("demo-business", "private-api-secret")


def test_free_query_sends_signed_post_and_normalizes_timeline(service, monkeypatch):
    calls = []

    def provider(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "Success": True, "ShipperCode": "YTO", "LogisticCode": "DEMO123456", "State": "3",
            "Traces": [{"AcceptTime": "2026-10-25 10:00:00", "AcceptStation": "测试揽收"},
                       {"AcceptTime": "2026-10-26 12:00:00", "AcceptStation": "测试签收"}],
        })

    monkeypatch.setattr("shop_api.tracking.httpx.post", provider)
    result = service.query(1, "YTO", " demo 123456 ")
    assert result["status"] == "已签收"
    assert result["waybill"] == "DEMO123456"
    assert result["traces"][0]["description"] == "测试签收"
    url, options = calls[0]
    assert url.startswith("https://api.kdniao.com/")
    form = options["data"]
    assert form["RequestType"] == "1002"
    assert json.loads(form["RequestData"]) == {"ShipperCode": "YTO", "LogisticCode": "DEMO123456"}
    expected = base64.b64encode(hashlib.md5((form["RequestData"] + "private-api-secret").encode()).hexdigest().encode()).decode()
    assert form["DataSign"] == expected
    assert "private-api-secret" not in json.dumps(result)
    assert service.query(1, "YTO", "DEMO123456")["cached"] is True
    assert len(calls) == 1
    service._last_request = float("-inf")
    assert service.query(2, "YTO", "DEMO123456")["cached"] is False
    assert len(calls) == 2


@pytest.mark.parametrize("courier,waybill", [("SF", "DEMO123456"), ("YTO", "bad/number"), ("UNKNOWN", "DEMO123456")])
def test_unsupported_or_invalid_input_never_calls_provider(service, monkeypatch, courier, waybill):
    monkeypatch.setattr("shop_api.tracking.httpx.post", lambda *args, **kwargs: pytest.fail("Unexpected network call"))
    with pytest.raises(HTTPException) as failure:
        service.query(1, courier, waybill)
    assert failure.value.status_code == 400


def test_missing_config_is_explicit():
    with pytest.raises(HTTPException) as failure:
        TrackingService("", "").query(1, "STO", "DEMO123456")
    assert failure.value.status_code == 503


@pytest.mark.parametrize("reason,expected_status,expected_message", [
    ("无效的输入[快递公司编码和运单号不匹配，请核实]", 400, "不匹配"),
    ("无效的输入[物流单号格式不正确]", 400, "格式"),
    ("签名校验失败", 503, "凭证"),
    ("业务错误[没有可用套餐]", 503, "查询权限"),
    ("套餐已过期", 503, "过期"),
    ("查询次数超过每日限制", 503, "次数"),
    ("未知错误 private-api-secret", 502, "未能完成查询"),
])
def test_provider_failures_explain_the_actual_category(service, monkeypatch, reason, expected_status, expected_message, caplog):
    monkeypatch.setattr("shop_api.tracking.httpx.post", lambda url, **kwargs: httpx.Response(200, request=httpx.Request("POST", url), json={"Success": False, "Reason": reason, "Traces": []}))
    with pytest.raises(HTTPException) as failure:
        service.query(1, "STO", "DEMO123456")
    assert failure.value.status_code == expected_status
    assert expected_message in failure.value.detail
    assert "private-api-secret" not in failure.value.detail + caplog.text
    assert "DEMO123456" not in caplog.text


@pytest.mark.parametrize("reason", ["暂无物流轨迹", "单号不存在或尚未揽收", "未查询到物流信息"])
def test_explicit_no_data_is_not_reported_as_authorization_failure(service, monkeypatch, reason):
    monkeypatch.setattr("shop_api.tracking.httpx.post", lambda url, **kwargs: httpx.Response(200, request=httpx.Request("POST", url), json={"Success": False, "Reason": reason}))
    result = service.query(1, "STO", "DEMO123456")
    assert result["status"] == "暂无轨迹"
    assert result["traces"] == []


@pytest.mark.parametrize("payload", [
    {"Success": False, "Reason": "invalid private-api-secret", "Traces": []},
    {"Success": True, "Traces": "bad"},
    {"Success": True, "LogisticCode": "OTHER12345", "Traces": []},
    {"Success": True, "Traces": [{"AcceptTime": 123, "AcceptStation": None}]},
    {"Traces": []},
])
def test_provider_failures_and_mismatches_are_not_shown_as_real_results(service, monkeypatch, payload):
    monkeypatch.setattr("shop_api.tracking.httpx.post", lambda url, **kwargs: httpx.Response(200, request=httpx.Request("POST", url), json=payload))
    with pytest.raises(HTTPException) as failure:
        service.query(1, "YTO", "DEMO123456")
    assert failure.value.status_code == 502
    assert "private-api-secret" not in failure.value.detail


def test_no_traces_and_timeouts_are_distinct(service, monkeypatch):
    monkeypatch.setattr("shop_api.tracking.httpx.post", lambda url, **kwargs: httpx.Response(200, request=httpx.Request("POST", url), json={"Success": False, "Reason": None, "Traces": []}))
    result = service.query(1, "STO", "DEMO123456")
    assert result["status"] == "暂无轨迹" and result["traces"] == []

    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("private-api-secret")

    monkeypatch.setattr("shop_api.tracking.httpx.post", timeout)
    with pytest.raises(HTTPException) as failure:
        TrackingService("id", "key").query(1, "STO", "DEMO123456")
    assert failure.value.status_code == 502
    assert "private-api-secret" not in failure.value.detail
