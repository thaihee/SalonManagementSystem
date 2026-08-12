import pytest
from app import dao
from app.exceptions import ValidationError, DuplicateError, NotFoundError


# =========================================================================
# TEST SUITE: Sản phẩm (Product)
# =========================================================================

def test_add_product_success(app):
    """Kiểm tra thêm sản phẩm hợp lệ thành công"""
    p = dao.add_product(name="Sáp vuốt tóc", price=120000, stock_quantity=50, min_stock_level=10)

    assert p.id is not None
    assert p.product_name == "Sáp vuốt tóc"
    assert p.stock_quantity == 50


def test_add_product_invalid_price(app):
    """Kiểm tra bắt lỗi ValidationError khi giá tiền bị âm"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_product(name="Kem dưỡng ẩm", price=-10000, stock_quantity=10, min_stock_level=5)

    assert "Giá sản phẩm không được âm" in str(excinfo.value)


def test_add_product_invalid_stock(app):
    """Kiểm tra bắt lỗi ValidationError khi tồn kho âm"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_product(name="Dầu gội", price=150000, stock_quantity=-5, min_stock_level=5)

    assert "Số lượng tồn kho không được âm" in str(excinfo.value)


def test_add_product_invalid_min_stock(app):
    """Kiểm tra bắt lỗi ValidationError khi mức tồn kho tối thiểu bị âm"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_product(name="Nước hoa tóc", price=180000, stock_quantity=20, min_stock_level=-3)

    assert "Mức tồn kho tối thiểu không được âm" in str(excinfo.value)


def test_add_product_duplicate_name(app):
    """Kiểm tra bắt lỗi DuplicateError khi trùng tên sản phẩm"""
    dao.add_product(name="Dầu xả bóng mượt", price=95000, stock_quantity=30, min_stock_level=5)

    with pytest.raises(DuplicateError) as excinfo:
        dao.add_product(name="Dầu xả bóng mượt", price=99000, stock_quantity=10, min_stock_level=5)

    assert "đã tồn tại trong hệ thống" in str(excinfo.value)


def test_update_product_success(app):
    """Kiểm tra cập nhật thông tin sản phẩm thành công"""
    p = dao.add_product(name="Gel tạo kiểu", price=70000, stock_quantity=40, min_stock_level=10)

    updated_p = dao.update_product(
        product_id=p.id, name="Gel tạo kiểu Pro", price=90000,
        stock_quantity=60, min_stock_level=15
    )

    assert updated_p.product_name == "Gel tạo kiểu Pro"
    assert updated_p.price == 90000
    assert updated_p.stock_quantity == 60
    assert updated_p.min_stock_level == 15


def test_update_product_keep_same_name_no_duplicate_error(app):
    """Cập nhật sản phẩm nhưng giữ nguyên tên cũ -> KHÔNG bị báo trùng với chính nó"""
    p = dao.add_product(name="Wax vuốt tóc", price=80000, stock_quantity=25, min_stock_level=5)

    updated_p = dao.update_product(
        product_id=p.id, name="Wax vuốt tóc", price=85000,
        stock_quantity=25, min_stock_level=5
    )
    assert updated_p.price == 85000


def test_update_product_duplicate_name_with_other_product(app):
    """Cập nhật tên sản phẩm A trùng với tên sản phẩm B đã tồn tại -> phải bị chặn"""
    dao.add_product(name="Serum mọc tóc", price=250000, stock_quantity=15, min_stock_level=5)
    p2 = dao.add_product(name="Tinh chất dưỡng tóc", price=220000, stock_quantity=15, min_stock_level=5)

    with pytest.raises(DuplicateError):
        dao.update_product(
            product_id=p2.id, name="Serum mọc tóc", price=220000,
            stock_quantity=15, min_stock_level=5
        )


def test_update_product_not_found(app):
    """Cập nhật sản phẩm không tồn tại -> NotFoundError"""
    with pytest.raises(NotFoundError):
        dao.update_product(
            product_id=9999, name="Sản phẩm ma", price=10000,
            stock_quantity=10, min_stock_level=5
        )


def test_delete_product_soft(app):
    """Kiểm tra tính năng Soft Delete (cập nhật active = False)"""
    p = dao.add_product(name="Lược tạo kiểu", price=45000, stock_quantity=100, min_stock_level=20)

    result = dao.delete_product(p.id)
    assert result is True

    deleted_p = dao.get_product_by_id(p.id)
    assert deleted_p.active is False


def test_delete_product_not_found(app):
    """Xóa sản phẩm không tồn tại -> NotFoundError"""
    with pytest.raises(NotFoundError):
        dao.delete_product(9999)


def test_deleted_product_not_shown_in_load_products(app):
    """Sản phẩm đã bị soft-delete không được xuất hiện trong danh sách load_products()"""
    p = dao.add_product(name="Bàn chải hấp dầu", price=55000, stock_quantity=30, min_stock_level=5)
    dao.delete_product(p.id)

    all_products = dao.load_products()
    names = [x.product_name for x in all_products]
    assert "Bàn chải hấp dầu" not in names


def test_check_low_stock_products(app):
    """Kiểm tra tính năng lọc sản phẩm sắp hết hàng (stock <= min_stock)"""
    # Thêm 1 SP an toàn và 1 SP sắp hết hàng
    dao.add_product(name="SP An Toàn", price=100, stock_quantity=20, min_stock_level=5)
    dao.add_product(name="SP Cảnh Báo", price=100, stock_quantity=3, min_stock_level=5)

    low_stock_list = dao.check_low_stock_products()

    assert len(low_stock_list) == 1
    assert low_stock_list[0].product_name == "SP Cảnh Báo"