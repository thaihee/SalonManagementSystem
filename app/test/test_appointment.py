import pytest
from datetime import datetime, timedelta, time
from types import SimpleNamespace  # Sử dụng SimpleNamespace để bọc ID thuần
from app import dao, db
from app.models import Appointment, AppointmentStatus, UserRole
from app.exceptions import ValidationError, NotFoundError


# =========================================================================
# FIXTURE TẠO DỮ LIỆU MẪU (BÓC TÁCH ID THUẦN TÚY)
# =========================================================================
@pytest.fixture
def setup_data(app):
    with app.app_context():
        # Dịch vụ 1: 30 phút (Active)
        s30 = dao.add_service(name="Cắt tóc nam 30p", price=100000, duration=30)
        # Dịch vụ 2: 45 phút (Active)
        s45 = dao.add_service(name="Gội đầu 45p", price=150000, duration=45)
        # Dịch vụ 3: Inactive
        s_inactive = dao.add_service(name="Dịch vụ cũ", price=50000, duration=30)
        dao.delete_service(s_inactive.id)

        # Nhân viên active
        staff = dao.add_user(
            full_name="Nhân viên A", username="staffa", password="Password1",
            phone="0988888888", email="staffa@example.com", role=UserRole.STAFF
        )
        # Khách hàng
        customer = dao.add_user(
            full_name="Khách B", username="custb", password="Password1",
            phone="0977777777", email="custb@example.com", role=UserRole.CUSTOMER
        )
        # Nhân viên inactive
        staff_inactive = dao.add_user(
            full_name="Nhân viên Nghỉ", username="staffoff", password="Password1",
            phone="0966666666", email="staffoff@example.com", role=UserRole.STAFF
        )
        dao.delete_user_soft(staff_inactive.id)

        # Bóc tách lấy ID thuần ngay khi Session còn sống
        return {
            "s30": SimpleNamespace(id=s30.id),
            "s45": SimpleNamespace(id=s45.id),
            "s_inactive": SimpleNamespace(id=s_inactive.id),
            "staff": SimpleNamespace(id=staff.id),
            "staff_inactive": SimpleNamespace(id=staff_inactive.id),
            "customer": SimpleNamespace(id=customer.id)
        }


# =========================================================================
# PHẦN 1: UNIT TEST LOGIC HÀM DAO
# =========================================================================

def test_slots_future_empty_day(app, setup_data):
    """1. Ngày tương lai rảnh hoàn toàn -> Trả về danh sách giờ 08:00 - 19:30"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=tomorrow_str,
            staff_id=setup_data["staff"].id
        )
        assert "08:00" in slots
        assert "19:30" in slots
        assert "20:00" not in slots


def test_slots_edge_case_closing_time_boundary(app, setup_data):
    """2. Edge case GIỜ ĐÓNG CỬA (20:00)"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        slots_30 = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=tomorrow_str,
            staff_id=setup_data["staff"].id
        )
        assert "19:30" in slots_30

        slots_45 = dao.get_available_slots(
            service_id=setup_data["s45"].id,
            date_str=tomorrow_str,
            staff_id=setup_data["staff"].id
        )
        assert "19:00" in slots_45
        assert "19:30" not in slots_45


def test_slots_past_date_returns_empty(app, setup_data):
    """3. Tra cứu ngày quá khứ -> Trả về []"""
    with app.app_context():
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        slots = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=yesterday_str,
            staff_id=setup_data["staff"].id
        )
        assert slots == []


def test_slots_today_filters_past_hours(app, setup_data):
    """4. Tra cứu HÔM NAY -> Tự động lọc bỏ các giờ đã trôi qua"""
    with app.app_context():
        today_str = datetime.now().strftime("%Y-%m-%d")
        slots = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=today_str,
            staff_id=setup_data["staff"].id
        )
        now_time_str = datetime.now().strftime("%H:%M")

        for slot in slots:
            assert slot > now_time_str


def test_slots_edge_case_start_of_day_overlap(app, setup_data):
    """5. Edge case ĐẦU CA: Lịch hẹn 08:00 (45p) -> Ẩn 08:00 & 08:30"""
    with app.app_context():
        tomorrow = datetime.now() + timedelta(days=1)
        booking_dt = datetime.combine(tomorrow.date(), time(8, 0))

        appt = Appointment(
            appointment_date=booking_dt,
            customer_id=setup_data["customer"].id,
            staff_id=setup_data["staff"].id,
            service_id=setup_data["s45"].id,
            status=AppointmentStatus.CONFIRMED
        )
        db.session.add(appt)
        db.session.commit()

        slots = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=tomorrow.strftime("%Y-%m-%d"),
            staff_id=setup_data["staff"].id
        )
        assert "08:00" not in slots
        assert "08:30" not in slots
        assert "09:00" in slots


