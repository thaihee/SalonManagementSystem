import pytest
from datetime import datetime, timedelta
from types import SimpleNamespace
from app import dao, db
from app.models import AppointmentStatus, UserRole, InvoiceItemType, PaymentMethod
from app.exceptions import ValidationError, NotFoundError, DuplicateError


@pytest.fixture
def setup_invoice_data(app):
    with app.app_context():
        # Tạo Dịch vụ: 100k
        service = dao.add_service(name="Cắt tóc Vip", price=100000, duration=30)
        # Tạo Sản phẩm: 50k, tồn kho 10
        product = dao.add_product(name="Sáp vuốt tóc", price=50000, stock_quantity=10, min_stock_level=2)

        # Tạo Staff & Customer
        staff = dao.add_user(
            full_name="Nhân viên Thu Ngân", username="staffcashier", password="Password1",
            phone="0912345678", email="cashier@salon.com", role=UserRole.STAFF
        )
        customer = dao.add_user(
            full_name="Khách Mua Hàng", username="custbuyer", password="Password1",
            phone="0987654321", email="buyer@salon.com", role=UserRole.CUSTOMER
        )

        # Tạo Lịch hẹn
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=customer.id,
            service_id=service.id,
            staff_id=staff.id,
            date_str=tomorrow_str,
            time_str="10:00"
        )

        return {
            "service": SimpleNamespace(id=service.id, price=100000),
            "product": SimpleNamespace(id=product.id, price=50000),
            "staff": SimpleNamespace(id=staff.id),
            "customer": SimpleNamespace(id=customer.id),
            "appointment": SimpleNamespace(id=appt.id)
        }


def test_create_invoice_success_with_discount_and_stock_deduction(app, setup_invoice_data):
    """1. Tạo hóa đơn thành công, áp giảm giá 10% và tự động trừ kho sản phẩm"""
    with app.app_context():
        details = [
            {"item_type": "SERVICE", "id": setup_invoice_data["service"].id, "quantity": 1},  # 100.000
            {"item_type": "PRODUCT", "id": setup_invoice_data["product"].id, "quantity": 2}   # 50.000 * 2 = 100.000
        ]
        # Gross Total = 200.000. Giảm giá 10% -> Total = 180.000

        invoice = dao.create_invoice(
            customer_id=setup_invoice_data["customer"].id,
            staff_id=setup_invoice_data["staff"].id,
            payment_method="CASH",
            details_data=details,
            discount_percent=10,
            appointment_id=setup_invoice_data["appointment"].id
        )

        # Kiểm tra tổng tiền
        assert invoice.total_amount == 180000.0
        assert invoice.discount_percent == 10.0

        # Kiểm tra tồn kho sản phẩm giảm từ 10 -> 8
        prod = dao.get_product_by_id(setup_invoice_data["product"].id)
        assert prod.stock_quantity == 8

        # Kiểm tra lịch hẹn chuyển sang COMPLETED
        appt = dao.Appointment.query.get(setup_invoice_data["appointment"].id)
        assert appt.status == AppointmentStatus.COMPLETED


def test_create_invoice_out_of_stock_fails(app, setup_invoice_data):
    """2. Mua số lượng vượt quá tồn kho -> Báo ValidationError"""
    with app.app_context():
        details = [
            {"item_type": "PRODUCT", "id": setup_invoice_data["product"].id, "quantity": 999}
        ]

        with pytest.raises(ValidationError):
            dao.create_invoice(
                customer_id=setup_invoice_data["customer"].id,
                staff_id=setup_invoice_data["staff"].id,
                payment_method="CASH",
                details_data=details
            )


def test_create_invoice_duplicate_appointment_fails(app, setup_invoice_data):
    """3. Lịch hẹn đã lập hóa đơn rồi -> Lần 2 báo DuplicateError"""
    with app.app_context():
        details = [{"item_type": "SERVICE", "id": setup_invoice_data["service"].id, "quantity": 1}]

        # Tạo lần 1
        dao.create_invoice(
            customer_id=setup_invoice_data["customer"].id,
            staff_id=setup_invoice_data["staff"].id,
            payment_method="CASH",
            details_data=details,
            appointment_id=setup_invoice_data["appointment"].id
        )

        # Tạo lần 2 trùng appointment_id -> Lỗi
        with pytest.raises(DuplicateError):
            dao.create_invoice(
                customer_id=setup_invoice_data["customer"].id,
                staff_id=setup_invoice_data["staff"].id,
                payment_method="CASH",
                details_data=details,
                appointment_id=setup_invoice_data["appointment"].id
            )


def test_api_create_invoice_success(client, setup_invoice_data):
    """4. Test Route POST /invoices trả về HTTP 201"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(setup_invoice_data["staff"].id)

    payload = {
        "customer_id": setup_invoice_data["customer"].id,
        "payment_method": "BANK_TRANSFER",
        "discount_percent": 20,
        "details": [
            {"item_type": "SERVICE", "id": setup_invoice_data["service"].id, "quantity": 1}
        ]
    }

    response = client.post('/invoices', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["invoice"]["total_amount"] == 80000.0  # 100k - 20% = 80k
    assert data["invoice"]["payment_method"] == "BANK_TRANSFER"