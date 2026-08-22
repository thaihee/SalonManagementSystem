import pytest
from app import dao
from app.exceptions import ValidationError, DuplicateError, NotFoundError
from app.models import ProductUnit


# =========================================================================
# add_product & _validate_product_core — Validation & Tạo sản phẩm
# =========================================================================
class TestAddProduct:

    def test_add_product_success(self, app):
        p = dao.add_product(
            name="Gôm xịt tóc Silhouett",
            unit="CHAI",
            stock_quantity=20,
            min_stock_level=5
        )
        assert p.id is not None
        assert p.product_name == "Gôm xịt tóc Silhouett"
        assert p.unit == ProductUnit.CHAI
        assert p.stock_quantity == 20.0
        assert p.min_stock_level == 5.0

    def test_empty_name_raises(self, app):
        with pytest.raises(ValidationError):
            dao.add_product(name="   ", unit="CHAI", stock_quantity=10, min_stock_level=2)

    def test_invalid_unit_raises(self, app):
        with pytest.raises(ValidationError):
            dao.add_product(name="Thuốc nhuộm", unit="CAN", stock_quantity=10, min_stock_level=2)

    @pytest.mark.parametrize("invalid_stock", [-1, "abc"])
    def test_invalid_stock_quantity_raises(self, app, invalid_stock):
        with pytest.raises(ValidationError):
            dao.add_product(name="Sáp vuốt tóc", unit="GOI", stock_quantity=invalid_stock, min_stock_level=2)

    @pytest.mark.parametrize("invalid_min", [-1, "abc"])
    def test_invalid_min_stock_raises(self, app, invalid_min):
        with pytest.raises(ValidationError):
            dao.add_product(name="Sáp vuốt tóc", unit="GOI", stock_quantity=10, min_stock_level=invalid_min)

    def test_duplicate_name_raises(self, app, sample_product):
        with pytest.raises(DuplicateError):
            dao.add_product(name=sample_product.product_name, unit="CHAI", stock_quantity=10, min_stock_level=2)


# =========================================================================
# update_product & delete_product
# =========================================================================
class TestUpdateAndDeleteProduct:

    def test_update_success(self, app, sample_product):
        updated = dao.update_product(
            product_id=sample_product.id,
            name="Dầu gội xịn",
            unit="ML",
            min_stock_level=15
        )
        assert updated.product_name == "Dầu gội xịn"
        assert updated.unit == ProductUnit.ML
        assert updated.min_stock_level == 15.0

    def test_update_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.update_product(99999, name="SP Ma", unit="CHAI", min_stock_level=5)

    def test_delete_product_soft(self, app, sample_product):
        assert dao.delete_product(sample_product.id) is True
        p = dao.get_product_by_id(sample_product.id)
        assert p.active is False

    def test_delete_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.delete_product(99999)


# =========================================================================
# Nhập / Xuất kho (import_stock, export_stock) & Cảnh báo tồn kho
# =========================================================================
class TestStockOperations:

    def test_import_stock_success(self, app, sample_product):
        updated = dao.import_stock(sample_product.id, quantity=20)
        assert updated.stock_quantity == 70.0  # 50 + 20

    @pytest.mark.parametrize("invalid_qty", [0, -5, "abc"])
    def test_import_stock_invalid_qty_raises(self, app, sample_product, invalid_qty):
        with pytest.raises(ValidationError):
            dao.import_stock(sample_product.id, quantity=invalid_qty)

    def test_import_stock_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.import_stock(99999, quantity=10)

    def test_export_stock_success(self, app, sample_product):
        updated = dao.export_stock(sample_product.id, quantity=20)
        assert updated.stock_quantity == 30.0  # 50 - 20

    def test_export_stock_exceeds_available_raises(self, app, sample_product):
        with pytest.raises(ValidationError):
            dao.export_stock(sample_product.id, quantity=100)  # Tồn kho chỉ có 50

    @pytest.mark.parametrize("invalid_qty", [0, -5, "abc"])
    def test_export_stock_invalid_qty_raises(self, app, sample_product, invalid_qty):
        with pytest.raises(ValidationError):
            dao.export_stock(sample_product.id, quantity=invalid_qty)

    def test_export_stock_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.export_stock(99999, quantity=5)

    def test_check_low_stock_products(self, app, sample_product):
        # Ban đầu stock=50, min=10 -> không nằm trong low stock
        assert len(dao.check_low_stock_products()) == 0

        # Xuất kho 45 chai -> stock=5 <= min=10 -> nằm trong low stock
        dao.export_stock(sample_product.id, 45)
        low_stock = dao.check_low_stock_products()
        assert len(low_stock) == 1
        assert low_stock[0].id == sample_product.id