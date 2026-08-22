import pytest
from datetime import datetime, timedelta, date
from app import dao
from app.exceptions import ValidationError, NotFoundError
from app.models import AppointmentStatus, InvoiceStatus, UserRole, Appointment


# =========================================================================
# 1. get_appointment_by_id & get_appointments_by_customer & get_appointments_by_staff
# =========================================================================
class TestQueryAppointments:

    def test_get_appointment_by_id_found(self, app, sample_appointment):
        appt = dao.get_appointment_by_id(sample_appointment.id)
        assert appt is not None
        assert appt.id == sample_appointment.id

    def test_get_appointment_by_id_not_found(self, app):
        assert dao.get_appointment_by_id(99999) is None

    def test_get_appointments_by_customer_success(self, app, customer_user, sample_appointment):
        appts = dao.get_appointments_by_customer(customer_user.id)
        assert len(appts) == 1
        assert appts[0].id == sample_appointment.id
        assert hasattr(appts[0], 'has_invoice')
        assert appts[0].has_invoice is False

    def test_get_appointments_by_customer_has_invoice_flag(self, app, customer_user, sample_appointment):
        dao.create_invoice(
            customer_id=customer_user.id,
            staff_id=sample_appointment.staff_id,
            details_data=[{"item_type": "SERVICE", "item_id": sample_appointment.service_id, "quantity": 1}],
            appointment_id=sample_appointment.id
        )
        appts = dao.get_appointments_by_customer(customer_user.id)
        assert len(appts) == 1
        assert appts[0].has_invoice is True

    def test_get_appointments_by_staff_filter_by_date(self, app, staff_user, sample_appointment):
        tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appts, total = dao.get_appointments_by_staff(staff_user.id, date_str=tomorrow_str)
        assert total == 1
        assert len(appts) == 1
        assert appts[0].id == sample_appointment.id

    def test_get_appointments_by_staff_invalid_date_format_raises(self, app, staff_user):
        with pytest.raises(ValidationError):
            dao.get_appointments_by_staff(staff_user.id, date_str="31-12-2026")


# =========================================================================
# 2. get_appointments (Tra cứu lịch hẹn toàn hệ thống - Admin/Lễ tân)
# =========================================================================
class TestGetAppointmentsAdmin:

    def test_filter_by_status(self, app, sample_appointment):
        confirmed = dao.get_appointments(status="CONFIRMED")
        assert len(confirmed) == 1

        cancelled = dao.get_appointments(status="CANCELLED")
        assert len(cancelled) == 0

    def test_filter_by_customer_and_staff(self, app, sample_appointment, customer_user, staff_user):
        appts = dao.get_appointments(customer_id=customer_user.id, staff_id=staff_user.id)
        assert len(appts) == 1
        assert appts[0].id == sample_appointment.id

    def test_filter_by_date_str_and_datetime(self, app, sample_appointment):
        tomorrow_dt = datetime.now() + timedelta(days=1)
        tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")

        appts_str = dao.get_appointments(date=tomorrow_str)
        assert len(appts_str) == 1

        appts_dt = dao.get_appointments(date=tomorrow_dt)
        assert len(appts_dt) == 1

    def test_invalid_date_str_raises(self, app):
        with pytest.raises(ValidationError):
            dao.get_appointments(date="2026/12/31")


