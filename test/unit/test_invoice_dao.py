import uuid

import pytest
from datetime import datetime, timedelta, date
from app import dao
from app.exceptions import ValidationError, DuplicateError, NotFoundError
from app.models import InvoiceStatus, PaymentMethod, PromotionType, InvoiceItemType


# =========================================================================
# 1. create_invoice — Lập hóa đơn NHÁP (DRAFT)
# =========================================================================
class TestCreateInvoice:

    def test_create_invoice_draft_success(self, app, customer_user, staff_user, sample_service):
        details = [{"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 1}]
        inv = dao.create_invoice(customer_user.id, staff_user.id, details_data=details)

        assert inv.id is not None
        assert inv.status == InvoiceStatus.DRAFT
        assert inv.total_amount == 100000.0  # Giá sample_service = 100,000đ
        assert len(inv.details) == 1

    def test_create_invoice_with_appointment_updates_appointment_status(self, app, sample_appointment):
        details = [{"item_type": "SERVICE", "item_id": sample_appointment.service_id, "quantity": 1}]
        inv = dao.create_invoice(
            customer_id=sample_appointment.customer_id,
            staff_id=sample_appointment.staff_id,
            details_data=details,
            appointment_id=sample_appointment.id
        )

        assert inv.appointment_id == sample_appointment.id
        # Lịch hẹn tự động chuyển sang COMPLETED
        assert sample_appointment.status.name == "COMPLETED"

    def test_create_invoice_duplicate_appointment_raises(self, app, sample_appointment):
        details = [{"item_type": "SERVICE", "item_id": sample_appointment.service_id, "quantity": 1}]
        # Lập hóa đơn lần 1
        dao.create_invoice(sample_appointment.customer_id, sample_appointment.staff_id, details, appointment_id=sample_appointment.id)

        # Lập hóa đơn đè cho cùng 1 appointment_id -> Báo lỗi
        with pytest.raises(DuplicateError):
            dao.create_invoice(sample_appointment.customer_id, sample_appointment.staff_id, details, appointment_id=sample_appointment.id)

    def test_create_invoice_empty_details_raises(self, app, customer_user, staff_user):
        with pytest.raises(ValidationError):
            dao.create_invoice(customer_user.id, staff_user.id, details_data=[])

    def test_create_invoice_without_service_line_raises(self, app, customer_user, staff_user, sample_product, sample_service_product):
        # Bắt buộc hóa đơn phải có ít nhất 1 dòng SERVICE
        details = [{"item_type": "PRODUCT_USED", "item_id": sample_product.id, "quantity": 1}]
        with pytest.raises(ValidationError):
            dao.create_invoice(customer_user.id, staff_user.id, details_data=details)

    def test_create_invoice_product_not_in_service_product_config_raises(self, app, customer_user, staff_user, sample_service):
        # Sản phẩm chưa được cấu hình ServiceProduct cho dịch vụ này
        suffix = uuid.uuid4().hex[:8]

        unlinked_prod = dao.add_product(
            f"Sáp tạo kiểu {suffix}",
            "GOI",
            stock_quantity=10,
            min_stock_level=2
        )
        details = [
            {"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 1},
            {"item_type": "PRODUCT_USED", "item_id": unlinked_prod.id, "quantity": 1}
        ]
        with pytest.raises(ValidationError):
            dao.create_invoice(customer_user.id, staff_user.id, details_data=details)

    def test_create_invoice_exceed_product_stock_quantity_raises(self, app, customer_user, staff_user, sample_service, sample_product, sample_service_product):
        # Tồn kho sample_product = 50, đòi dùng 100
        details = [
            {"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 1},
            {"item_type": "PRODUCT_USED", "item_id": sample_product.id, "quantity": 100}
        ]
        with pytest.raises(ValidationError):
            dao.create_invoice(customer_user.id, staff_user.id, details_data=details)

    def test_create_invoice_invalid_customer_or_staff_raises(self, app, customer_user, staff_user, sample_service):
        details = [{"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 1}]

        # Customer không tồn tại
        with pytest.raises(NotFoundError):
            dao.create_invoice(99999, staff_user.id, details_data=details)

        # Staff không tồn tại
        with pytest.raises(NotFoundError):
            dao.create_invoice(customer_user.id, 99999, details_data=details)


# =========================================================================
# 2. confirm_invoice_payment — Lễ tân xác nhận thanh toán (DRAFT -> PAID)
# =========================================================================
class TestConfirmInvoicePayment:

    def test_confirm_payment_success_deducts_stock(self, app, customer_user, staff_user,
                                                   receptionist_user, sample_service,
                                                   sample_product, sample_service_product):
        details = [
            {"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 1},
            {"item_type": "PRODUCT_USED", "item_id": sample_product.id, "quantity": 5}
        ]
        inv = dao.create_invoice(customer_user.id, staff_user.id, details_data=details)
        assert sample_product.stock_quantity == 50.0
        paid_inv = dao.confirm_invoice_payment(
            invoice_id=inv.id,
            receptionist_id=receptionist_user.id,
            payment_method="CASH"
        )
        assert paid_inv.status == InvoiceStatus.PAID
        assert paid_inv.payment_method == PaymentMethod.CASH
        assert paid_inv.receptionist_id == receptionist_user.id
        assert sample_product.stock_quantity == 45.0

    def test_confirm_payment_with_percent_promotion(self, app, sample_invoice, receptionist_user):
        today = datetime.now().date()
        suffix = uuid.uuid4().hex[:8].upper()
        promo = dao.add_promotion(
            f"SALE{suffix}",
            "PERCENT",
            10,
            today.strftime("%Y-%m-%d"),
            (today + timedelta(days=5)).strftime("%Y-%m-%d")
        )
        paid_inv = dao.confirm_invoice_payment(
            invoice_id=sample_invoice.id,
            receptionist_id=receptionist_user.id,
            payment_method="BANK_TRANSFER",
            promotion_id=promo.id
        )
        assert paid_inv.promotion_id == promo.id
        assert paid_inv.total_amount == 90000.0

    def test_confirm_payment_with_fixed_promotion(self, app, sample_invoice, receptionist_user):
        # Mã giảm 30k
        today = datetime.now().date()
        suffix = uuid.uuid4().hex[:8].upper()

        promo = dao.add_promotion(
            f"FIX{suffix}",
            "FIXED",
            30000,
            today.strftime("%Y-%m-%d"),
            (today + timedelta(days=5)).strftime("%Y-%m-%d")
        )

        paid_inv = dao.confirm_invoice_payment(
            invoice_id=sample_invoice.id,
            receptionist_id=receptionist_user.id,
            payment_method="CARD",
            promotion_id=promo.id
        )

        assert paid_inv.total_amount == 70000.0  # 100,000đ - 30,000đ

    def test_confirm_payment_expired_promotion_raises(self, app, sample_invoice, receptionist_user):
        # Mã hết hạn
        suffix = uuid.uuid4().hex[:8].upper()

        yesterday = datetime.now().date() - timedelta(days=2)

        expired_promo = dao.add_promotion(
            promo_code=f"EXP{suffix}",
            promo_type="PERCENT",
            value=20,
            start_date=(yesterday - timedelta(days=5)).strftime("%Y-%m-%d"),
            end_date=yesterday.strftime("%Y-%m-%d"),
        )

        with pytest.raises(ValidationError):
            dao.confirm_invoice_payment(
                invoice_id=sample_invoice.id,
                receptionist_id=receptionist_user.id,
                payment_method="CASH",
                promotion_id=expired_promo.id,
            )

    def test_confirm_payment_already_paid_raises(self, app, sample_invoice, receptionist_user):
        dao.confirm_invoice_payment(sample_invoice.id, receptionist_user.id, "CASH")
        # Duyệt thanh toán lần 2 -> Báo lỗi
        with pytest.raises(ValidationError):
            dao.confirm_invoice_payment(sample_invoice.id, receptionist_user.id, "CASH")

    def test_confirm_payment_invalid_receptionist_raises(self, app, sample_invoice, customer_user):
        # customer_user không phải RECEPTIONIST hay ADMIN
        with pytest.raises(NotFoundError):
            dao.confirm_invoice_payment(sample_invoice.id, receptionist_id=customer_user.id, payment_method="CASH")


# =========================================================================
# 3. cancel_invoice_draft & update_invoice_draft (Admin sửa/hủy đơn nháp)
# =========================================================================
class TestAdminDraftInvoiceOperations:

    def test_cancel_invoice_draft_success(self, app, sample_invoice):
        cancelled = dao.cancel_invoice_draft(sample_invoice.id)
        assert cancelled.status == InvoiceStatus.CANCELLED
        assert cancelled.active is False
        assert cancelled.appointment_id is None

    def test_cancel_non_draft_invoice_raises(self, app, sample_invoice, receptionist_user):
        dao.confirm_invoice_payment(sample_invoice.id, receptionist_user.id, "CASH")
        # Đơn đã PAID không được phép hủy
        with pytest.raises(ValidationError):
            dao.cancel_invoice_draft(sample_invoice.id)

    def test_update_invoice_draft_success(self, app, sample_invoice, sample_service):
        suffix = uuid.uuid4().hex[:8]

        new_svc = dao.add_service(
            f"Nhuộm Tóc {suffix}",
            300000,
            60
        )
        new_details = [
            {"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 1},
            {"item_type": "SERVICE", "item_id": new_svc.id, "quantity": 1}
        ]

        updated = dao.update_invoice_draft(sample_invoice.id, details_data=new_details)
        assert updated.total_amount == 400000.0  # 100k + 300k
        assert len(updated.details) == 2

    def test_update_paid_invoice_draft_raises(self, app, sample_invoice, receptionist_user, sample_service):
        dao.confirm_invoice_payment(sample_invoice.id, receptionist_user.id, "CASH")
        new_details = [{"item_type": "SERVICE", "item_id": sample_service.id, "quantity": 2}]
        with pytest.raises(ValidationError):
            dao.update_invoice_draft(sample_invoice.id, details_data=new_details)


# =========================================================================
# 4. Tra cứu Hóa đơn & Báo cáo Doanh thu (get_invoices, get_revenue_report)
# =========================================================================
class TestInvoicesQueryAndReports:

    def test_get_invoices_filters(self, app, sample_invoice, receptionist_user, customer_user, staff_user):
        dao.confirm_invoice_payment(sample_invoice.id, receptionist_user.id, "CASH")

        # Filter theo status=PAID
        invoices_paid, total = dao.get_invoices(status="PAID")
        assert sample_invoice.id in [inv.id for inv in invoices_paid]
        assert all(inv.status.name == "PAID" for inv in invoices_paid)

        # Filter theo customer_id
        invoices_cust, _ = dao.get_invoices(customer_id=customer_user.id)
        assert all(
            inv.customer_id == customer_user.id
            for inv in invoices_cust
        )

        # Filter theo staff_id
        invoices_staff, _ = dao.get_invoices(staff_id=staff_user.id)
        assert sample_invoice.id in [inv.id for inv in invoices_staff]
        assert all(
            inv.staff_id == staff_user.id
            for inv in invoices_staff
        )

    def test_get_revenue_report_grouping(
            self, app, sample_invoice, receptionist_user
    ):
        dao.confirm_invoice_payment(
            sample_invoice.id,
            receptionist_user.id,
            "CASH"
        )

        # Theo ngày
        report_day = dao.get_revenue_report(period_type="day")

        target_day = sample_invoice.invoice_date.strftime("%Y-%m-%d")
        day_row = next(
            row for row in report_day
            if row["period"] == target_day
        )

        assert day_row["total_invoices"] >= 1
        assert day_row["total_revenue"] >= 100000.0

        # Theo tháng
        report_month = dao.get_revenue_report(period_type="month")

        target_month = sample_invoice.invoice_date.strftime("%Y-%m")
        month_row = next(
            row for row in report_month
            if row["period"] == target_month
        )

        assert month_row["total_invoices"] >= 1
        assert month_row["total_revenue"] >= 100000.0

    def test_get_revenue_report_invalid_period_raises(self, app):
        with pytest.raises(ValidationError):
            dao.get_revenue_report(period_type="invalid_period")


# =========================================================================
# 5. Quản lý Khuyến mãi (Promotion CRUD)
# =========================================================================
class TestPromotionOperations:

    def test_add_promotion_success(self, app):
        today = datetime.now().date()
        suffix = uuid.uuid4().hex[:8].upper()
        promo_code = f"PROMO{suffix}"

        promo = dao.add_promotion(
            promo_code=promo_code,
            promo_type="PERCENT",
            value=15,
            start_date=today.strftime("%Y-%m-%d"),
            end_date=(today + timedelta(days=10)).strftime("%Y-%m-%d")
        )

        assert promo is not None
        assert promo.promo_code == promo_code
        assert promo.value == 15

    def test_add_promotion_duplicate_code_raises(self, app, sample_promotion):
        today = datetime.now().date()
        start_str = today.strftime("%Y-%m-%d")
        end_str = (today + timedelta(days=5)).strftime("%Y-%m-%d")  # end_date phải sau start_date

        with pytest.raises(DuplicateError):
            dao.add_promotion(sample_promotion.promo_code, "PERCENT", 10, start_str, end_str)

    def test_add_promotion_start_after_end_raises(self, app):
        today = datetime.now().date()
        start_str = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")
        with pytest.raises(ValidationError):
            dao.add_promotion("ERR_DATE", "PERCENT", 10, start_str, end_str)

    def test_update_promotion_success(self, app, sample_promotion):
        today = datetime.now().date().strftime("%Y-%m-%d")
        suffix = uuid.uuid4().hex[:8].upper()
        new_code = f"SALE{suffix}"

        updated = dao.update_promotion(
            promo_id=sample_promotion.id,
            promo_code=new_code,
            promo_type="PERCENT",
            value=20,
            start_date=today,
            end_date=sample_promotion.end_date.strftime("%Y-%m-%d")
        )

        assert updated.promo_code == new_code
        assert updated.value == 20

    def test_delete_unused_promotion_hard_delete(self, app, sample_promotion):
        assert dao.delete_promotion(sample_promotion.id) is True
        assert dao.get_promotion_by_id(sample_promotion.id) is None

    def test_delete_used_promotion_soft_delete(self, app, sample_invoice, receptionist_user, sample_promotion):
        dao.confirm_invoice_payment(sample_invoice.id, receptionist_user.id, "CASH", promotion_id=sample_promotion.id)
        # Mã đã dùng trong hóa đơn -> Chuyển active = False
        dao.delete_promotion(sample_promotion.id)
        promo_db = dao.get_promotion_by_id(sample_promotion.id)
        assert promo_db is not None
        assert promo_db.active is False