def test_slots_middle_day_overlap(app, setup_data):
    """6. Trùng lịch giữa ngày 14:00 (30p) -> Chỉ ẩn 14:00"""
    with app.app_context():
        tomorrow = datetime.now() + timedelta(days=1)
        booking_dt = datetime.combine(tomorrow.date(), time(14, 0))

        appt = Appointment(
            appointment_date=booking_dt,
            customer_id=setup_data["customer"].id,
            staff_id=setup_data["staff"].id,
            service_id=setup_data["s30"].id,
            status=AppointmentStatus.CONFIRMED
        )
        db.session.add(appt)
        db.session.commit()

        slots = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=tomorrow.strftime("%Y-%m-%d"),
            staff_id=setup_data["staff"].id
        )
        assert "13:30" in slots
        assert "14:00" not in slots
        assert "14:30" in slots


def test_slots_cancelled_status_frees_slot(app, setup_data):
    """7. Lịch hẹn CANCELLED -> Khung giờ mở lại bình thường"""
    with app.app_context():
        tomorrow = datetime.now() + timedelta(days=1)
        booking_dt = datetime.combine(tomorrow.date(), time(10, 0))

        appt = Appointment(
            appointment_date=booking_dt,
            customer_id=setup_data["customer"].id,
            staff_id=setup_data["staff"].id,
            service_id=setup_data["s30"].id,
            status=AppointmentStatus.CANCELLED
        )
        db.session.add(appt)
        db.session.commit()

        slots = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=tomorrow.strftime("%Y-%m-%d"),
            staff_id=setup_data["staff"].id
        )
        assert "10:00" in slots


def test_slots_other_statuses_block_slot(app, setup_data):
    """8. Trạng thái COMPLETED đều chiếm dụng khung giờ"""
    with app.app_context():
        tomorrow = datetime.now() + timedelta(days=1)

        a1 = Appointment(
            appointment_date=datetime.combine(tomorrow.date(), time(11, 0)),
            customer_id=setup_data["customer"].id,
            staff_id=setup_data["staff"].id,
            service_id=setup_data["s30"].id,
            status=AppointmentStatus.COMPLETED
        )
        a2 = Appointment(
            appointment_date=datetime.combine(tomorrow.date(), time(15, 0)),
            customer_id=setup_data["customer"].id,
            staff_id=setup_data["staff"].id,
            service_id=setup_data["s30"].id,
            status=AppointmentStatus.COMPLETED
        )
        db.session.add_all([a1, a2])
        db.session.commit()

        slots = dao.get_available_slots(
            service_id=setup_data["s30"].id,
            date_str=tomorrow.strftime("%Y-%m-%d"),
            staff_id=setup_data["staff"].id
        )
        assert "11:00" not in slots
        assert "15:00" not in slots


def test_slots_invalid_service_throws_error(app, setup_data):
    """9. Báo NotFoundError khi Service ID không tồn tại hoặc đã bị ẩn"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        with pytest.raises(NotFoundError):
            dao.get_available_slots(service_id=99999, date_str=tomorrow_str)

        with pytest.raises(NotFoundError):
            dao.get_available_slots(service_id=setup_data["s_inactive"].id, date_str=tomorrow_str)


def test_slots_invalid_staff_throws_error(app, setup_data):
    """10. Báo NotFoundError khi Staff ID rác / inactive / không phải Role STAFF"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        with pytest.raises(NotFoundError):
            dao.get_available_slots(service_id=setup_data["s30"].id, date_str=tomorrow_str, staff_id=99999)

        with pytest.raises(NotFoundError):
            dao.get_available_slots(service_id=setup_data["s30"].id, date_str=tomorrow_str, staff_id=setup_data["staff_inactive"].id)

        with pytest.raises(NotFoundError):
            dao.get_available_slots(service_id=setup_data["s30"].id, date_str=tomorrow_str, staff_id=setup_data["customer"].id)


def test_slots_invalid_date_format_throws_error(app, setup_data):
    """11. Báo ValidationError khi truyền định dạng ngày sai"""
    with app.app_context():
        with pytest.raises(ValidationError):
            dao.get_available_slots(service_id=setup_data["s30"].id, date_str="31-12-2026")


# =========================================================================
# PHẦN 2: INTEGRATION TEST ROUTE API
# =========================================================================

def test_api_get_available_slots_success(client, setup_data):
    """12. Gọi API GET /appointments/available-slots thành công (HTTP 200)"""
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"/appointments/available-slots?service_id={setup_data['s30'].id}&staff_id={setup_data['staff'].id}&date={tomorrow_str}"

    response = client.get(url)
    assert response.status_code == 200

    data = response.get_json()
    assert "available_slots" in data
    assert data["date"] == tomorrow_str
    assert isinstance(data["available_slots"], list)


def test_api_get_available_slots_missing_params(client):
    """13. Gọi API thiếu tham số bắt buộc -> Trả về HTTP 400"""
    response = client.get("/appointments/available-slots?service_id=1")
    assert response.status_code == 400


