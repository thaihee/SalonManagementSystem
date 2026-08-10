import hashlib
import re
from sqlalchemy.exc import IntegrityError

from app.models import User, UserRole, Service
from app import db, app
from app.exceptions import ValidationError, DuplicateError


def get_user_by_id(user_id):
    return User.query.get(user_id)

def validate_user_input(full_name, username, password, phone, email, is_update=False):
    """Hàm bổ trợ kiểm tra định dạng dữ liệu đầu vào"""
    if not full_name or not full_name.strip():
        raise ValidationError("Vui lòng nhập họ tên!")
    if len(full_name.strip()) > 100:
        raise ValidationError("Họ tên không được quá 100 ký tự!")

    if phone is None or not re.match(r'^[0-9]{9,15}$', phone):
        raise ValidationError("Số điện thoại không hợp lệ (phải từ 9-15 chữ số)!")

    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not email or not re.match(email_regex, email):
        raise ValidationError("Email không đúng định dạng!")

    if not is_update:
        username = username.strip() if username else ""
        if len(username) < 5 or len(username) > 20:
            raise ValidationError("Username phải từ 5 đến 20 ký tự!")
        if re.search(r'\s', username):
            raise ValidationError("Username không được chứa khoảng trắng!")
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            raise ValidationError("Username không được chứa ký tự đặc biệt!")

        # Kiểm tra độ mạnh mật khẩu (Tối thiểu 8 ký tự, có chữ hoa, chữ thường, số)
        if len(password) < 8:
            raise ValidationError("Mật khẩu phải từ 8 ký tự trở lên!")
        if not re.search(r'[0-9]', password):
            raise ValidationError("Mật khẩu phải chứa ít nhất 1 chữ số!")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Mật khẩu phải chứa ít nhất 1 ký tự hoa!")
        if not re.search(r'[a-z]', password):
            raise ValidationError("Mật khẩu phải chứa ít nhất 1 ký tự thường!")


#=========================Nghiệp vụ 1: Xác thực & Phân quyền==========================

def add_user(full_name, username, password, phone, email, role=UserRole.CUSTOMER):
    """Đăng ký tài khoản (Khách hàng) hoặc tạo nhân viên (Admin)"""
    validate_user_input(full_name, username, password, phone, email, is_update=False)

    username = username.strip()
    email = email.strip()

    # Kiểm tra trùng lặp DB
    if User.query.filter(User.username == username).first():
        raise DuplicateError(f"Username '{username}' đã tồn tại!")
    if User.query.filter(User.email == email).first():
        raise DuplicateError(f"Email '{email}' đã tồn tại!")

    # Hash mật khẩu an toàn với werkzeug
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

    u = User(
        full_name=full_name.strip(),
        username=username,
        password=password,
        phone=phone.strip(),
        email=email,
        role=role
    )

    db.session.add(u)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể lưu tài khoản vào cơ sở dữ liệu!")
    return u


def auth_user(username, password):
    if not username:
        raise ValidationError("Vui lòng nhập username!")
    if not password:
        raise ValidationError("Vui lòng nhập mật khẩu!")
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())
    u = User.query.filter(User.username == username).first()
    if not u:
        raise ValidationError("Tên đăng nhập hoặc mật khẩu không chính xác!")
    if password != u.password:
        raise ValidationError("Tên đăng nhập hoặc mật khẩu không chính xác!")
    if not u.active:
        raise ValidationError("Tài khoản của bạn đã bị vô hiệu hóa!")
    return u


def get_users(role=None):
    """Lấy danh sách người dùng (Admin dùng)"""
    query = User.query
    if role:
        query = query.filter(User.role == role)
    return query.all()


def update_user_profile(user_id, full_name, phone, email):
    """Cập nhật thông tin bản thân (User/Staff/Admin)"""
    u = get_user_by_id(user_id)
    if not u:
        raise ValidationError("Người dùng không tồn tại!")

    validate_user_input(full_name, u.username, None, phone, email, is_update=True)

    # Kiểm tra email trùng với người khác
    existing_email = User.query.filter(User.email == email.strip(), User.id != user_id).first()
    if existing_email:
        raise DuplicateError(f"Email '{email}' đã được sử dụng bởi tài khoản khác!")

    u.full_name = full_name.strip()
    u.phone = phone.strip()
    u.email = email.strip()

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Exception("Không thể cập nhật thông tin người dùng!")
    return u


def delete_user_soft(user_id):
    """Vô hiệu hóa tài khoản nhân viên/người dùng (Soft Delete qua cột active)"""
    u = get_user_by_id(user_id)
    if not u:
        raise ValidationError("Người dùng không tồn tại!")

    u.active = False
    db.session.commit()
    return u


def load_services(kw=None, page=1):
    """Lấy danh sách dịch vụ Salon hiển thị ở trang chủ (có tìm kiếm & phân trang)"""
    query = Service.query.filter(Service.active.__eq__(True))
    if kw:
        query = query.filter(Service.service_name.contains(kw.strip()))

    page_size = app.config.get('PAGE_SIZE', 8)
    if page:
        start = (page - 1) * page_size
        query = query.offset(start).limit(page_size)

    return query.all()


def count_services(kw=None):
    """Đếm tổng số lượng dịch vụ active để tính số trang (Phân trang)"""
    query = Service.query.filter(Service.active.__eq__(True))
    if kw:
        query = query.filter(Service.service_name.contains(kw.strip()))
    return query.count()