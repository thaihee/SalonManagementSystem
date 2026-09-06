import uuid
from datetime import datetime, timedelta

import pytest

from app import dao
from app.models import UserRole


# =========================================================================
# HELPER
# =========================================================================

def unique_suffix():
    return uuid.uuid4().hex[:8]


def unique_phone():
    return f"09{uuid.uuid4().int % 100000000:08d}"


# =========================================================================
# HELPER: Đăng nhập giả lập qua session
# =========================================================================

@pytest.fixture
def login_as(client):
    def _login_as(user):
        with client.session_transaction() as sess:
            sess["user_id"] = str(user.id)
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True

        return client

    return _login_as


# =========================================================================
# USER FIXTURES
# =========================================================================

@pytest.fixture
def admin_user(app):
    suffix = unique_suffix()

    user = dao.add_user(
        full_name="Admin Test",
        username=f"admintest{suffix}",
        password="Admin123",
        phone=unique_phone(),
        email=f"admin_{suffix}@test.com",
        role=UserRole.ADMIN,
    )

    user.raw_password = "Admin123"
    return user


@pytest.fixture
def staff_user(app):
    suffix = unique_suffix()

    user = dao.add_user(
        full_name="Staff Test",
        username=f"stafftest{suffix}",
        password="Staff123",
        phone=unique_phone(),
        email=f"staff_{suffix}@test.com",
        role=UserRole.STAFF,
    )

    user.raw_password = "Staff123"
    return user


@pytest.fixture
def receptionist_user(app):
    suffix = unique_suffix()

    user = dao.add_user(
        full_name="Reception Test",
        username=f"recep{suffix}",
        password="Recep123",
        phone=unique_phone(),
        email=f"reception_{suffix}@test.com",
        role=UserRole.RECEPTIONIST,
    )

    user.raw_password = "Recep123"
    return user


@pytest.fixture
def customer_user(app):
    suffix = unique_suffix()

    user = dao.add_user(
        full_name="Customer Test",
        username=f"customertest{suffix}",
        password="Customer123",
        phone=unique_phone(),
        email=f"customer_{suffix}@test.com",
        role=UserRole.CUSTOMER,
    )

    user.raw_password = "Customer123"
    return user

# =========================================================================
# CLIENT FIXTURES
# =========================================================================

@pytest.fixture
def admin_client(client, login_as, admin_user):
    return login_as(admin_user)


@pytest.fixture
def staff_client(client, login_as, staff_user):
    return login_as(staff_user)


@pytest.fixture
def receptionist_client(client, login_as, receptionist_user):
    return login_as(receptionist_user)


@pytest.fixture
def customer_client(client, login_as, customer_user):
    return login_as(customer_user)


# =========================================================================
# SAMPLE DATA FIXTURES
# =========================================================================

@pytest.fixture
def sample_service(app):
    suffix = unique_suffix()

    return dao.add_service(
        name=f"Service Test {suffix}",
        price=100000,
        duration=30,
        description="Dịch vụ dùng cho integration test",
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


@pytest.fixture
def sample_service_product(
    app,
    sample_service,
    sample_product,
):
    return dao.add_service_product(
        service_id=sample_service.id,
        product_id=sample_product.id,
        default_quantity=1,
    )


@pytest.fixture
def sample_appointment(
    app,
    customer_user,
    staff_user,
    sample_service,
):
    """
    Tạo 1 lịch hẹn riêng cho từng test.
    Không dùng lại appointment của test trước.
    """

    target_date = (
        datetime.now() + timedelta(days=2)
    ).strftime("%Y-%m-%d")

    return dao.create_appointment(
        customer_id=customer_user.id,
        service_id=sample_service.id,
        staff_id=staff_user.id,
        date_str=target_date,
        time_str="09:00",
    )


@pytest.fixture
def sample_promotion(app):
    suffix = unique_suffix()
    today = datetime.now().date()

    return dao.add_promotion(
        promo_code=f"SALE_{suffix}",
        promo_type="PERCENT",
        value=10,
        start_date=today.strftime("%Y-%m-%d"),
        end_date=(
            today + timedelta(days=30)
        ).strftime("%Y-%m-%d"),
    )


@pytest.fixture
def sample_invoice(
    app,
    customer_user,
    staff_user,
    sample_service,
):
    details_data = [
        {
            "item_type": "SERVICE",
            "item_id": sample_service.id,
            "quantity": 1,
        }
    ]

    return dao.create_invoice(
        customer_id=customer_user.id,
        staff_id=staff_user.id,
        details_data=details_data,
    )