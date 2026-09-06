import uuid

import pytest

from app import dao
from app.models import UserRole
from app.exceptions import ValidationError, DuplicateError, NotFoundError


# =========================================================================
# add_user — Đăng ký tài khoản
# =========================================================================
class TestAddUser:

    def test_add_user_success(self, app):
        suffix = uuid.uuid4().hex[:8]

        user = dao.add_user(
            full_name="Nguyễn Văn A",
            username=f"user{suffix}",
            password="Password123",
            phone=f"09{uuid.uuid4().int % 100000000:08d}",
            email=f"user{suffix}@example.com",
        )

        assert user is not None
        assert user.id is not None
        assert user.full_name == "Nguyễn Văn A"

    def test_add_user_with_role_staff(self, app):
        suffix = uuid.uuid4().hex[:8]

        user = dao.add_user(
            full_name="Nhân Viên B",
            username=f"staff{suffix}",
            password="Password123",
            phone=f"09{uuid.uuid4().int % 100000000:08d}",
            email=f"staff{suffix}@example.com",
            role=UserRole.STAFF,
        )

        assert user is not None
        assert user.role == UserRole.STAFF

    def test_duplicate_username_raises(self, app, customer_user):
        with pytest.raises(DuplicateError):
            dao.add_user(
                full_name="Người Khác", username=customer_user.username,
                password="Password123", phone="0987654321", email="khac@example.com",
            )

    def test_duplicate_email_raises(self, app, customer_user):
        with pytest.raises(DuplicateError):
            dao.add_user(
                full_name="Người Khác", username="nguoikhac1",
                password="Password123", phone="0987654321", email=customer_user.email,
            )

    def test_empty_full_name_raises(self, app):
        with pytest.raises(ValidationError):
            dao.add_user(
                full_name="   ", username="username1", password="Password123",
                phone="0912345678", email="a@example.com",
            )

    @pytest.mark.parametrize("phone", [
        "123456789",     # không bắt đầu bằng 0
        "09123456",      # thiếu số
        "091234567890",  # dư số
        "abcdefghij",    # không phải số
        None,
    ])
    def test_invalid_phone_raises(self, app, phone):
        with pytest.raises(ValidationError):
            dao.add_user(
                full_name="Test User", username="testuser1", password="Password123",
                phone=phone, email="a@example.com",
            )

    @pytest.mark.parametrize("email", ["not-an-email", "abc@", "@abc.com", ""])
    def test_invalid_email_raises(self, app, email):
        with pytest.raises(ValidationError):
            dao.add_user(
                full_name="Test User", username="testuser2", password="Password123",
                phone="0912345678", email=email,
            )

    @pytest.mark.parametrize("username", [
        "usr",                  # < 5 ký tự
        "a" * 21,                # > 20 ký tự
        "user name",             # có khoảng trắng
        "user@name",             # ký tự đặc biệt
    ])
    def test_invalid_username_raises(self, app, username):
        with pytest.raises(ValidationError):
            dao.add_user(
                full_name="Test User", username=username, password="Password123",
                phone="0912345678", email="a@example.com",
            )

    @pytest.mark.parametrize("password", [
        "short1A",       # < 8 ký tự
        "lowercase123",  # thiếu chữ hoa
        "UPPERCASE123",  # thiếu chữ thường
        "NoDigitsHere",  # thiếu số
        "",
        None,
    ])
    def test_weak_password_raises(self, app, password):
        with pytest.raises(ValidationError):
            dao.add_user(
                full_name="Test User", username="testuser3", password=password,
                phone="0912345678", email="a@example.com",
            )


# =========================================================================
# auth_user — Đăng nhập
# =========================================================================
class TestAuthUser:

    def test_auth_success(self, app, customer_user):
        user = dao.auth_user(customer_user.username, "Customer123")
        assert user.id == customer_user.id

    def test_wrong_username_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.auth_user("khongtontai", "Customer123")

    def test_wrong_password_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.auth_user(customer_user.username, "SaiMatKhau123")

    def test_empty_username_raises(self, app):
        with pytest.raises(ValidationError):
            dao.auth_user("", "Customer123")

    def test_empty_password_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.auth_user(customer_user.username, "")

    def test_inactive_account_raises(self, app, customer_user):
        dao.toggle_user_active(customer_user.id)  # khóa tài khoản
        with pytest.raises(ValidationError):
            dao.auth_user(customer_user.username, "Customer123")


