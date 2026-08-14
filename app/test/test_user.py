import pytest
from app import dao, db
from app.models import User, UserRole
from app.exceptions import ValidationError, DuplicateError, NotFoundError


# =========================================================================
# TEST SUITE: Nghiệp vụ 1 - Xác thực & Phân quyền (User)
# =========================================================================

# --------------------------- add_user ---------------------------

def test_add_user_success(app):
    """Đăng ký tài khoản hợp lệ thành công, mật khẩu phải được hash (không lưu plain text)"""
    u = dao.add_user(
        full_name="Nguyễn Văn A",
        username="nguyenvana",
        password="Password1",
        phone="0900000001",
        email="nguyenvana@example.com",
    )

    assert u.id is not None
    assert u.full_name == "Nguyễn Văn A"
    assert u.role == UserRole.CUSTOMER  # role mặc định
    assert u.password != "Password1"  # phải được hash, không lưu plain text


def test_add_user_custom_role(app):
    """Tạo tài khoản với role tùy chỉnh (VD: Admin tạo nhân viên)"""
    u = dao.add_user(
        full_name="Trần Thị B",
        username="tranthib",
        password="Password1",
        phone="0900000002",
        email="tranthib@example.com",
        role=UserRole.STAFF,
    )
    assert u.role == UserRole.STAFF


def test_add_user_empty_full_name(app):
    """Họ tên rỗng -> ValidationError"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_user(
            full_name="   ",
            username="testuser1",
            password="Password1",
            phone="0900000003",
            email="testuser1@example.com",
        )
    assert "họ tên" in str(excinfo.value).lower()


def test_add_user_full_name_too_long(app):
    """Họ tên quá 100 ký tự -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="A" * 101,
            username="testuser2",
            password="Password1",
            phone="0900000004",
            email="testuser2@example.com",
        )


def test_add_user_invalid_phone(app):
    """Số điện thoại sai định dạng -> ValidationError"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_user(
            full_name="Lê Văn C",
            username="levanc",
            password="Password1",
            phone="0123abc",
            email="levanc@example.com",
        )
    assert "điện thoại" in str(excinfo.value).lower()


def test_add_user_invalid_email(app):
    """Email sai định dạng -> ValidationError"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_user(
            full_name="Phạm Văn D",
            username="phamvand",
            password="Password1",
            phone="0900000005",
            email="not-an-email",
        )
    assert "email" in str(excinfo.value).lower()


def test_add_user_username_too_short(app):
    """Username dưới 5 ký tự -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="Hoàng Văn E",
            username="ab",
            password="Password1",
            phone="0900000006",
            email="hoangvane@example.com",
        )


def test_add_user_username_too_long(app):
    """Username trên 20 ký tự -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="Hoàng Văn F",
            username="a" * 21,
            password="Password1",
            phone="0900000007",
            email="hoangvanf@example.com",
        )


def test_add_user_username_with_whitespace(app):
    """Username chứa khoảng trắng -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="Đỗ Thị G",
            username="do thi g",
            password="Password1",
            phone="0900000008",
            email="dothig@example.com",
        )


def test_add_user_username_special_char(app):
    """Username chứa ký tự đặc biệt -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="Vũ Văn H",
            username="vuvan@h",
            password="Password1",
            phone="0900000009",
            email="vuvanh@example.com",
        )


def test_add_user_password_too_short(app):
    """Mật khẩu dưới 8 ký tự -> ValidationError"""
    with pytest.raises(ValidationError) as excinfo:
        dao.add_user(
            full_name="Ngô Thị K",
            username="ngothik",
            password="Ab1",
            phone="0900000010",
            email="ngothik@example.com",
        )
    assert "mật khẩu" in str(excinfo.value).lower()


def test_add_user_password_no_digit(app):
    """Mật khẩu thiếu chữ số -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="Bùi Văn L",
            username="buivanl",
            password="Password",
            phone="0900000011",
            email="buivanl@example.com",
        )


def test_add_user_password_no_uppercase(app):
    """Mật khẩu thiếu chữ hoa -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="Đặng Văn M",
            username="dangvanm",
            password="password1",
            phone="0900000012",
            email="dangvanm@example.com",
        )


