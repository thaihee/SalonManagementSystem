import pytest
from app import app as flask_app, db
from app import dao
from app.models import Service, Product
from app.exceptions import ValidationError, DuplicateError, NotFoundError


# =========================================================================
# FIXTURE: Cấu hình môi trường test độc lập
# =========================================================================
@pytest.fixture
def app():
    """Tạo môi trường Flask app riêng cho testing với SQLite in-memory"""
    flask_app.config.update({
        "TESTING": True,
        # Dùng SQLite trên RAM để test chạy nhanh và không ảnh hưởng DB thật
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False
    })

    with flask_app.app_context():
        db.create_all()  # Tạo các bảng tạm thời trên RAM
        yield flask_app
        db.session.remove()
        db.drop_all()  # Xóa sạch sau khi test xong


@pytest.fixture
def client(app):
    return app.test_client()


# =========================================================================
# TEST SUITE: Dịch vụ (Service)
# =========================================================================

def test_add_service_success(app):
    """Kiểm tra thêm dịch vụ hợp lệ thành công"""
    s = dao.add_service(name="Cắt tóc nam", price=100000, duration=30, description="Cắt cơ bản")

    assert s.id is not None
    assert s.service_name == "Cắt tóc nam"
    assert s.price == 100000
    assert s.duration_minutes == 30

    # Kiểm tra DB xem đã lưu chưa
    saved_service = Service.query.get(s.id)
    assert saved_service is not None


def test_add_service_invalid_price(app):
    """Kiểm tra bắt lỗi ValidationError khi giá tiền bị âm"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_service(name="Gội đầu", price=-50000, duration=30)

    assert "Giá dịch vụ không được âm" in str(excinfo.value)


def test_add_service_duplicate_name(app):
    """Kiểm tra bắt lỗi DuplicateError khi trùng tên dịch vụ"""
    dao.add_service(name="Uốn tóc", price=300000, duration=60)

    with pytest.raises(DuplicateError) as excinfo:
        dao.add_service(name="Uốn tóc", price=350000, duration=90)

    assert "đã tồn tại trong hệ thống" in str(excinfo.value)


def test_update_service_success(app):
    """Kiểm tra cập nhật thông tin dịch vụ thành công"""
    s = dao.add_service(name="Nhuộm tóc", price=200000, duration=60)

    updated_s = dao.update_service(service_id=s.id, name="Nhuộm tóc VIP", price=250000, duration=90)

    assert updated_s.service_name == "Nhuộm tóc VIP"
    assert updated_s.price == 250000
    assert updated_s.duration_minutes == 90


def test_delete_service_soft(app):
    """Kiểm tra tính năng Soft Delete (cập nhật active = False)"""
    s = dao.add_service(name="Massage mặt", price=150000, duration=45)

    result = dao.delete_service(s.id)
    assert result is True

    deleted_s = Service.query.get(s.id)
    assert deleted_s.active is False


# =========================================================================
# TEST SUITE: Sản phẩm (Product)
# =========================================================================

def test_add_product_success(app):
    """Kiểm tra thêm sản phẩm hợp lệ thành công"""
    p = dao.add_product(name="Sáp vuốt tóc", price=120000, stock_quantity=50, min_stock_level=10)

    assert p.id is not None
    assert p.product_name == "Sáp vuốt tóc"
    assert p.stock_quantity == 50


def test_add_product_invalid_stock(app):
    """Kiểm tra bắt lỗi ValidationError khi tồn kho âm"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_product(name="Dầu gội", price=150000, stock_quantity=-5, min_stock_level=5)

    assert "Số lượng tồn kho không được âm" in str(excinfo.value)


def test_check_low_stock_products(app):
    """Kiểm tra tính năng lọc sản phẩm sắp hết hàng (stock <= min_stock)"""
    # Thêm 1 SP an toàn và 1 SP sắp hết hàng
    dao.add_product(name="SP An Toàn", price=100, stock_quantity=20, min_stock_level=5)
    dao.add_product(name="SP Cảnh Báo", price=100, stock_quantity=3, min_stock_level=5)

    low_stock_list = dao.check_low_stock_products()

    assert len(low_stock_list) == 1
    assert low_stock_list[0].product_name == "SP Cảnh Báo"