# =========================================================================
# 3. get_available_slots (Thuật toán kiểm tra khung giờ trống 08:00 - 20:00)
# =========================================================================
class TestGetAvailableSlotsDetailed:

    def test_service_inactive_raises(self, app, sample_service, staff_user):
        dao.delete_service(sample_service.id)
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        with pytest.raises(NotFoundError):
            dao.get_available_slots(sample_service.id, target_date, staff_id=staff_user.id)

    def test_staff_not_found_or_inactive_raises(self, app, sample_service, staff_user):
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

        with pytest.raises(NotFoundError):
            dao.get_available_slots(sample_service.id, target_date, staff_id=99999)

        dao.toggle_user_active(staff_user.id)
        with pytest.raises(NotFoundError):
            dao.get_available_slots(sample_service.id, target_date, staff_id=staff_user.id)

    def test_invalid_date_format_raises(self, app, sample_service):
        with pytest.raises(ValidationError):
            dao.get_available_slots(sample_service.id, "15-08-2026")

    def test_exceed_30_days_boundary_raises(self, app, sample_service):
        day_30 = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        assert isinstance(dao.get_available_slots(sample_service.id, day_30), list)

        day_31 = (date.today() + timedelta(days=31)).strftime("%Y-%m-%d")
        with pytest.raises(ValidationError):
            dao.get_available_slots(sample_service.id, day_31)

    def test_past_date_returns_empty_list(self, app, sample_service):
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert dao.get_available_slots(sample_service.id, yesterday_str) == []

    def test_slot_overlapping_calculation(self, app, customer_user, staff_user):
        # Dùng ngày cách 2 ngày tới
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        long_svc = dao.add_service("Nhuộm Tóc", 300000, 90)  # 90 phút (1.5 tiếng)

        # Lịch hẹn bận lúc 10:00 -> Chiếm khoảng giờ 10:00 - 11:30
        dao.create_appointment(
            customer_id=customer_user.id, service_id=long_svc.id,
            staff_id=staff_user.id, date_str=target_date, time_str="10:00"
        )

        slots = dao.get_available_slots(long_svc.id, target_date, staff_id=staff_user.id)

        # 08:00 -> 09:30 (Trống, không chạm 10:00) => KHẢ DỤNG
        assert "08:00" in slots

        # 09:00 -> 10:30 (Bị va chạm với khoảng 10:00-11:30) => KHÔNG KHẢ DỤNG
        assert "09:00" not in slots

        # 10:00 -> 11:30 (Trùng chính xác giờ bắt đầu) => KHÔNG KHẢ DỤNG
        assert "10:00" not in slots

        # 12:00 -> 13:30 (Trống, sau 11:30) => KHẢ DỤNG
        assert "12:00" in slots

    def test_exclude_appointment_id_keeps_original_slot(self, app, sample_appointment):
        appt_date_str = sample_appointment.appointment_date.strftime("%Y-%m-%d")

        slots = dao.get_available_slots(
            service_id=sample_appointment.service_id,
            date_str=appt_date_str,
            staff_id=sample_appointment.staff_id,
            exclude_appointment_id=sample_appointment.id
        )
        assert "09:00" in slots


# =========================================================================
# 4. create_appointment (Tạo lịch hẹn & Kiểm tra ràng buộc va chạm)
# =========================================================================
class TestCreateAppointmentDetailed:

    def test_customer_not_found_raises(self, app, sample_service):
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        with pytest.raises(NotFoundError):
            dao.create_appointment(99999, sample_service.id, date_str=target_date, time_str="10:00")

    def test_service_not_found_raises(self, app, customer_user):
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        with pytest.raises(NotFoundError):
            dao.create_appointment(customer_user.id, 99999, date_str=target_date, time_str="10:00")

    def test_invalid_time_format_raises(self, app, customer_user, sample_service):
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        with pytest.raises(ValidationError):
            dao.create_appointment(customer_user.id, sample_service.id, date_str=target_date, time_str="10:00:00")

    def test_booking_in_past_time_raises(self, app, customer_user, sample_service):
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        with pytest.raises(ValidationError):
            dao.create_appointment(customer_user.id, sample_service.id, date_str=yesterday_str, time_str="10:00")

    def test_booking_exceed_30_days_raises(self, app, customer_user, sample_service):
        day_31_str = (date.today() + timedelta(days=31)).strftime("%Y-%m-%d")
        with pytest.raises(ValidationError):
            dao.create_appointment(customer_user.id, sample_service.id, date_str=day_31_str, time_str="10:00")

    def test_unavailable_time_slot_raises(self, app, customer_user, staff_user, sample_service):
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        with pytest.raises(ValidationError):
            dao.create_appointment(customer_user.id, sample_service.id, staff_id=staff_user.id, date_str=target_date,
                                   time_str="22:00")

    def test_auto_assign_staff_finds_available_stylist(self, app, customer_user, staff_user, sample_service):
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

        # Đặt lịch hẹn ngẫu nhiên (staff_id=None) ở khung giờ rảnh 10:00
        new_appt = dao.create_appointment(customer_user.id, sample_service.id, staff_id=None, date_str=target_date,
                                          time_str="10:00")
        assert new_appt.staff_id is not None

    def test_customer_self_time_overlap_raises(self, app, customer_user, staff_user):
        svc1 = dao.add_service("Cắt tóc", 100000, 30)
        svc2 = dao.add_service("Gội đầu", 50000, 30)
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

        dao.create_appointment(customer_user.id, svc1.id, staff_user.id, target_date, "10:00")

        with pytest.raises(ValidationError):
            dao.create_appointment(customer_user.id, svc2.id, staff_id=None, date_str=target_date, time_str="10:00")

    def test_note_cleaned_and_truncated_to_255_chars(self, app, customer_user, staff_user, sample_service):
        target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        long_note = "   " + "A" * 300 + "   "
        appt = dao.create_appointment(
            customer_user.id, sample_service.id, staff_user.id,
            target_date, "15:00", note=long_note
        )
        assert len(appt.note) == 255
        assert appt.note == "A" * 255


