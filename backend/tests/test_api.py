import pytest
from fastapi.testclient import TestClient
from urllib.parse import parse_qs, urlparse

from app import create_app


@pytest.fixture()
def client(tmp_path):
    with TestClient(create_app("sqlite://", upload_directory=tmp_path / "uploads")) as test_client:
        yield test_client


def register_and_login(client):
    payload = {"username": "molecule_user", "email": "molecule_user@example.com", "password": "StrongPass1!", "confirmPassword": "StrongPass1!"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    return client.post("/api/auth/login", json={"username": payload["username"], "password": payload["password"]}).json()["token"]


def admin_headers(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_registration_rejects_weak_password(client):
    response = client.post("/api/auth/register", json={"username": "test_user", "email": "test_user@example.com", "password": "weak", "confirmPassword": "weak"})
    assert response.status_code == 400
    assert response.json()["message"].startswith("密码至少")


def test_registration_requires_a_unique_email(client):
    payload = {"username": "email_user", "email": "email_user@example.com", "password": "StrongPass1!", "confirmPassword": "StrongPass1!"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json={**payload, "username": "other_user"}).status_code == 409
    assert client.post("/api/auth/register", json={key: value for key, value in payload.items() if key != "email"}).status_code == 422


def test_login_accepts_a_registered_email(client):
    payload = {"username": "email_login_user", "email": "email_login_user@example.com", "password": "StrongPass1!", "confirmPassword": "StrongPass1!"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    response = client.post("/api/auth/login", json={"username": "EMAIL_LOGIN_USER@EXAMPLE.COM", "password": payload["password"]})
    assert response.status_code == 200
    assert response.json()["user"]["username"] == payload["username"]


def test_password_reset_is_single_use_and_invalidates_existing_login(client, monkeypatch):
    token = register_and_login(client)
    delivered = []
    monkeypatch.setattr("shop_api.routers.send_password_reset_email", lambda recipient, username, url: delivered.append((recipient, username, url)))
    response = client.post("/api/auth/forgot-password", json={"email": "molecule_user@example.com"})
    assert response.status_code == 200
    assert delivered and delivered[0][0] == "molecule_user@example.com"
    reset_token = parse_qs(urlparse(delivered[0][2]).query)["token"][0]
    reset = client.post("/api/auth/reset-password", json={"token": reset_token, "newPassword": "NewStrongPass1!", "confirmPassword": "NewStrongPass1!"})
    assert reset.status_code == 200
    assert client.get("/api/cart", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "molecule_user", "password": "StrongPass1!"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "molecule_user", "password": "NewStrongPass1!"}).status_code == 200
    assert client.post("/api/auth/reset-password", json={"token": reset_token, "newPassword": "OtherStrong1!", "confirmPassword": "OtherStrong1!"}).status_code == 400


def test_products_endpoint_allows_the_frontend_dev_origin(client):
    response = client.get("/api/products", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cart_and_order_reduce_stock(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/cart", json={"productId": 1, "quantity": 1}, headers=headers).status_code == 201
    cart = client.get("/api/cart", headers=headers).json()
    order = client.post("/api/orders", json={"itemIds": [cart[0]["id"]]}, headers=headers)
    assert order.status_code == 201
    assert order.json()["total"] == 10.0
    assert client.get("/api/products/1").json()["stock"] == 11


def test_order_rolls_back_when_stock_insufficient(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/cart", json={"productId": 1, "quantity": 13}, headers=headers)
    cart = client.get("/api/cart", headers=headers).json()
    response = client.post("/api/orders", json={"itemIds": [cart[0]["id"]]}, headers=headers)
    assert response.status_code == 409
    assert client.get("/api/products/1").json()["stock"] == 12


def test_customer_can_upload_an_image_and_publish_a_rich_comment(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post("/api/comment-images", headers=headers, files={"image": ("note.png", b"png-data", "image/png")})
    assert uploaded.status_code == 201
    image = uploaded.json()
    content = f'<p><strong>结构很有层次</strong> <span style="color:#265842">颜色很漂亮</span></p><img src="{image["url"]}" alt="留言图片"><script>alert(1)</script>'
    created = client.post("/api/products/1/comments", headers=headers, json={"content": content, "imageIds": [image["id"]]})
    assert created.status_code == 201
    assert "<strong>结构很有层次</strong>" in created.json()["content"]
    assert "<script>" not in created.json()["content"]
    comments = client.get("/api/products/1/comments")
    assert comments.status_code == 200
    assert comments.json()[0]["author"] == "molecule_user"


def test_checkout_saves_address_card_and_delivery_snapshot(client):
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    address = {"recipientName": "小林", "recipientPhone": "13800138000", "province": "江苏省", "city": "常州市", "district": "天宁区", "detail": "文化广场 1 号"}
    assert client.put("/api/account/address", headers=headers, json=address).json() == address
    card = client.post("/api/payment-methods", headers=headers, json={"cardNumber": "4242 4242 4242 4242"})
    assert card.status_code == 201 and card.json()["last4"] == "4242"
    assert "4242 4242" not in str(card.json())
    client.post("/api/cart", json={"productId": 1, "quantity": 1}, headers=headers)
    cart = client.get("/api/cart", headers=headers).json()
    order = client.post("/api/orders", headers=headers, json={"itemIds": [cart[0]["id"]], "deliveryService": "sf", "paymentType": "bank_card", "paymentMethodId": card.json()["id"], "address": address})
    assert order.status_code == 201
    assert order.json()["total"] == 15.0
    assert order.json()["fulfillment"]["deliveryFee"] == 5.0
    assert order.json()["fulfillment"]["paymentLast4"] == "4242"
    assert order.json()["customerAccount"] == "molecule_user"
    assert order.json()["notificationStatus"] == "pending"


def test_admin_can_disable_and_restore_a_user_immediately(client):
    customer_token = register_and_login(client)
    headers = admin_headers(client)
    users = client.get("/api/admin/users?status=active", headers=headers)
    customer = next(user for user in users.json()["items"] if user["username"] == "molecule_user")
    assert client.post(f"/api/admin/users/{customer['id']}/disable", headers=headers).status_code == 200
    assert client.get("/api/cart", headers={"Authorization": f"Bearer {customer_token}"}).json()["message"] == "该用户已停用"
    assert client.post("/api/auth/login", json={"username": "molecule_user", "password": "StrongPass1!"}).json()["message"] == "该用户已停用"
    assert client.post(f"/api/admin/users/{customer['id']}/restore", headers=headers).status_code == 200
    assert client.post("/api/auth/login", json={"username": "molecule_user", "password": "StrongPass1!"}).status_code == 200


def test_admin_product_lifecycle_hides_unlisted_products_and_validates_prices(client):
    headers = admin_headers(client)
    created = client.post("/api/admin/products", headers=headers, json={"name": "管理端新品", "price": "12.50", "quantity": 2, "tagline": "新品简介", "story": "新品故事"})
    assert created.status_code == 200
    product_id = created.json()["id"]
    assert created.json()["lowStock"] is True
    assert client.post(f"/api/admin/products/{product_id}/price", headers=headers, json={"percent": 10, "direction": "up"}).json()["price"] == 13.75
    assert client.post(f"/api/admin/products/{product_id}/unlist", headers=headers).status_code == 200
    assert all(product["id"] != product_id for product in client.get("/api/products").json())
    assert client.post("/api/cart", headers=headers, json={"productId": product_id, "quantity": 1}).status_code == 409
    assert client.post(f"/api/admin/products/{product_id}/relist", headers=headers, json={"price": "13.75", "quantity": 3}).status_code == 200
    assert any(product["id"] == product_id for product in client.get("/api/products").json())


def test_management_dashboard_aggregates_orders_and_current_inventory(client):
    token = register_and_login(client)
    customer_headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/cart", json={"productId": 1, "quantity": 2}, headers=customer_headers).status_code == 201
    cart = client.get("/api/cart", headers=customer_headers).json()
    assert client.post("/api/orders", json={"itemIds": [cart[0]["id"]]}, headers=customer_headers).status_code == 201
    response = client.get("/api/admin/dashboard", headers=admin_headers(client))
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["todayOrders"] == 1
    assert payload["trend"][-1]["orders"] == 1
    assert payload["users"][0]["username"] == "molecule_user"
    assert payload["products"][0]["product"] == "苯"
    assert payload["details"]["items"][0]["items"][0]["currentStock"] == 10
