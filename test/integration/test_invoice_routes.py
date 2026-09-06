import uuid

import pytest
from datetime import datetime, timedelta
from app import dao
from app.models import UserRole, InvoiceStatus


# =========================================================================
# 1. POST /invoices — Nhân viên/Admin tạo hóa đơn nháp (DRAFT)
# =========================================================================
class TestCreateInvoiceRouteDetailed:

    def test_create_invoice_unauthorized(self, client):
        """Khách chưa đăng nhập lập hóa đơn -> Redirect sang /login"""
        response = client.post('/invoices', json={})
        assert response.status_code == 302
        assert '/login' in response.location

    def test_create_invoice_customer_forbidden(self, customer_client):
        """Customer cố tình tạo hóa đơn -> 403 Forbidden (RBAC)"""
        response = customer_client.post('/invoices', json={
            'customer_id': 1,
            'details': [{'item_type': 'SERVICE', 'item_id': 1, 'quantity': 1}]
        })
        assert response.status_code == 403

    def test_create_invoice_missing_data_raises_400(self, staff_client):
        """Thiếu customer_id hoặc details -> 400 Bad Request"""
        response = staff_client.post('/invoices', json={'customer_id': 1})
        assert response.status_code == 400
        assert "Vui lòng cung cấp customer_id và danh sách chi tiết" in response.json['error']

    def test_create_invoice_success_staff(self, staff_client, customer_user, sample_service):
        """Staff tạo hóa đơn nháp thành công -> 201 Created với Status DRAFT"""
        details = [{'item_type': 'SERVICE', 'item_id': sample_service.id, 'quantity': 1}]
        response = staff_client.post('/invoices', json={
            'customer_id': customer_user.id,
            'details': details
        })
        assert response.status_code == 201
        assert response.json['invoice']['status'] == 'DRAFT'
        assert "Tạo hóa đơn nháp thành công" in response.json['message']

    def test_create_invoice_with_appointment_success(self, staff_client, sample_appointment):
        """Tạo hóa đơn từ Lịch hẹn có sẵn -> Lịch hẹn chuyển COMPLETED"""
        details = [{'item_type': 'SERVICE', 'item_id': sample_appointment.service_id, 'quantity': 1}]
        response = staff_client.post('/invoices', json={
            'customer_id': sample_appointment.customer_id,
            'appointment_id': sample_appointment.id,
            'details': details
        })
        assert response.status_code == 201

    def test_create_invoice_duplicate_appointment_raises_409(self, staff_client, sample_appointment):
        """Lập hóa đơn 2 lần cho cùng 1 Lịch hẹn -> 409 Conflict"""
        details = [{'item_type': 'SERVICE', 'item_id': sample_appointment.service_id, 'quantity': 1}]
        # Lần 1: Thành công
        staff_client.post('/invoices', json={
            'customer_id': sample_appointment.customer_id,
            'appointment_id': sample_appointment.id,
            'details': details
        })
        # Lần 2: Trùng lặp -> Bị chặn
        response = staff_client.post('/invoices', json={
            'customer_id': sample_appointment.customer_id,
            'appointment_id': sample_appointment.id,
            'details': details
        })
        assert response.status_code == 409

    def test_create_invoice_product_stock_exceeded_raises_400(self, staff_client, customer_user, sample_service,
                                                              sample_product, sample_service_product):
        """Nhập số lượng sản phẩm vượt tồn kho hiện tại -> 400 Bad Request"""
        details = [
            {'item_type': 'SERVICE', 'item_id': sample_service.id, 'quantity': 1},
            {'item_type': 'PRODUCT_USED', 'item_id': sample_product.id, 'quantity': 9999}
        ]
        response = staff_client.post('/invoices', json={
            'customer_id': customer_user.id,
            'details': details
        })
        assert response.status_code == 400

    def test_create_invoice_non_existent_customer_raises_404(self, staff_client, sample_service):
        """Tạo hóa đơn cho Khách hàng không tồn tại -> 404 Not Found"""
        details = [{'item_type': 'SERVICE', 'item_id': sample_service.id, 'quantity': 1}]
        response = staff_client.post('/invoices', json={
            'customer_id': 99999,
            'details': details
        })
        assert response.status_code == 404


