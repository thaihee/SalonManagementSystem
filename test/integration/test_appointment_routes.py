import uuid

import pytest
from datetime import datetime, date, timedelta
from app import dao
from app.models import AppointmentStatus, UserRole


# =========================================================================
# 1. GET /booking & GET /appointments/available-slots
# =========================================================================
class TestBookingViewAndSlotsDetailed:

    def test_booking_view_unauthenticated(self, client):
        """Khách chưa đăng nhập vào /booking -> Redirect sang /login"""
        response = client.get('/booking')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_booking_view_authenticated_success(self, customer_client, sample_service):
        """Khách đã đăng nhập xem form đặt lịch kèm service_id -> 200 OK"""
        response = customer_client.get(f'/booking?service_id={sample_service.id}')
        assert response.status_code == 200

    def test_get_available_slots_missing_params_raises_400(
            self,
            customer_client
    ):
        """
        Gọi API tra cứu slot thiếu date hoặc service_id
        -> 400 Bad Request
        """
        response = customer_client.get(
            '/appointments/available-slots?service_id=1'
        )

        assert response.status_code == 400
        assert (
                response.json['error']
                == "Thiếu service_id hoặc date!"
        )

    def test_get_available_slots_non_existent_service_raises_404(
            self,
            customer_client
    ):
        """
        Tra cứu slot cho Dịch vụ không tồn tại
        -> 404 Not Found
        """
        target_date = (
                date.today() + timedelta(days=2)
        ).strftime('%Y-%m-%d')

        response = customer_client.get(
            '/appointments/available-slots'
            f'?service_id=99999'
            f'&date={target_date}'
        )

        assert response.status_code == 404

    def test_get_available_slots_success(
            self,
            customer_client,
            sample_service,
            staff_user
    ):
        """
        Tra cứu khung giờ trống hợp lệ
        -> 200 OK kèm danh sách slots
        """
        target_date = (
                date.today() + timedelta(days=2)
        ).strftime('%Y-%m-%d')

        response = customer_client.get(
            '/appointments/available-slots'
            f'?service_id={sample_service.id}'
            f'&date={target_date}'
            f'&staff_id={staff_user.id}'
        )

        assert response.status_code == 200
        assert response.json['date'] == target_date
        assert isinstance(
            response.json['available_slots'],
            list
        )

    def test_get_available_slots_exclude_appointment_id(
            self,
            customer_client,
            sample_appointment
    ):
        """
        Tra cứu slot khi đang chỉnh sửa lịch hẹn gốc
        (exclude appointment hiện tại)
        -> 200 OK
        """
        target_date = (
            sample_appointment
            .appointment_date
            .strftime('%Y-%m-%d')
        )

        response = customer_client.get(
            '/appointments/available-slots'
            f'?service_id={sample_appointment.service_id}'
            f'&date={target_date}'
            f'&staff_id={sample_appointment.staff_id}'
            f'&appointment_id={sample_appointment.id}'
        )

        assert response.status_code == 200


