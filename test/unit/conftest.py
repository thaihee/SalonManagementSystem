import pytest
import uuid
from datetime import datetime, timedelta

from app import dao
from app.models import UserRole


def unique_suffix():
    return uuid.uuid4().hex[:8]


def unique_phone():
    return f"09{uuid.uuid4().int % 100000000:08d}"


# =========================================================================
# NGHIỆP VỤ 1: User mẫu theo từng role
# Dùng chung cho test_auth_dao.py và cho các unit test khác cần customer/staff
# =========================================================================
@pytest.fixture
def admin_user(app):
    suffix = unique_suffix()

    return dao.add_user(
        full_name="Admin Test",
        username=f"admin{suffix}",
        password="Admin123",
        phone=unique_phone(),
        email=f"admin{suffix}@test.com",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def staff_user(app):
    suffix = unique_suffix()

    return dao.add_user(
        full_name="Staff Test",
        username=f"staff{suffix}",
        password="Staff123",
        phone=unique_phone(),
        email=f"staff{suffix}@test.com",
        role=UserRole.STAFF,
    )


@pytest.fixture
def receptionist_user(app):
    suffix = unique_suffix()

    return dao.add_user(
        full_name="Reception Test",
        username=f"recep{suffix}",
        password="Recep123",
        phone=unique_phone(),
        email=f"recep{suffix}@test.com",
        role=UserRole.RECEPTIONIST,
    )


@pytest.fixture
def customer_user(app):
    suffix = unique_suffix()

    return dao.add_user(
        full_name="Customer Test",
        username=f"cust{suffix}",
        password="Customer123",
        phone=unique_phone(),
        email=f"cust{suffix}@test.com",
        role=UserRole.CUSTOMER,
    )


# =========================================================================
# NGHIỆP VỤ 2 & 6: Service + Service-Product (định mức)
# =========================================================================
@pytest.fixture
def sample_service(app):
    suffix = unique_suffix()

    return dao.add_service(
        name=f"Service Test {suffix}",
        price=100000,
        duration=30,
        description="Dịch vụ test",
    )


@pytest.fixture
def sample_product(app):
    suffix = unique_suffix()

    return dao.add_product(
        name=f"Product Test {suffix}",
        unit="CHAI",
        stock_quantity=50,
        min_stock_level=10,
    )


# =========================================================================
# NGHIỆP VỤ 3: Product & Nhập/Xuất kho
# =========================================================================


@pytest.fixture
def sample_service_product(app, sample_service, sample_product):
    """Định mức: dịch vụ Cắt tóc nam dùng 1 chai Dầu gội / lần"""
    return dao.add_service_product(
        service_id=sample_service.id,
        product_id=sample_product.id,
        default_quantity=1,
    )


# =========================================================================
# NGHIỆP VỤ 4: Appointment
# `staff_user` bắt buộc phải active + role STAFF để create_appointment
# tìm thấy khi auto-gán stylist ngẫu nhiên (staff_id=None)
# =========================================================================
@pytest.fixture
def sample_appointment(app, customer_user, staff_user, sample_service):
    tomorrow = datetime.now() + timedelta(days=1)
    return dao.create_appointment(
        customer_id=customer_user.id,
        service_id=sample_service.id,
        staff_id=staff_user.id,
        date_str=tomorrow.strftime("%Y-%m-%d"),
        time_str="09:00",
    )


# =========================================================================
# NGHIỆP VỤ 5 & 7: Invoice + Promotion
# =========================================================================
@pytest.fixture
def sample_promotion(app):
    suffix = unique_suffix().upper()
    today = datetime.now().date()

    return dao.add_promotion(
        promo_code=f"SALE{suffix}",
        promo_type="PERCENT",
        value=10,
        start_date=today.strftime("%Y-%m-%d"),
        end_date=(today + timedelta(days=30)).strftime("%Y-%m-%d"),
    )


@pytest.fixture
def sample_invoice(app, customer_user, staff_user, sample_service):
    details_data = [
        {"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 1}
    ]
    return dao.create_invoice(
        customer_id=customer_user.id,
        staff_id=staff_user.id,
        details_data=details_data,
    )