# =========================================================================
# get_users — Danh sách người dùng (Admin)
# =========================================================================
class TestGetUsers:

    def test_get_all_users(self, app, admin_user, staff_user, customer_user):
        users = dao.get_users()

        user_ids = [u.id for u in users]

        assert admin_user.id in user_ids
        assert staff_user.id in user_ids
        assert customer_user.id in user_ids

    def test_filter_by_role(self, app, admin_user, staff_user, customer_user):
        staffs = dao.get_users(role=UserRole.STAFF)

        assert staff_user.id in [u.id for u in staffs]

        assert all(
            u.role == UserRole.STAFF
            for u in staffs
        )


# =========================================================================
# update_user_profile — Cập nhật thông tin cá nhân
# =========================================================================
class TestUpdateUserProfile:

    def test_update_success(self, app, customer_user):
        suffix = uuid.uuid4().hex[:8]

        new_phone = f"09{uuid.uuid4().int % 100000000:08d}"
        new_email = f"moi{suffix}@example.com"

        updated = dao.update_user_profile(
            user_id=customer_user.id,
            full_name="Tên Mới",
            phone=new_phone,
            email=new_email,
        )

        assert updated.full_name == "Tên Mới"
        assert updated.phone == new_phone
        assert updated.email == new_email

    def test_update_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.update_user_profile(
                user_id=99999, full_name="Ai Đó", phone="0999999999", email="ai@example.com",
            )

    def test_update_duplicate_email_raises(self, app, customer_user, staff_user):
        with pytest.raises(DuplicateError):
            dao.update_user_profile(
                user_id=customer_user.id, full_name=customer_user.full_name,
                phone=customer_user.phone, email=staff_user.email,  # trùng email của staff
            )

    def test_update_keep_own_email_ok(self, app, customer_user):
        """Cập nhật nhưng giữ nguyên email chính mình thì không được coi là trùng."""
        updated = dao.update_user_profile(
            user_id=customer_user.id, full_name="Tên Mới Khác",
            phone=customer_user.phone, email=customer_user.email,
        )
        assert updated.full_name == "Tên Mới Khác"

    def test_update_invalid_phone_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.update_user_profile(
                user_id=customer_user.id, full_name=customer_user.full_name,
                phone="123", email=customer_user.email,
            )


# =========================================================================
# change_password — Đổi mật khẩu
# =========================================================================
class TestChangePassword:

    def test_change_password_success(self, app, customer_user):
        dao.change_password(customer_user.id, "Customer123", "NewPass456")
        # Đăng nhập lại bằng mật khẩu mới phải thành công
        user = dao.auth_user(customer_user.username, "NewPass456")
        assert user.id == customer_user.id

    def test_wrong_old_password_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.change_password(customer_user.id, "SaiMatKhauCu1", "NewPass456")

    def test_new_password_same_as_old_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.change_password(customer_user.id, "Customer123", "Customer123")

    def test_new_password_weak_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.change_password(customer_user.id, "Customer123", "yeu")

    def test_user_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.change_password(99999, "Customer123", "NewPass456")

    def test_empty_old_password_raises(self, app, customer_user):
        with pytest.raises(ValidationError):
            dao.change_password(customer_user.id, "", "NewPass456")


# =========================================================================
# toggle_user_active / delete_user_soft — Khóa / Vô hiệu hóa tài khoản
# =========================================================================
class TestToggleAndDelete:

    def test_toggle_user_active_flips_status(self, app, customer_user):
        assert customer_user.active is True
        dao.toggle_user_active(customer_user.id)
        assert customer_user.active is False
        dao.toggle_user_active(customer_user.id)
        assert customer_user.active is True

    def test_toggle_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.toggle_user_active(99999)

    def test_delete_user_soft_sets_inactive(self, app, customer_user):
        dao.delete_user_soft(customer_user.id)
        assert customer_user.active is False
        # User vẫn còn trong DB (soft delete), không bị xóa vật lý
        assert dao.get_user_by_id(customer_user.id) is not None

    def test_delete_not_found_raises(self, app):
        with pytest.raises(NotFoundError):
            dao.delete_user_soft(99999)

    def test_deleted_user_cannot_login(self, app, customer_user):
        dao.delete_user_soft(customer_user.id)
        with pytest.raises(ValidationError):
            dao.auth_user(customer_user.username, "Customer123")


# =========================================================================
# get_user_by_id
# =========================================================================
class TestGetUserById:

    def test_found(self, app, customer_user):
        user = dao.get_user_by_id(customer_user.id)
        assert user.id == customer_user.id

    def test_not_found_returns_none(self, app):
        assert dao.get_user_by_id(99999) is None