# =========================================================================
# 2. GET /invoices/<id> — Xem chi tiết hóa đơn & Bảo mật IDOR
# =========================================================================
class TestGetInvoiceDetailRouteDetailed:

    def test_get_invoice_detail_success_receptionist(self, receptionist_client, sample_invoice):
        """Lễ tân xem chi tiết hóa đơn hợp lệ -> 200 OK"""
        response = receptionist_client.get(f'/invoices/{sample_invoice.id}')
        assert response.status_code == 200

    def test_get_invoice_detail_success_owner_customer(self, customer_client, sample_invoice):
        """Khách hàng chính chủ xem hóa đơn của mình -> 200 OK"""
        response = customer_client.get(f'/invoices/{sample_invoice.id}')
        assert response.status_code == 200

    def test_get_invoice_detail_not_found(self, receptionist_client):
        """Xem hóa đơn không tồn tại -> 404 Not Found"""
        response = receptionist_client.get('/invoices/99999')
        assert response.status_code == 404

    def test_get_invoice_detail_idor_protection(self, client, app, sample_invoice):
        """Khách hàng A cố tình xem hóa đơn của Khách hàng B -> 403 Forbidden"""
        suffix = uuid.uuid4().hex[:8]

        other_cust = dao.add_user(
            "Other Cust",
            f"other{suffix}",
            "Password123",
            f"09{uuid.uuid4().int % 100000000:08d}",
            f"other{suffix}@test.com",
            role=UserRole.CUSTOMER
        )
        with client.session_transaction() as sess:
            sess["user_id"] = str(other_cust.id)
            sess["_user_id"] = str(other_cust.id)

        response = client.get(f'/invoices/{sample_invoice.id}')
        assert response.status_code == 403


# =========================================================================
# 3. GET /invoices/me — Khách hàng xem lịch sử hóa đơn của mình
# =========================================================================
class TestMyInvoicesRouteDetailed:

    def test_my_invoices_unauthenticated(self, client):
        """Chưa đăng nhập xem lịch sử hóa đơn -> Redirect về /login"""
        response = client.get('/invoices/me')
        assert response.status_code == 302

    def test_my_invoices_success(self, customer_client, sample_invoice):
        """Customer xem lịch sử hóa đơn cá nhân -> 200 OK"""
        response = customer_client.get('/invoices/me')
        assert response.status_code == 200

    def test_my_invoices_filter_by_status(self, customer_client, sample_invoice):
        """Lọc danh sách hóa đơn cá nhân theo trạng thái (DRAFT/PAID) -> 200 OK"""
        response = customer_client.get('/invoices/me?status=DRAFT')
        assert response.status_code == 200

    def test_my_invoices_filter_by_date(self, customer_client, sample_invoice):
        """Lọc danh sách hóa đơn theo ngày tạo -> 200 OK"""
        today_str = datetime.now().strftime('%Y-%m-%d')
        response = customer_client.get(f'/invoices/me?date={today_str}')
        assert response.status_code == 200


# =========================================================================
# 4. GET View giao diện Nhân viên & Lễ tân
# =========================================================================
class TestStaffAndReceptionInvoiceViewsDetailed:

    def test_staff_create_invoice_view(self, staff_client, sample_service):
        """Nhân viên mở trang giao diện lập hóa đơn nháp -> 200 OK"""
        response = staff_client.get('/staff/create-invoice')
        assert response.status_code == 200

    def test_staff_invoices_list_view(self, staff_client, sample_invoice):
        """Nhân viên xem danh sách hóa đơn do mình lập -> 200 OK"""
        response = staff_client.get('/staff/invoices')
        assert response.status_code == 200

    def test_reception_invoices_list_view(self, receptionist_client, sample_invoice):
        """Lễ tân xem danh sách tất cả hóa đơn Salon -> 200 OK"""
        response = receptionist_client.get('/reception/invoices')
        assert response.status_code == 200

    def test_reception_invoice_checkout_view_draft(self, receptionist_client, sample_invoice):
        """Lễ tân mở trang thanh toán Checkout cho hóa đơn DRAFT -> 200 OK"""
        response = receptionist_client.get(f'/reception/invoice/{sample_invoice.id}/checkout')
        assert response.status_code == 200

    def test_reception_invoice_checkout_view_already_paid(self, receptionist_client, receptionist_user, sample_invoice):
        """Mở trang Checkout của hóa đơn đã PAID -> Redirect về danh sách kèm Flash message"""
        # Sửa sample_invoice.staff_id thành receptionist_user.id để thỏa mãn role RECEPTIONIST/ADMIN
        dao.confirm_invoice_payment(
            invoice_id=sample_invoice.id,
            receptionist_id=receptionist_user.id,
            payment_method="CASH"
        )
        response = receptionist_client.get(f'/reception/invoice/{sample_invoice.id}/checkout')
        assert response.status_code == 302
        assert '/reception/invoices' in response.location

