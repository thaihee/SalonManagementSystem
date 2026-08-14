import pytest

from app import dao
from app.exceptions import ValidationError, NotFoundError

# =========================================================================
# TEST SUITE: Nhập kho
# =========================================================================

def test_import_stock_success(app):
    """Nhập kho hợp lệ -> stock_quantity tăng đúng số lượng"""
    p = dao.add_product(name="Dầu xả phục hồi", price=100000, stock_quantity=10, min_stock_level=5)
    updated = dao.import_stock(p.id, 5)
    assert updated.stock_quantity == 15


def test_import_stock_invalid_quantity_zero(app):
    """Nhập kho với số lượng = 0 -> phải bị chặn"""
    p = dao.add_product(name="Kem ủ tóc", price=150000, stock_quantity=10, min_stock_level=5)
    with pytest.raises(ValidationError) as excinfo:
        dao.import_stock(p.id, 0)
    assert "lớn hơn 0" in str(excinfo.value)


def test_import_stock_invalid_quantity_negative(app):
    """Nhập kho với số lượng âm -> phải bị chặn"""
    p = dao.add_product(name="Serum dưỡng tóc", price=200000, stock_quantity=10, min_stock_level=5)
    with pytest.raises(ValidationError):
        dao.import_stock(p.id, -5)


def test_import_stock_not_a_number(app):
    """Nhập kho với dữ liệu không phải số -> phải bị chặn"""
    p = dao.add_product(name="Xịt dưỡng tóc", price=90000, stock_quantity=10, min_stock_level=5)
    with pytest.raises(ValidationError):
        dao.import_stock(p.id, "abc")


def test_import_stock_product_not_found(app):
    """Nhập kho cho sản phẩm không tồn tại -> NotFoundError"""
    with pytest.raises(NotFoundError):
        dao.import_stock(9999, 10)


# =========================================================================
# TEST SUITE: Xuất kho (trọng tâm: validate không cho xuất âm)
# =========================================================================

def test_export_stock_success(app):
    """Xuất kho hợp lệ -> stock_quantity giảm đúng số lượng"""
    p = dao.add_product(name="Sáp tạo kiểu", price=85000, stock_quantity=10, min_stock_level=5)
    updated = dao.export_stock(p.id, 4)
    assert updated.stock_quantity == 6


def test_export_stock_exact_all(app):
    """Xuất đúng bằng số lượng tồn kho hiện có -> về 0, KHÔNG lỗi"""
    p = dao.add_product(name="Dầu dưỡng bóng", price=70000, stock_quantity=5, min_stock_level=2)
    updated = dao.export_stock(p.id, 5)
    assert updated.stock_quantity == 0


def test_export_stock_not_enough(app):
    """Xuất kho vượt quá tồn kho hiện có -> phải chặn, KHÔNG cho stock âm"""
    p = dao.add_product(name="Tinh dầu bưởi", price=60000, stock_quantity=3, min_stock_level=5)
    with pytest.raises(ValidationError) as excinfo:
        dao.export_stock(p.id, 10)
    assert "Không đủ tồn kho" in str(excinfo.value)

    # Đảm bảo stock KHÔNG bị thay đổi/âm sau khi validate fail
    unchanged = dao.get_product_by_id(p.id)
    assert unchanged.stock_quantity == 3


def test_export_stock_invalid_quantity_negative(app):
    """Xuất kho với số lượng âm -> phải bị chặn"""
    p = dao.add_product(name="Gôm vuốt tóc", price=95000, stock_quantity=10, min_stock_level=5)
    with pytest.raises(ValidationError):
        dao.export_stock(p.id, -3)


def test_export_stock_product_not_found(app):
    """Xuất kho cho sản phẩm không tồn tại -> NotFoundError"""
    with pytest.raises(NotFoundError):
        dao.export_stock(9999, 5)


# =========================================================================
# TEST SUITE: Cảnh báo tồn kho thấp (liên kết với nghiệp vụ xuất kho)
# =========================================================================

def test_low_stock_warning_triggered_after_export(app):
    """Xuất kho khiến tồn kho tụt xuống <= min_stock_level -> phải xuất hiện
    trong danh sách cảnh báo tồn kho thấp"""
    p = dao.add_product(name="Tinh dầu bạc hà", price=60000, stock_quantity=10, min_stock_level=8)
    dao.export_stock(p.id, 5)  # còn 5, dưới min_stock_level=8

    low_stock = dao.check_low_stock_products()
    names = [x.product_name for x in low_stock]
    assert "Tinh dầu bạc hà" in names


def test_low_stock_warning_not_triggered_when_above_min(app):
    """Tồn kho còn trên min_stock_level -> KHÔNG xuất hiện trong cảnh báo"""
    p = dao.add_product(name="Dầu gội thảo dược", price=100000, stock_quantity=20, min_stock_level=5)
    dao.export_stock(p.id, 3)  # còn 17, vẫn trên min_stock_level=5

    low_stock = dao.check_low_stock_products()
    names = [x.product_name for x in low_stock]
    assert "Dầu gội thảo dược" not in names


def test_low_stock_warning_cleared_after_import(app):
    """Sản phẩm đang cảnh báo thấp, sau khi nhập thêm đủ hàng -> hết cảnh báo"""
    p = dao.add_product(name="Kem chống nắng tóc", price=110000, stock_quantity=3, min_stock_level=5)
    assert p.product_name in [x.product_name for x in dao.check_low_stock_products()]

    dao.import_stock(p.id, 10)  # 3 + 10 = 13, trên min_stock_level=5
    low_stock = dao.check_low_stock_products()
    names = [x.product_name for x in low_stock]
    assert "Kem chống nắng tóc" not in names