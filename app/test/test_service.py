import pytest
from app import dao, db  # Thêm import db
from app.models import Service
from app.exceptions import ValidationError, DuplicateError


# =========================================================================
# TEST SUITE: Dịch vụ (Service)
# =========================================================================

def test_add_service_success(app):
    """Kiểm tra thêm dịch vụ hợp lệ thành công"""
    s = dao.add_service(name="Cắt tóc nam", price=100000, duration=30)

    assert s.id is not None
    assert s.service_name == "Cắt tóc nam"
    assert s.price == 100000
    assert s.duration_minutes == 30

    # Kiểm tra DB xem đã lưu chưa (Sửa cảnh báo Query.get)
    saved_service = db.session.get(Service, s.id)
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


def test_add_service_avatar_too_long(app):
    """Kiểm tra bắt lỗi ValidationError khi đường dẫn avatar vượt quá 255 ký tự"""
    long_avatar_url = "https://example.com/images/" + "a" * 250 + ".png"

    with pytest.raises(ValidationError) as excinfo:
        dao.add_service(name="Cạo mặt", price=50000, duration=15, avatar=long_avatar_url)

    assert "vượt quá 255 ký tự" in str(excinfo.value).lower()


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

    # Sửa cảnh báo Query.get
    deleted_s = db.session.get(Service, s.id)
    assert deleted_s.active is False