# =========================================================================
# 5. PATCH /invoices/<id>/confirm-payment — Lễ tân xác nhận thanh toán
# =========================================================================
class TestConfirmInvoicePaymentRouteDetailed:

    def test_confirm_payment_unauthorized(self, client, sample_invoice):
        """Chưa đăng nhập duyệt thanh toán -> Redirect sang /login"""
        response = client.patch(f'/invoices/{sample_invoice.id}/confirm-payment', json={'payment_method': 'CASH'})
        assert response.status_code == 302

    def test_confirm_payment_forbidden_customer(self, customer_client, sample_invoice):
        """Customer cố tình tự duyệt thanh toán -> 403 Forbidden"""
        response = customer_client.patch(f'/invoices/{sample_invoice.id}/confirm-payment',
                                         json={'payment_method': 'CASH'})
        assert response.status_code == 403

    def test_confirm_payment_missing_method_raises_400(self, receptionist_client, sample_invoice):
        """Xác nhận thanh toán không truyền payment_method -> 400 Bad Request"""
        response = receptionist_client.patch(f'/invoices/{sample_invoice.id}/confirm-payment', json={})
        assert response.status_code == 400
        assert response.json['error'] == "Vui lòng chọn hình thức thanh toán!"

    def test_confirm_payment_success(self, receptionist_client, sample_invoice, sample_promotion):
        """Lễ tân duyệt thanh toán thành công (DRAFT -> PAID, áp mã giảm) -> 200 OK"""
        response = receptionist_client.patch(f'/invoices/{sample_invoice.id}/confirm-payment', json={
            'payment_method': 'CASH',
            'promotion_id': sample_promotion.id
        })
        assert response.status_code == 200
        assert response.json['message'] == "Xác nhận thanh toán thành công!"
        assert response.json['invoice']['status'] == 'PAID'
        assert response.json['invoice']['payment_method'] == 'CASH'

    def test_confirm_payment_expired_promotion_raises_400(self, receptionist_client, sample_invoice):
        """Áp dụng khuyến mãi đã hết hạn -> 400 Bad Request"""
        suffix = uuid.uuid4().hex[:8].upper()

        yesterday = datetime.now().date() - timedelta(days=2)

        expired_promo = dao.add_promotion(
            f"EXP{suffix}",
            "PERCENT",
            20,
            (yesterday - timedelta(days=5)).strftime("%Y-%m-%d"),
            yesterday.strftime("%Y-%m-%d")
        )

        response = receptionist_client.patch(
            f'/invoices/{sample_invoice.id}/confirm-payment',
            json={
                'payment_method': 'CASH',
                'promotion_id': expired_promo.id
            }
        )
        assert response.status_code == 400

    def test_confirm_payment_already_paid_raises_400(self, receptionist_client, sample_invoice):
        """Xác nhận thanh toán lần 2 khi hóa đơn đã PAID -> 400 Bad Request"""
        # Lần 1: Duyệt OK
        receptionist_client.patch(f'/invoices/{sample_invoice.id}/confirm-payment', json={'payment_method': 'CASH'})

        # Lần 2: Duyệt đè -> Báo lỗi
        response = receptionist_client.patch(f'/invoices/{sample_invoice.id}/confirm-payment',
                                             json={'payment_method': 'CASH'})
        assert response.status_code == 400