def test_api_get_available_slots_not_found(client, setup_data):
    """14. Gọi API truyền service_id không tồn tại -> Trả về HTTP 404"""
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"/appointments/available-slots?service_id=9999&date={tomorrow_str}"

    response = client.get(url)
    assert response.status_code == 404


# =========================================================================
# PHẦN 3: TEST CHO NGHIỆP VỤ THÊM LỊCH HẸN (CREATE)
# =========================================================================

def test_create_appointment_dao_success(app, setup_data):
    """15. [DAO] Tạo lịch hẹn thành công"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="09:00",
            note="Khách muốn cắt ngắn"
        )
        assert appt.id is not None
        assert appt.status == AppointmentStatus.CONFIRMED
        assert appt.note == "Khách muốn cắt ngắn"


def test_create_appointment_dao_conflict_slot(app, setup_data):
    """16. [DAO] Báo ValidationError khi đặt trùng khung giờ đã có người đặt"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        # Đặt lần 1
        dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="10:00"
        )

        # Đặt trùng lần 2 -> Báo lỗi
        with pytest.raises(ValidationError):
            dao.create_appointment(
                customer_id=setup_data["customer"].id,
                service_id=setup_data["s30"].id,
                staff_id=setup_data["staff"].id,
                date_str=tomorrow_str,
                time_str="10:00"
            )


def test_api_create_appointment_success(client, setup_data):
    """17. [API] POST /appointments tạo lịch thành công (HTTP 201)"""
    # Simulate login
    with client.session_transaction() as sess:
        sess['_user_id'] = str(setup_data["customer"].id)

    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    payload = {
        "service_id": setup_data["s30"].id,
        "staff_id": setup_data["staff"].id,
        "date": tomorrow_str,
        "time": "14:00",
        "note": "Tạo qua API"
    }

    response = client.post('/appointments', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["appointment"]["status"] == "CONFIRMED"


# =========================================================================
# PHẦN 4: TEST CHO NGHIỆP VỤ HỦY / XÓA LỊCH HẸN (CANCEL/DELETE)
# =========================================================================

def test_cancel_appointment_dao_success(app, setup_data):
    """18. [DAO] Hủy lịch hẹn thành công chuyển status sang CANCELLED"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="11:00"
        )

        cancelled_appt = dao.cancel_appointment(appt.id)
        assert cancelled_appt.status == AppointmentStatus.CANCELLED


def test_cancel_appointment_dao_already_cancelled(app, setup_data):
    """19. [DAO] Báo ValidationError khi cố hủy lịch hẹn đã bị hủy trước đó"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="11:30"
        )
        dao.cancel_appointment(appt.id)

        with pytest.raises(ValidationError):
            dao.cancel_appointment(appt.id)


def test_api_cancel_appointment_success(client, setup_data):
    """20. [API] PATCH /appointments/<id>/cancel thành công (HTTP 200)"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(setup_data["customer"].id)

    with client.application.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="15:00"
        )
        appt_id = appt.id

    response = client.patch(f'/appointments/{appt_id}/cancel')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "CANCELLED"


# =========================================================================
# PHẦN 5: TEST CHO NGHIỆP VỤ SỬA LỊCH HẸN (UPDATE)
# =========================================================================

def test_update_appointment_dao_change_time_success(app, setup_data):
    """21. [DAO] Đổi giờ/ngày hẹn thành công"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="16:00"
        )

        updated_appt = dao.update_appointment(
            appointment_id=appt.id,
            date_str=tomorrow_str,
            time_str="16:30",
            note="Đổi sang 16h30"
        )
        assert updated_appt.appointment_date.strftime("%H:%M") == "16:30"
        assert updated_appt.note == "Đổi sang 16h30"


def test_update_appointment_dao_cancelled_fails(app, setup_data):
    """22. [DAO] Báo ValidationError khi cố chỉnh sửa lịch đã hủy"""
    with app.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="17:00"
        )
        dao.cancel_appointment(appt.id)

        with pytest.raises(ValidationError):
            dao.update_appointment(appointment_id=appt.id, note="Cố sửa lịch đã hủy")


def test_api_update_appointment_success(client, setup_data):
    """23. [API] PUT /appointments/<id> cập nhật thành công (HTTP 200)"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(setup_data["customer"].id)

    with client.application.app_context():
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = dao.create_appointment(
            customer_id=setup_data["customer"].id,
            service_id=setup_data["s30"].id,
            staff_id=setup_data["staff"].id,
            date_str=tomorrow_str,
            time_str="18:00"
        )
        appt_id = appt.id

    payload = {
        "date": tomorrow_str,
        "time": "18:30",
        "note": "Cập nhật ghi chú mới"
    }

    response = client.put(f'/appointments/{appt_id}', json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "18:30" in data["appointment"]["appointment_date"]
    assert data["appointment"]["note"] == "Cập nhật ghi chú mới"