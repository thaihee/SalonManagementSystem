import uuid

import pytest
from datetime import datetime, timedelta
from app import dao
from app.models import PromotionType
from app.exceptions import ValidationError, DuplicateError, NotFoundError


class TestPromotionDAO:

    def test_add_promotion_success(self, app):
        """Tạo mã khuyến mãi thành công (theo % và theo số tiền cố định)"""
        today = datetime.now()
        end = today + timedelta(days=7)
        suffix = uuid.uuid4().hex[:8].upper()

        percent_code = f"KM{suffix}"
        fixed_code = f"FIX{suffix}"

        # 1. Tạo KM PERCENT
        p1 = dao.add_promotion(
            percent_code,
            "PERCENT",
            20,
            today.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )

        assert p1.promo_code == percent_code
        assert p1.value == 20

        # 2. Tạo KM FIXED
        p2 = dao.add_promotion(
            fixed_code,
            "FIXED",
            50000,
            today.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )

        assert p2.promo_code == fixed_code
        assert p2.value == 50000

    def test_add_promotion_invalid_percent_value_raises_validation_error(self, app):
        """Tạo khuyến mãi % vượt quá 100% hoặc <= 0 -> Ném ValidationError"""
        today = datetime.now()
        end = today + timedelta(days=7)

        with pytest.raises(ValidationError, match="Khuyến mãi theo % phải lớn hơn 0 và không vượt quá 100"):
            dao.add_promotion("OVER100", "PERCENT", 150, today.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        with pytest.raises(ValidationError, match="Khuyến mãi theo % phải lớn hơn 0 và không vượt quá 100"):
            dao.add_promotion("ZERO", "PERCENT", 0, today.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    def test_add_promotion_invalid_dates_raises_validation_error(self, app):
        """Ngày bắt đầu >= Ngày kết thúc -> Ném ValidationError"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        with pytest.raises(ValidationError, match="Ngày bắt đầu phải trước ngày kết thúc"):
            dao.add_promotion("INVALID_DATE", "PERCENT", 10, today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d"))

    def test_add_promotion_duplicate_code_raises_duplicate_error(self, app):
        """Trùng mã promo_code -> Ném DuplicateError"""
        today = datetime.now()
        end = today + timedelta(days=7)

        code = f"TRUNG{uuid.uuid4().hex[:8].upper()}"

        dao.add_promotion(
            code,
            "PERCENT",
            10,
            today.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )

        with pytest.raises(DuplicateError):
            dao.add_promotion(
                code,
                "PERCENT",
                20,
                today.strftime("%Y-%m-%d"),
                end.strftime("%Y-%m-%d")
            )

    def test_get_active_promotions_filters_expired(self, app):
        """Hàm get_active_promotions chỉ lấy mã đang còn hạn hiệu lực"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        prev_week = today - timedelta(days=7)
        next_week = today + timedelta(days=7)

        suffix = uuid.uuid4().hex[:8].upper()

        expired_code = f"EXP{suffix}"
        active_code = f"VALID{suffix}"

        # Mã đã hết hạn
        dao.add_promotion(
            expired_code,
            "PERCENT",
            10,
            prev_week.strftime("%Y-%m-%d"),
            yesterday.strftime("%Y-%m-%d")
        )

        # Mã đang có hiệu lực
        dao.add_promotion(
            active_code,
            "PERCENT",
            15,
            prev_week.strftime("%Y-%m-%d"),
            next_week.strftime("%Y-%m-%d")
        )

        active_promos = dao.get_active_promotions()
        active_codes = [p.promo_code for p in active_promos]

        assert active_code in active_codes
        assert expired_code not in active_codes

    def test_update_promotion_success(self, app):
        """Cập nhật thông tin khuyến mãi -> Thành công"""
        today = datetime.now()
        end = today + timedelta(days=7)
        suffix = uuid.uuid4().hex[:8].upper()

        old_code = f"OLD{suffix}"
        new_code = f"NEW{suffix}"

        p = dao.add_promotion(
            old_code,
            "PERCENT",
            10,
            today.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )

        updated_p = dao.update_promotion(
            p.id,
            new_code,
            "FIXED",
            20000,
            today.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )

        assert updated_p.promo_code == new_code
        assert updated_p.value == 20000

    def test_delete_promotion_hard_vs_soft_delete(
            self, app, sample_invoice, receptionist_user
    ):
        """Test cơ chế xóa: Chưa dùng -> Hard Delete; Đã dùng trong Hóa đơn -> Soft Delete (active=False)"""
        today = datetime.now()
        end = today + timedelta(days=7)
        suffix = uuid.uuid4().hex[:8].upper()

        unused_code = f"UNUSED{suffix}"
        used_code = f"USED{suffix}"

        # 1. Mã chưa dùng -> Hard Delete
        p_unused = dao.add_promotion(
            unused_code,
            "PERCENT",
            10,
            today.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )

        p_unused_id = p_unused.id
        dao.delete_promotion(p_unused_id)

        assert dao.get_promotion_by_id(p_unused_id) is None

        # 2. Mã đã dùng trong hóa đơn -> Soft Delete
        p_used = dao.add_promotion(
            used_code,
            "PERCENT",
            10,
            today.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )

        dao.confirm_invoice_payment(
            sample_invoice.id,
            receptionist_user.id,
            "CASH",
            promotion_id=p_used.id
        )

        dao.delete_promotion(p_used.id)

        deleted_promo = dao.get_promotion_by_id(p_used.id)

        assert deleted_promo is not None
        assert deleted_promo.active is False