# =========================================================================
# 2. POST /appointments (Tạo lịch hẹn) & Chống IDOR
# =========================================================================
class TestCreateAppointmentRouteDetailed:

    def test_create_appointment_unauthenticated(self, client, sample_service):
        """Chưa đăng nhập gọi API tạo lịch hẹn -> Redirect sang /login"""
        target_date = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        response = client.post('/appointments', json={
            'service_id': sample_service.id,
            'date': target_date,
            'time': '10:00'
        })
        assert response.status_code == 302

    def test_create_appointment_customer_success(self, customer_client, sample_service, staff_user):
        """Khách hàng tự tạo lịch hẹn thành công -> 201 Created với status CONFIRMED"""
        target_date = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        response = customer_client.post('/appointments', json={
            'service_id': sample_service.id,
            'staff_id': staff_user.id,
            'date': target_date,
            'time': '10:00',
            'note': 'Cắt tóc kiểu Layer'
        })
        assert response.status_code == 201
        assert response.json['message'] == "Đặt lịch hẹn thành công!"
        assert response.json['appointment']['status'] == "CONFIRMED"

    def test_create_appointment_without_staff_success(
            self,
            customer_client,
            sample_service
    ):
        """
        Customer không chỉ định Stylist
        -> hệ thống tự động gán 1 Stylist khả dụng.
        """

        target_date = (
                date.today() + timedelta(days=2)
        ).strftime('%Y-%m-%d')

        slot_response = customer_client.get(
            '/appointments/available-slots'
            f'?service_id={sample_service.id}'
            f'&date={target_date}'
        )

        assert slot_response.status_code == 200

        available_slots = (
            slot_response.json['available_slots']
        )

        assert available_slots

        selected_time = available_slots[0]

        response = customer_client.post(
            '/appointments',
            json={
                'service_id': sample_service.id,
                'date': target_date,
                'time': selected_time
            }
        )

        assert response.status_code == 201

        assert (
                response.json['appointment']['staff_id']
                is not None
        )

    def test_create_appointment_missing_required_fields_raises_400(self, customer_client):
        """Tạo lịch hẹn thiếu thông tin (thiếu giờ/ngày/dịch vụ) -> 400 Bad Request"""
        response = customer_client.post('/appointments', json={'service_id': 1})
        assert response.status_code == 400
        assert "Vui lòng cung cấp đầy đủ" in response.json['error']

    def test_create_appointment_past_date_raises_400(self, customer_client, sample_service):
        """Đặt lịch hẹn trong quá khứ -> 400 Bad Request"""
        yesterday_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        response = customer_client.post('/appointments', json={
            'service_id': sample_service.id,
            'date': yesterday_str,
            'time': '10:00'
        })
        assert response.status_code == 400

    def test_create_appointment_customer_self_overlap_raises_400(self, customer_client, sample_service, staff_user):
        """Khách hàng cố tình đặt 2 lịch hẹn trùng giờ nhau -> 400 Bad Request"""
        target_date = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        # Lần 1: Thành công
        customer_client.post('/appointments', json={
            'service_id': sample_service.id, 'staff_id': staff_user.id,
            'date': target_date, 'time': '14:00'
        })
        # Lần 2: Trùng đè -> Bị chặn
        response = customer_client.post('/appointments', json={
            'service_id': sample_service.id, 'staff_id': staff_user.id,
            'date': target_date, 'time': '14:00'
        })
        assert response.status_code == 400

    def test_create_appointment_idor_protection(
            self,
            customer_client,
            customer_user,
            sample_service
    ):
        """
        Customer truyền customer_id giả
        -> backend phải bỏ ID giả,
           dùng ID user đang đăng nhập.
        """

        target_date = (
                date.today() + timedelta(days=3)
        ).strftime('%Y-%m-%d')

        slot_response = customer_client.get(
            '/appointments/available-slots'
            f'?service_id={sample_service.id}'
            f'&date={target_date}'
        )

        assert slot_response.status_code == 200

        available_slots = (
            slot_response.json['available_slots']
        )

        assert available_slots

        selected_time = available_slots[0]

        response = customer_client.post(
            '/appointments',
            json={
                'customer_id': 99999,
                'service_id': sample_service.id,
                'date': target_date,
                'time': selected_time
            }
        )

        assert response.status_code == 201

        # customer_id giả phải bị bỏ qua
        assert (
                response.json['appointment']['customer_id']
                == customer_user.id
        )

        # Hệ thống phải tự gán một stylist khả dụng
        assert (
                response.json['appointment']['staff_id']
                is not None
        )


