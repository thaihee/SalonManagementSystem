import pytest
from app import dao
from app.models import UserRole


# =========================================================================
# HELPER: Tạo user theo role & đăng nhập vào test client
# =========================================================================

def _make_user(role, suffix, avatar=None):
    return dao.add_user(
        full_name=f"User {suffix}",
        username=f"user{suffix}",
        password="Password1",
        phone=f"09000000{suffix}",
        email=f"user{suffix}@example.com",
        role=role,
        avatar=avatar
    )


def login_as(client, user):
    """Giả lập đăng nhập bằng cách set session key của Flask-Login trực tiếp"""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


@pytest.fixture
def admin_user(app):
    return _make_user(UserRole.ADMIN, "01")


@pytest.fixture
def staff_user(app):
    return _make_user(UserRole.STAFF, "02")


@pytest.fixture
def customer_user(app):
    return _make_user(UserRole.CUSTOMER, "03")


# =========================================================================
# TEST SUITE 1: Phân quyền chung (role_required)
# =========================================================================

def test_admin_route_requires_login(client, app):
    """Chưa đăng nhập -> 403"""
    resp = client.get("/admin/products/low-stock")
    assert resp.status_code == 403


def test_admin_route_blocks_customer(client, customer_user):
    """Đăng nhập với role CUSTOMER -> 403 (không phải ADMIN)"""
    login_as(client, customer_user)
    resp = client.get("/admin/products/low-stock")
    assert resp.status_code == 403


def test_admin_route_blocks_staff(client, staff_user):
    """Đăng nhập với role STAFF -> 403 (route chỉ cho phép ADMIN)"""
    login_as(client, staff_user)
    resp = client.get("/admin/products/low-stock")
    assert resp.status_code == 403


def test_admin_route_allows_admin(client, admin_user):
    """Đăng nhập với role ADMIN -> truy cập được"""
    login_as(client, admin_user)
    resp = client.get("/admin/products/low-stock")
    assert resp.status_code == 200


# =========================================================================
# TEST SUITE 2: CRUD Dịch vụ (Service) qua /admin/services
# =========================================================================

def test_list_services_route(client, admin_user):
    """GET /admin/services trả về danh sách dịch vụ dạng JSON"""
    dao.add_service(name="Cắt tóc nam", price=100000, duration=30)
    login_as(client, admin_user)

    resp = client.get("/admin/services")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert any(s["service_name"] == "Cắt tóc nam" for s in data)


def test_create_service_route_success(client, admin_user):
    """POST /admin/services tạo dịch vụ thành công -> 201"""
    login_as(client, admin_user)

    resp = client.post("/admin/services", data={
        "service_name": "Uốn tóc",
        "price": "300000",
        "duration_minutes": "60",
        "description": "Uốn tóc kèm dưỡng",
    })

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["success"] is True
    assert data["id"] is not None


def test_create_service_with_avatar_success(client, admin_user):
    """Thêm dịch vụ thành công có chứa đường dẫn avatar"""
    login_as(client, admin_user)

    s = dao.add_service(
        name="Tẩy tóc VIP",
        price=500000,
        duration=120,
        avatar="http://example.com/taytoc.jpg"
    )
    assert s.avatar == "http://example.com/taytoc.jpg"


def test_create_service_route_validation_error(client, admin_user):
    """POST /admin/services với giá âm -> 400"""
    login_as(client, admin_user)

    resp = client.post("/admin/services", data={
        "service_name": "Dịch vụ lỗi",
        "price": "-1000",
        "duration_minutes": "30",
    })

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False


def test_create_service_route_duplicate(client, admin_user):
    """POST /admin/services với tên đã tồn tại -> 409"""
    dao.add_service(name="Gội đầu", price=100000, duration=30)
    login_as(client, admin_user)

    resp = client.post("/admin/services", data={
        "service_name": "Gội đầu",
        "price": "120000",
        "duration_minutes": "30",
    })

    assert resp.status_code == 409


def test_update_service_route_success(client, admin_user):
    """PUT /admin/services/<id> cập nhật thành công -> 200"""
    s = dao.add_service(name="Nhuộm tóc", price=200000, duration=60)
    login_as(client, admin_user)

    resp = client.put(f"/admin/services/{s.id}", data={
        "service_name": "Nhuộm tóc VIP",
        "price": "250000",
        "duration_minutes": "90",
    })

    assert resp.status_code == 200
    updated = dao.get_service_by_id(s.id)
    assert updated.service_name == "Nhuộm tóc VIP"


