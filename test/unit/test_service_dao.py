import pytest
from app import dao
from app.exceptions import ValidationError, DuplicateError, NotFoundError


# =========================================================================
# validate_service_input & add_service — Validation & Tạo dịch vụ
# =========================================================================
class TestAddService:

    def test_add_service_success(self, app):
        svc = dao.add_service(
            name="Gội đầu dưỡng sinh",
            price=150000,
            duration=45,
            description="Thư giãn 45 phút",
            avatar="https://example.com/avatar.jpg"
        )
        assert svc.id is not None
        assert svc.service_name == "Gội đầu dưỡng sinh"
        assert svc.price == 150000.0
        assert svc.duration_minutes == 45
        assert svc.active is True

    def test_empty_name_raises(self, app):
        with pytest.raises(ValidationError):
            dao.add_service(name="   ", price=100000, duration=30)

    def test_avatar_too_long_raises(self, app):
        long_avatar = "http://example.com/" + "a" * 250
        with pytest.raises(ValidationError):
            dao.add_service(name="Tẩy tóc", price=100000, duration=30, avatar=long_avatar)

    @pytest.mark.parametrize("invalid_price", [-10000, "abc", None])
    def test_invalid_price_raises(self, app, invalid_price):
        with pytest.raises(ValidationError):
            dao.add_service(name="Sấy tóc", price=invalid_price, duration=30)

    @pytest.mark.parametrize("invalid_duration", [0, -15, "xyz", "12.5", None])
    def test_invalid_duration_raises(self, app, invalid_duration):
        with pytest.raises(ValidationError):
            dao.add_service(name="Sấy tóc", price=100000, duration=invalid_duration)

    def test_duplicate_name_raises(self, app, sample_service):
        with pytest.raises(DuplicateError):
            dao.add_service(name=sample_service.service_name, price=200000, duration=45)


# =========================================================================
# update_service — Cập nhật dịch vụ
# =========================================================================
class TestUpdateService:

    def test_update_success(self, app, sample_service):
        updated = dao.update_service(
            service_id=sample_service.id,
            name="Cắt tóc nam VIP",
            price=120000,
            duration=40,
            description="Mô tả mới",
            avatar="https://example.com/new.jpg"
        )
        assert updated.service_name == "Cắt tóc nam VIP"
        assert updated.price == 120000.0
        assert updated.duration_minutes == 40
        assert updated.description == "Mô tả mới"

    def test_update_keep_own_name_ok(self, app, sample_service):
        updated = dao.update_service(sample_service.id, name=sample_service.service_name, price=150000)
        assert updated.price == 150000.0

    def test_update_duplicate_name_raises(self, app, sample_service):
        other_svc = dao.add_service(name="Uốn tóc", price=200000, duration=60)
        with pytest.raises(DuplicateError):
            dao.update_service(other_svc.id, name=sample_service.service_name)

    def test_update_invalid_price_raises(self, app, sample_service):
        with pytest.raises(ValidationError):
            dao.update_service(sample_service.id, price="invalid_number")

    def test_update_invalid_duration_raises(self, app, sample_service):
        with pytest.raises(ValidationError):
            dao.update_service(sample_service.id, duration="invalid_number")

    def test_update_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.update_service(99999, name="Dịch vụ không tồn tại")


# =========================================================================
# delete_service & Query Services
# =========================================================================
class TestDeleteAndQueryService:

    def test_delete_service_soft(self, app, sample_service):
        assert dao.delete_service(sample_service.id) is True
        svc = dao.get_service_by_id(sample_service.id)
        assert svc.active is False

    def test_delete_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.delete_service(99999)

    def test_load_and_count_services(self, app, sample_service):
        assert dao.count_services() == 1
        assert dao.count_services(kw="Cắt") == 1
        assert dao.count_services(kw="Không_Khớp") == 0

        services = dao.load_services(kw="Cắt", page=1, page_size=10)
        assert len(services) == 1
        assert services[0].id == sample_service.id

    def test_get_services_paged(self, app, sample_service):
        services, total = dao.get_services_paged(page=1, page_size=10)
        assert total == 1
        assert len(services) == 1


# =========================================================================
# ServiceProduct — Định mức sản phẩm theo dịch vụ
# =========================================================================
class TestServiceProduct:

    def test_add_service_product_success(self, app, sample_service, sample_product):
        sp = dao.add_service_product(
            service_id=sample_service.id,
            product_id=sample_product.id,
            default_quantity=2.5
        )
        assert sp.id is not None
        assert sp.default_quantity == 2.5

    def test_add_duplicate_pair_raises(self, app, sample_service_product):
        with pytest.raises(DuplicateError):
            dao.add_service_product(
                service_id=sample_service_product.service_id,
                product_id=sample_service_product.product_id,
                default_quantity=1
            )

    @pytest.mark.parametrize("invalid_qty", [0, -1, "abc"])
    def test_add_invalid_quantity_raises(self, app, sample_service, sample_product, invalid_qty):
        with pytest.raises(ValidationError):
            dao.add_service_product(sample_service.id, sample_product.id, default_quantity=invalid_qty)

    def test_add_non_existent_service_raises(self, app, sample_product):
        with pytest.raises(NotFoundError):
            dao.add_service_product(service_id=99999, product_id=sample_product.id, default_quantity=1)

    def test_add_non_existent_product_raises(self, app, sample_service):
        with pytest.raises(NotFoundError):
            dao.add_service_product(service_id=sample_service.id, product_id=99999, default_quantity=1)

    def test_update_service_product_success(self, app, sample_service_product):
        updated = dao.update_service_product(sample_service_product.id, default_quantity=3.0)
        assert updated.default_quantity == 3.0

    def test_update_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.update_service_product(99999, default_quantity=2.0)

    def test_delete_service_product_success(self, app, sample_service_product):
        assert dao.delete_service_product(sample_service_product.id) is True
        assert dao.get_service_product_by_id(sample_service_product.id) is None

    def test_delete_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.delete_service_product(99999)