# =========================================================================
# 3. PUT /appointments/<id> & PATCH /appointments/<id>/cancel & IDOR
# =========================================================================
class TestUpdateAndCancelAppointmentRoutesDetailed:

    def test_update_appointment_customer_success(self, customer_client, sample_appointment):
        """Khách hàng sửa ngày/giờ/ghi chú lịch hẹn của mình -> 200 OK"""
        target_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        response = customer_client.put(f'/appointments/{sample_appointment.id}', json={
            'date': target_date,
            'time': '15:00',
            'note': 'Đã đổi giờ sang 15:00'
        })
        assert response.status_code == 200
        assert response.json['message'] == "Cập nhật lịch hẹn thành công!"

    def test_update_appointment_customer_cannot_change_status_idor(self, customer_client, sample_appointment):
        """Customer không được tự ý đổi status lịch hẹn -> 403 Forbidden"""
        response = customer_client.put(f'/appointments/{sample_appointment.id}', json={
            'status': 'COMPLETED'
        })
        assert response.status_code == 403
        assert response.json['error'] == "Bạn không có quyền thay đổi trạng thái lịch hẹn!"

    def test_update_appointment_staff_can_change_status_success(self, staff_client, sample_appointment):
        """Staff hoặc Admin đổi status lịch hẹn -> 200 OK"""
        response = staff_client.put(f'/appointments/{sample_appointment.id}', json={
            'status': 'COMPLETED'
        })
        assert response.status_code == 200
        assert response.json['appointment']['status'] == 'COMPLETED'

    def test_update_appointment_other_customer_idor_blocked(self, client, app, sample_appointment):
        """Customer A sửa lịch hẹn của Customer B -> 403 Forbidden"""
        suffix = uuid.uuid4().hex[:8]

        other_cust = dao.add_user(
            "Cust B",
            f"custb{suffix}",
            "Password123",
            f"09{uuid.uuid4().int % 100000000:08d}",
            f"custb{suffix}@test.com",
            role=UserRole.CUSTOMER
        )
        with client.session_transaction() as sess:
            sess["user_id"] = str(other_cust.id)
            sess["_user_id"] = str(other_cust.id)

        response = client.put(f'/appointments/{sample_appointment.id}', json={'note': 'Hack note'})
        assert response.status_code == 403
        assert response.json['error'] == "Bạn không có quyền sửa lịch hẹn này!"

    def test_cancel_appointment_customer_success(self, customer_client, sample_appointment):
        """Khách hàng hủy lịch hẹn của chính mình -> 200 OK"""
        response = customer_client.patch(f'/appointments/{sample_appointment.id}/cancel')
        assert response.status_code == 200
        assert response.json['message'] == "Hủy lịch hẹn thành công!"
        assert response.json['status'] == "CANCELLED"

    def test_cancel_appointment_other_customer_idor_blocked(self, client, sample_appointment):
        """Customer A hủy lịch hẹn của Customer B -> 403 Forbidden"""
        suffix = uuid.uuid4().hex[:8]

        other_cust = dao.add_user(
            "Cust C",
            f"custc{suffix}",
            "Password123",
            f"09{uuid.uuid4().int % 100000000:08d}",
            f"custc{suffix}@test.com",
            role=UserRole.CUSTOMER
        )
        with client.session_transaction() as sess:
            sess["user_id"] = str(other_cust.id)
            sess["_user_id"] = str(other_cust.id)

        response = client.patch(f'/appointments/{sample_appointment.id}/cancel')
        assert response.status_code == 403

    def test_cancel_non_existent_appointment_raises_404(self, customer_client):
        """Hủy lịch hẹn không tồn tại -> 404 Not Found"""
        response = customer_client.patch('/appointments/99999/cancel')
        assert response.status_code == 404


# =========================================================================
# 4. VIEW & API ROUTES: Tra cứu & Danh sách lịch hẹn
# =========================================================================
class TestAppointmentViewsAndAPIsDetailed:

    def test_my_appointments_view_customer_unauthenticated(self, client):
        """Chưa đăng nhập xem lịch hẹn cá nhân -> Redirect về /login"""
        response = client.get('/appointments/me')
        assert response.status_code == 302

    def test_my_appointments_view_customer_success(self, customer_client, sample_appointment):
        """Khách hàng xem danh sách 'Lịch hẹn của tôi' -> 200 OK"""
        response = customer_client.get('/appointments/me')
        assert response.status_code == 200

    def test_my_appointments_view_customer_filters(self, customer_client, sample_appointment):
        """Khách hàng lọc lịch hẹn cá nhân theo status và date -> 200 OK"""
        target_date = sample_appointment.appointment_date.strftime('%Y-%m-%d')
        response = customer_client.get(f'/appointments/me?status=CONFIRMED&date={target_date}')
        assert response.status_code == 200

    def test_staff_appointments_view_authorized(self, staff_client, sample_appointment):
        """Nhân viên xem giao diện danh sách lịch hẹn được giao -> 200 OK"""
        response = staff_client.get('/staff/appointments')
        assert response.status_code == 200

    def test_reception_appointments_view_authorized(self, receptionist_client, sample_appointment):
        """Lễ tân tra cứu danh sách lịch hẹn toàn hệ thống -> 200 OK"""
        response = receptionist_client.get('/reception/appointments')
        assert response.status_code == 200

    def test_staff_appointments_api_success(self, staff_client, sample_appointment):
        """Nhân viên gọi API lấy JSON danh sách lịch hẹn -> 200 OK"""
        response = staff_client.get('/api/staff/appointments')
        assert response.status_code == 200
        assert 'appointments' in response.json
        assert len(response.json['appointments']) >= 1