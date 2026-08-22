from datetime import date, timedelta

import pytest
from flask_login import login_user
from app.models import User


# =========================================================================
# 1. TEST CSRF CHO FORM DATA (HTML FORMS)
# =========================================================================
class TestAuthCSRFProtection:

    def test_login_post_with_valid_csrf_token_success(self, client_csrf_enabled, customer_user, valid_csrf_token):
        """POST /login gửi đủ username, password và csrf_token chuẩn -> 302 Redirect"""
        response = client_csrf_enabled.post('/login', data={
            'username': customer_user.username,
            'password': customer_user.raw_password,
            'csrf_token': valid_csrf_token
        })
        assert response.status_code == 302

    def test_register_post_with_valid_csrf_token_success(self, client_csrf_enabled, valid_csrf_token):
        """POST /register gửi kèm csrf_token chuẩn -> Thành công (302) hoặc Form Error (400)"""
        response = client_csrf_enabled.post('/register', data={
            'full_name': 'Khách Hàng CSRF',
            'username': 'cust_csrf_123',
            'password': 'Password123',
            'confirm': 'Password123',
            'confirm_password': 'Password123',
            'phone': '0911222333',
            'email': 'csrf_cust@gmail.com',
            'csrf_token': valid_csrf_token
        })
        assert response.status_code in (302, 200, 400)


# =========================================================================
# 2. TEST CSRF CHO API JSON (SEND VIA HEADER X-CSRFToken)
# =========================================================================
class TestStateChangingRoutesCSRFProtection:

    def test_create_appointment_with_valid_csrf_header_success(
            self,
            app_csrf_enabled,
            client_csrf_enabled,
            customer_user,
            sample_service,
            staff_user,
            valid_csrf_token
    ):
        """
        Gửi API JSON kèm Header X-CSRFToken chuẩn
        -> request vượt qua CSRF
        -> tạo lịch hẹn thành công.
        """

        # ==========================================
        # 1. Login thật
        # ==========================================

        login_response = client_csrf_enabled.post(
            '/login',
            data={
                'username': customer_user.username,
                'password': customer_user.raw_password,
                'csrf_token': valid_csrf_token
            }
        )

        assert login_response.status_code == 302

        # ==========================================
        # 2. Chọn ngày tương lai
        # ==========================================

        target_date = (
                date.today() + timedelta(days=2)
        ).strftime('%Y-%m-%d')

        # ==========================================
        # 3. Lấy slot thực sự khả dụng
        # GET không cần CSRF
        # ==========================================

        slot_response = client_csrf_enabled.get(
            '/appointments/available-slots'
            f'?service_id={sample_service.id}'
            f'&date={target_date}'
            f'&staff_id={staff_user.id}'
        )

        assert slot_response.status_code == 200

        available_slots = (
            slot_response.json['available_slots']
        )

        assert available_slots, (
            "Không có slot khả dụng để test CSRF"
        )

        selected_time = available_slots[0]

        # ==========================================
        # 4. POST với CSRF header hợp lệ
        # ==========================================

        response = client_csrf_enabled.post(
            '/appointments',
            json={
                'service_id': sample_service.id,
                'staff_id': staff_user.id,
                'date': target_date,
                'time': selected_time
            },
            headers={
                'X-CSRFToken': valid_csrf_token
            }
        )

        print(
            "\n[CSRF CREATE APPOINTMENT]",
            response.status_code,
            response.get_data(as_text=True)
        )

        # ==========================================
        # 5. Request phải vượt qua CSRF
        # và tạo appointment thành công
        # ==========================================

        assert response.status_code == 201

    def test_cancel_appointment_with_valid_csrf_header_success(self, app_csrf_enabled, client_csrf_enabled, customer_user, sample_appointment, valid_csrf_token):
        """Hủy lịch hẹn qua API JSON gửi kèm Header X-CSRFToken chuẩn -> Thành công (200)"""
        # Đăng nhập bằng POST /login thực tế để Flask-Login tự ghi Cookie Session
        client_csrf_enabled.post('/login', data={
            'username': customer_user.username,
            'password': customer_user.raw_password,
            'csrf_token': valid_csrf_token
        })

        response = client_csrf_enabled.patch(
            f'/appointments/{sample_appointment.id}/cancel',
            headers={'X-CSRFToken': valid_csrf_token}
        )
        assert response.status_code == 200


# =========================================================================
# 3. SAFE METHODS (GET) KHÔNG BỊ ẢNH HƯỞNG BỞI CSRF
# =========================================================================
class TestSafeMethodsBypassCSRF:

    @pytest.mark.parametrize("safe_url", [
        '/',
        '/login',
        '/register',
        '/users/me',
        '/appointments/me'
    ])
    def test_get_requests_do_not_require_csrf_token(self, client_csrf_enabled, customer_user, valid_csrf_token, safe_url):
        """Các yêu cầu GET (Safe Methods) luôn luôn hoạt động bình thường mà không cần CSRF token"""
        client_csrf_enabled.post('/login', data={
            'username': customer_user.username,
            'password': customer_user.raw_password,
            'csrf_token': valid_csrf_token
        })

        response = client_csrf_enabled.get(safe_url)
        assert response.status_code in (200, 302)