def test_delete_service_route_success(client, admin_user):
    """DELETE /admin/services/<id> xóa mềm thành công -> 200"""
    s = dao.add_service(name="Massage mặt", price=150000, duration=45)
    login_as(client, admin_user)

    resp = client.delete(f"/admin/services/{s.id}")
    assert resp.status_code == 200

    deleted = dao.get_service_by_id(s.id)
    assert deleted.active is False


# =========================================================================
# TEST SUITE 3: Nhập / Xuất kho qua /admin/products/<id>/import|export
# =========================================================================

def test_import_stock_route_success(client, admin_user):
    """POST /admin/products/<id>/import nhập kho thành công -> 200"""
    p = dao.add_product(name="Dầu gội đầu", price=100000, stock_quantity=10, min_stock_level=5)
    login_as(client, admin_user)

    resp = client.post(f"/admin/products/{p.id}/import", data={"quantity": "5"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["stock_quantity"] == 15


def test_export_stock_route_success(client, admin_user):
    """POST /admin/products/<id>/export xuất kho thành công -> 200"""
    p = dao.add_product(name="Sáp vuốt tóc", price=90000, stock_quantity=10, min_stock_level=5)
    login_as(client, admin_user)

    resp = client.post(f"/admin/products/{p.id}/export", data={"quantity": "4"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["stock_quantity"] == 6


def test_export_stock_route_not_enough(client, admin_user):
    """POST export vượt quá tồn kho -> 400, không cho xuất âm"""
    p = dao.add_product(name="Tinh dầu bưởi", price=60000, stock_quantity=3, min_stock_level=5)
    login_as(client, admin_user)

    resp = client.post(f"/admin/products/{p.id}/export", data={"quantity": "10"})

    assert resp.status_code == 400
    unchanged = dao.get_product_by_id(p.id)
    assert unchanged.stock_quantity == 3


# =========================================================================
# TEST SUITE 4: Cảnh báo tồn kho thấp qua /admin/products/low-stock
# =========================================================================

def test_low_stock_products_route(client, admin_user):
    """GET /admin/products/low-stock trả về đúng danh sách sản phẩm sắp hết hàng"""
    dao.add_product(name="SP An Toàn", price=100000, stock_quantity=20, min_stock_level=5)
    dao.add_product(name="SP Cảnh Báo", price=100000, stock_quantity=3, min_stock_level=5)
    login_as(client, admin_user)

    resp = client.get("/admin/products/low-stock")
    assert resp.status_code == 200

    data = resp.get_json()
    names = [p["product_name"] for p in data]
    assert "SP Cảnh Báo" in names
    assert "SP An Toàn" not in names


# =========================================================================
# TEST SUITE 5: Quản lý Người dùng / Nhân viên qua /users (Bao gồm Avatar)
# =========================================================================

def test_list_users_route(client, admin_user, staff_user):
    """GET /users trả về danh sách tất cả tài khoản người dùng"""
    login_as(client, admin_user)

    resp = client.get("/users")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    usernames = [u["username"] for u in data]
    assert admin_user.username in usernames
    assert staff_user.username in usernames


def test_create_staff_route_success(client, admin_user):
    """POST /users tạo tài khoản nhân viên mới thành công -> 201"""
    login_as(client, admin_user)

    resp = client.post("/users", data={
        "full_name": "Nhân Viên Mới",
        "username": "staffnew",
        "password": "Password1",
        "phone": "0988888888",
        "email": "staffnew@example.com"
    })

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["success"] is True
    assert data["user"]["role"] == "STAFF"


def test_update_user_avatar_dao(app):
    with app.app_context():
        u = dao.add_user(
            full_name="User Test Avatar",
            username="testavatar",
            password="Password1",
            phone="0912345678",
            email="avatar@example.com",
            avatar="http://example.com/old-avatar.jpg"
        )

        updated = dao.update_user_profile(
            user_id=u.id,
            full_name="User Test Avatar",
            phone="0912345678",
            email="avatar@example.com",
            avatar="http://example.com/new-avatar.jpg"
        )

        assert updated.avatar == "http://example.com/new-avatar.jpg"


def test_deactivate_user_route_success(client, admin_user, staff_user):
    """DELETE /users/<id> vô hiệu hóa tài khoản (Soft Delete) -> 200"""
    login_as(client, admin_user)

    resp = client.delete(f"/users/{staff_user.id}")
    assert resp.status_code == 200

    reloaded = dao.get_user_by_id(staff_user.id)
    assert reloaded.active is False