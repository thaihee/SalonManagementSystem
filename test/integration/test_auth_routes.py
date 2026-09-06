import uuid

import pytest
from app import dao
from app.models import UserRole


# =========================================================================
# 1. GET /login & POST /login
# =========================================================================
class TestLoginRoutes:

    def test_login_view_unauthenticated(self, client):
        """Khách chưa đăng nhập vào GET /login -> 200 OK"""
        response = client.get('/login')
        assert response.status_code == 200

    def test_login_view_already_authenticated(self, customer_client):
        """Đã đăng nhập truy cập GET /login -> Redirect về / (302)"""
        response = customer_client.get('/login')
        assert response.status_code == 302
        assert response.location.endswith('/')

    def test_login_process_customer_success(self, client, customer_user):
        """Khách hàng đăng nhập đúng -> Redirect về / (302)"""
        response = client.post('/login', data={
            'username': customer_user.username,
            'password': customer_user.raw_password
        })
        assert response.status_code == 302
        assert response.location.endswith('/')

    @pytest.mark.parametrize("role, expected_redirect", [
        (UserRole.ADMIN, '/admin'),
        (UserRole.RECEPTIONIST, '/reception/appointments'),
        (UserRole.STAFF, '/staff/appointments')
    ])
    def test_login_process_redirect_by_role(self, client, app, role, expected_redirect):
        """Đăng nhập Admin/Receptionist/Staff -> Redirect về đúng URL quản trị theo Role"""
        # clean_username = f"user{role.name.lower()}"
        suffix = uuid.uuid4().hex[:8]

        user = dao.add_user(
            f"User {role.name}",
            f"usr{suffix}",
            "Password123",
            f"09{uuid.uuid4().int % 100000000:08d}",
            f"{role.name.lower()}{suffix}@test.com",
            role=role
        )
        response = client.post('/login', data={'username': user.username, 'password': "Password123"})
        assert response.status_code == 302
        assert expected_redirect in response.location

    def test_login_process_wrong_password(self, client, customer_user):
        """Đăng nhập sai mật khẩu -> index.py trả về 401 UNAUTHORIZED"""
        response = client.post('/login', data={'username': customer_user.username, 'password': 'WrongPassword123'})
        assert response.status_code == 401
        assert "Tên đăng nhập hoặc mật khẩu không chính xác!" in response.get_data(as_text=True)

    def test_login_process_disabled_account(self, client, customer_user):
        """Tài khoản bị vô hiệu hóa -> index.py trả về 401 UNAUTHORIZED"""
        dao.toggle_user_active(customer_user.id)
        response = client.post('/login', data={'username': customer_user.username, 'password': customer_user.raw_password})
        assert response.status_code == 401
        assert "Tài khoản của bạn đã bị vô hiệu hóa!" in response.get_data(as_text=True)


# =========================================================================
# 2. GET /register & POST /register
# =========================================================================
class TestRegisterRoutes:

    def test_register_view_unauthenticated(self, client):
        """Mở trang đăng ký -> 200 OK"""
        response = client.get('/register')
        assert response.status_code == 200

    def test_register_process_success(self, client):
        """Đăng ký thành công -> Redirect về /login (302)"""
        suffix = uuid.uuid4().hex[:8]

        response = client.post('/register', data={
            'full_name': 'Khách Hàng Mới',
            'username': f'cust{suffix}',
            'password': 'Password123',
            'confirm': 'Password123',
            'phone': f"09{uuid.uuid4().int % 100000000:08d}",
            'email': f'cust{suffix}@gmail.com'
        })
        assert response.status_code == 302
        assert response.location.endswith('/login')

    def test_register_process_password_mismatch(self, client):
        """Mật khẩu không khớp -> index.py trả về 400 Bad Request"""
        response = client.post('/register', data={
            'full_name': 'Khách Hàng Mới', 'username': 'newcustomer2',
            'password': 'Password123', 'confirm': 'DifferentPass123',
            'phone': '0988776655', 'email': 'newcust2@gmail.com'
        })
        assert response.status_code == 400
        assert "Mật khẩu xác nhận không khớp!" in response.get_data(as_text=True)

    def test_register_process_duplicate_error(self, client, customer_user):
        """Đăng ký trùng username -> index.py trả về 409 Conflict"""
        response = client.post('/register', data={
            'full_name': 'Trùng Username', 'username': customer_user.username,
            'password': 'Password123', 'confirm': 'Password123',
            'phone': '0988776655', 'email': 'unique_email@gmail.com'
        })
        assert response.status_code == 409
        assert "đã tồn tại!" in response.get_data(as_text=True)


# =========================================================================
# 3. GET /users/me & PUT /users/me & POST /users/change-password & GET /logout
# =========================================================================
class TestUserProfileAndLogoutRoutes:

    def test_profile_view_unauthorized(self, client):
        """Chưa đăng nhập xem /users/me -> Redirect về /login (302)"""
        response = client.get('/users/me')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_profile_view_authorized(self, customer_client):
        """Đã đăng nhập xem /users/me -> 200 OK"""
        response = customer_client.get('/users/me')
        assert response.status_code == 200

    def test_profile_update_json_success(self, customer_client, customer_user):
        """Cập nhật thông tin qua PUT /users/me JSON -> 200 OK"""
        new_phone = f"09{uuid.uuid4().int % 100000000:08d}"

        response = customer_client.put('/users/me', json={
            'full_name': 'Tên Mới Cập Nhật',
            'phone': new_phone,
            'email': customer_user.email
        })
        assert response.status_code == 200
        assert response.json['message'] == "Cập nhật thông tin cá nhân thành công!"

    def test_change_password_success(self, customer_client, customer_user):
        """Đổi mật khẩu thành công qua POST /users/change-password -> 200 OK"""
        response = customer_client.post('/users/change-password', json={
            'old_password': customer_user.raw_password,
            'new_password': 'NewPassword123',
            'confirm_password': 'NewPassword123'
        })
        assert response.status_code == 200
        assert response.json['success'] is True

    def test_logout_success(self, customer_client):
        """Đăng xuất -> Redirect về /login (302)"""
        response = customer_client.get('/logout')
        assert response.status_code == 302
        assert '/login' in response.location