def test_add_user_password_no_lowercase(app):
    """Mật khẩu thiếu chữ thường -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.add_user(
            full_name="Trịnh Văn N",
            username="trinhvann",
            password="PASSWORD1",
            phone="0900000013",
            email="trinhvann@example.com",
        )


def test_add_user_duplicate_username(app):
    """Trùng username -> DuplicateError"""
    dao.add_user(
        full_name="Người Một",
        username="nguoimot",
        password="Password1",
        phone="0900000014",
        email="nguoimot@example.com",
    )
    with pytest.raises(DuplicateError) as excinfo:
        dao.add_user(
            full_name="Người Hai",
            username="nguoimot",
            password="Password2",
            phone="0900000015",
            email="nguoihai@example.com",
        )
    assert "đã tồn tại" in str(excinfo.value)


def test_add_user_duplicate_email(app):
    """Trùng email -> DuplicateError"""
    dao.add_user(
        full_name="Người Ba",
        username="nguoiba",
        password="Password1",
        phone="0900000016",
        email="trung@example.com",
    )
    with pytest.raises(DuplicateError) as excinfo:
        dao.add_user(
            full_name="Người Bốn",
            username="nguoibon",
            password="Password2",
            phone="0900000017",
            email="trung@example.com",
        )
    assert "đã tồn tại" in str(excinfo.value)


def test_add_user_avatar_too_long(app):
    """Kiểm tra bắt lỗi khi đường dẫn avatar quá 255 ký tự"""
    long_avatar_url = "a" * 256

    with pytest.raises(ValidationError) as excinfo:
        dao.add_user(
            full_name="Người Dùng Mới",
            username="newuser",
            password="Password1",
            phone="0900000999",
            email="newuser@example.com",
            avatar=long_avatar_url
        )
    assert "vượt quá 255 ký tự" in str(excinfo.value).lower()

# --------------------------- auth_user ---------------------------

def test_auth_user_success(app):
    """Đăng nhập đúng username/password -> trả về User"""
    dao.add_user(
        full_name="Người Đăng Nhập",
        username="loginuser",
        password="Password1",
        phone="0900000018",
        email="loginuser@example.com",
    )
    u = dao.auth_user(username="loginuser", password="Password1")
    assert u is not None
    assert u.username == "loginuser"


def test_auth_user_wrong_password(app):
    """Sai mật khẩu -> ValidationError"""
    dao.add_user(
        full_name="Người Sai MK",
        username="wrongpwuser",
        password="Password1",
        phone="0900000019",
        email="wrongpwuser@example.com",
    )
    with pytest.raises(ValidationError) as excinfo:
        dao.auth_user(username="wrongpwuser", password="SaiMatKhau1")
    assert "không chính xác" in str(excinfo.value)


def test_auth_user_username_not_exist(app):
    """Username không tồn tại -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.auth_user(username="khongtontai", password="Password1")


def test_auth_user_missing_username(app):
    """Thiếu username -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.auth_user(username="", password="Password1")


def test_auth_user_missing_password(app):
    """Thiếu password -> ValidationError"""
    with pytest.raises(ValidationError):
        dao.auth_user(username="loginuser", password="")


def test_auth_user_inactive_account(app):
    """Tài khoản đã bị vô hiệu hóa (active=False) -> không cho đăng nhập"""
    u = dao.add_user(
        full_name="Người Bị Khóa",
        username="lockeduser",
        password="Password1",
        phone="0900000020",
        email="lockeduser@example.com",
    )
    dao.delete_user_soft(u.id)

    with pytest.raises(ValidationError) as excinfo:
        dao.auth_user(username="lockeduser", password="Password1")
    assert "vô hiệu hóa" in str(excinfo.value)


# --------------------------- update_user_profile ---------------------------

def test_update_user_profile_success(app):
    """Cập nhật hồ sơ cá nhân thành công (Bao gồm cả cập nhật avatar)"""
    u = dao.add_user(
        full_name="Người Cũ",
        username="updateuser",
        password="Password1",
        phone="0900000021",
        email="updateuser@example.com",
        avatar="https://example.com/old-avatar.jpg"
    )

    updated = dao.update_user_profile(
        user_id=u.id,
        full_name="Người Mới",
        phone="0900000099",
        email="updated@example.com",
        avatar="https://example.com/new-avatar.jpg"
    )

    assert updated.full_name == "Người Mới"
    assert updated.phone == "0900000099"
    assert updated.email == "updated@example.com"
    assert updated.avatar == "https://example.com/new-avatar.jpg"


def test_update_user_profile_not_found(app):
    """Cập nhật hồ sơ user không tồn tại -> NotFoundError"""
    with pytest.raises(NotFoundError):
        dao.update_user_profile(
            user_id=9999,
            full_name="Ma",
            phone="0900000022",
            email="ma@example.com",
            avatar="https://example.com/ghost.jpg"
        )


def test_update_user_profile_keep_own_email_no_duplicate_error(app):
    """Giữ nguyên email cũ của chính mình -> KHÔNG báo trùng"""
    u = dao.add_user(
        full_name="Giữ Email",
        username="keepemailuser",
        password="Password1",
        phone="0900000023",
        email="keepemail@example.com",
    )

    updated = dao.update_user_profile(
        user_id=u.id,
        full_name="Giữ Email Mới",
        phone="0900000024",
        email="keepemail@example.com",
        avatar="https://example.com/keep-email.jpg"
    )
    assert updated.full_name == "Giữ Email Mới"
    assert updated.avatar == "https://example.com/keep-email.jpg"


def test_update_user_profile_duplicate_email_with_other_user(app):
    """Đổi email trùng với user khác -> DuplicateError"""
    dao.add_user(
        full_name="User X",
        username="userx",
        password="Password1",
        phone="0900000025",
        email="taken@example.com",
    )
    u2 = dao.add_user(
        full_name="User Y",
        username="usery",
        password="Password1",
        phone="0900000026",
        email="usery@example.com",
    )

    with pytest.raises(DuplicateError):
        dao.update_user_profile(
            user_id=u2.id,
            full_name="User Y",
            phone="0900000026",
            email="taken@example.com",
            avatar="https://example.com/duplicate.jpg"
        )

# --------------------------- delete_user_soft ---------------------------

def test_delete_user_soft(app):
    """Vô hiệu hóa tài khoản (Soft Delete qua active=False)"""
    u = dao.add_user(
        full_name="Người Bị Xóa",
        username="deleteuser",
        password="Password1",
        phone="0900000027",
        email="deleteuser@example.com",
    )

    result = dao.delete_user_soft(u.id)
    assert result.active is False

    # Sửa cảnh báo Query.get
    reloaded = db.session.get(User, u.id)
    assert reloaded.active is False


def test_delete_user_soft_not_found(app):
    """Vô hiệu hóa tài khoản không tồn tại -> NotFoundError"""
    with pytest.raises(NotFoundError):
        dao.delete_user_soft(9999)