# =========================================================================
# 5. cancel_appointment (Hủy lịch hẹn)
# =========================================================================
class TestCancelAppointmentDetailed:

    def test_cancel_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.cancel_appointment(99999)

    def test_cancel_less_than_2_hours_boundary_raises(self, app, customer_user, staff_user, sample_service):
        near_future = datetime.now() + timedelta(hours=1, minutes=30)
        appt = Appointment(
            customer_id=customer_user.id, service_id=sample_service.id,
            staff_id=staff_user.id, appointment_date=near_future, status=AppointmentStatus.CONFIRMED
        )
        dao.db.session.add(appt)
        dao.db.session.commit()

        with pytest.raises(ValidationError):
            dao.cancel_appointment(appt.id)

    def test_cancel_already_has_invoice_raises(self, app, sample_appointment):
        dao.create_invoice(
            customer_id=sample_appointment.customer_id,
            staff_id=sample_appointment.staff_id,
            details_data=[{"item_type": "SERVICE", "item_id": sample_appointment.service_id, "quantity": 1}],
            appointment_id=sample_appointment.id
        )
        with pytest.raises(ValidationError):
            dao.cancel_appointment(sample_appointment.id)

    def test_cancel_already_cancelled_raises(self, app, sample_appointment):
        dao.cancel_appointment(sample_appointment.id)
        with pytest.raises(ValidationError):
            dao.cancel_appointment(sample_appointment.id)

    def test_cancel_completed_appointment_raises(self, app, sample_appointment):
        sample_appointment.status = AppointmentStatus.COMPLETED
        dao.db.session.commit()

        with pytest.raises(ValidationError):
            dao.cancel_appointment(sample_appointment.id)


# =========================================================================
# 6. update_appointment (Cập nhật lịch hẹn)
# =========================================================================
class TestUpdateAppointmentDetailed:

    def test_update_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.update_appointment(99999, note="Sửa thử")

    def test_update_less_than_2_hours_raises(self, app, customer_user, staff_user, sample_service):
        near_future = datetime.now() + timedelta(hours=1)
        appt = Appointment(
            customer_id=customer_user.id, service_id=sample_service.id,
            staff_id=staff_user.id, appointment_date=near_future, status=AppointmentStatus.CONFIRMED
        )
        dao.db.session.add(appt)
        dao.db.session.commit()

        with pytest.raises(ValidationError):
            dao.update_appointment(appt.id, note="Sửa gấp")

    def test_update_appointment_with_invoice_raises(self, app, sample_appointment):
        dao.create_invoice(
            customer_id=sample_appointment.customer_id,
            staff_id=sample_appointment.staff_id,
            details_data=[{"item_type": "SERVICE", "item_id": sample_appointment.service_id, "quantity": 1}],
            appointment_id=sample_appointment.id
        )
        with pytest.raises(ValidationError):
            dao.update_appointment(sample_appointment.id, note="Đổi thông tin")

    def test_update_cancelled_or_completed_raises(self, app, sample_appointment):
        dao.cancel_appointment(sample_appointment.id)
        with pytest.raises(ValidationError):
            dao.update_appointment(sample_appointment.id, note="Sửa lại lịch đã hủy")

    def test_update_status_by_str_success(self, app, sample_appointment):
        updated = dao.update_appointment(sample_appointment.id, status="COMPLETED")
        assert updated.status == AppointmentStatus.COMPLETED

    def test_update_status_by_enum_success(self, app, sample_appointment):
        updated = dao.update_appointment(sample_appointment.id, status=AppointmentStatus.CONFIRMED)
        assert updated.status == AppointmentStatus.CONFIRMED

    def test_update_invalid_status_str_raises(self, app, sample_appointment):
        with pytest.raises(ValidationError):
            dao.update_appointment(sample_appointment.id, status="INVALID_STATUS")

    def test_update_new_time_and_service_success(self, app, sample_appointment):
        new_svc = dao.add_service("Uốn Tóc", 200000, 60)
        day_5 = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")

        updated = dao.update_appointment(
            sample_appointment.id,
            service_id=new_svc.id,
            date_str=day_5,
            time_str="14:00"
        )

        assert updated.service_id == new_svc.id
        assert updated.appointment_date.strftime("%Y-%m-%d %H:%M") == f"{day_5} 14:00"