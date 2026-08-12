import hashlib
import re
from sqlalchemy.exc import IntegrityError

from app.models import User, UserRole, Service, Product
from app import db, app
from app.exceptions import ValidationError, DuplicateError, NotFoundError


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
        raise NotFoundError("Người dùng không tồn tại!")

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
        raise NotFoundError("Người dùng không tồn tại!")

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


# =========================================================================
# Nghiệp vụ 2: Quản lý Dịch vụ (Service)
# =========================================================================

def get_service_by_id(service_id):
    return Service.query.get(service_id)


def get_all_services():
    return Service.query.all()


def validate_service_input(name, price, duration, is_update=False, service_id=None):
    """Hàm kiểm tra dữ liệu đầu vào cho Dịch vụ"""
    if not name or not name.strip():
        raise ValidationError("Tên dịch vụ không được để trống!")

    try:
        price = float(price)
        if price < 0:
            raise ValidationError("Giá dịch vụ không được âm!")
    except (ValueError, TypeError):
        raise ValidationError("Giá dịch vụ phải là một số hợp lệ!")

    try:
        duration = int(duration)
        if duration <= 0:
            raise ValidationError("Thời gian thực hiện phải lớn hơn 0 phút!")
    except (ValueError, TypeError):
        raise ValidationError("Thời gian thực hiện phải là số nguyên!")

    # Kiểm tra trùng tên dịch vụ
    name = name.strip()
    query = Service.query.filter(Service.service_name == name)
    if is_update and service_id:
        query = query.filter(Service.id != service_id)

    if query.first():
        raise DuplicateError(f"Dịch vụ '{name}' đã tồn tại trong hệ thống!")


def add_service(name, price, duration, description=None):
    """Thêm mới dịch vụ"""
    validate_service_input(name, price, duration)

    s = Service(
        service_name=name.strip(),
        price=float(price),
        duration_minutes=int(duration),
        description=description.strip() if description else None
    )

    db.session.add(s)
    try:
        db.session.commit()
        return s
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể thêm dịch vụ!")


def update_service(service_id, name, price, duration, description=None):
    """Cập nhật dịch vụ"""
    s = get_service_by_id(service_id)
    if not s:
        raise NotFoundError("Không tìm thấy dịch vụ!")

    validate_service_input(name, price, duration, is_update=True, service_id=service_id)

    s.service_name = name.strip()
    s.price = float(price)
    s.duration_minutes = int(duration)
    s.description = description.strip() if description else None

    try:
        db.session.commit()
        return s
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể cập nhật dịch vụ!")


def delete_service(service_id):
    """Xóa mềm (Soft Delete) dịch vụ"""
    s = get_service_by_id(service_id)
    if not s:
        raise NotFoundError("Không tìm thấy dịch vụ!")

    s.active = False
    db.session.commit()
    return True


# =========================================================================
# Nghiệp vụ 3: Quản lý Sản phẩm (Product)
# =========================================================================

def get_product_by_id(product_id):
    return Product.query.get(product_id)


def load_products(kw=None, page=None):
    """Lấy danh sách sản phẩm (có tìm kiếm & phân trang)"""
    query = Product.query.filter(Product.active.__eq__(True))
    if kw:
        query = query.filter(Product.product_name.contains(kw.strip()))

    page_size = app.config.get('PAGE_SIZE', 8)
    if page:
        start = (page - 1) * page_size
        query = query.offset(start).limit(page_size)

    return query.all()


def count_products(kw=None):
    """Đếm tổng số lượng sản phẩm để phân trang"""
    query = Product.query.filter(Product.active.__eq__(True))
    if kw:
        query = query.filter(Product.product_name.contains(kw.strip()))
    return query.count()


def validate_product_input(name, price, stock, min_stock, is_update=False, product_id=None):
    """Hàm kiểm tra dữ liệu đầu vào cho Sản phẩm"""
    if not name or not name.strip():
        raise ValidationError("Tên sản phẩm không được để trống!")

    try:
        price = int(price)
        if price < 0:
            raise ValidationError("Giá sản phẩm không được âm!")
    except (ValueError, TypeError):
        raise ValidationError("Giá sản phẩm phải là một số hợp lệ!")

    try:
        stock = int(stock)
        if stock < 0:
            raise ValidationError("Số lượng tồn kho không được âm!")
    except (ValueError, TypeError):
        raise ValidationError("Số lượng tồn kho phải là số nguyên!")

    try:
        min_stock = int(min_stock)
        if min_stock < 0:
            raise ValidationError("Mức tồn kho tối thiểu không được âm!")
    except (ValueError, TypeError):
        raise ValidationError("Mức tồn kho tối thiểu phải là số nguyên!")

    # Kiểm tra trùng tên sản phẩm
    name = name.strip()
    query = Product.query.filter(Product.product_name == name)
    if is_update and product_id:
        query = query.filter(Product.id != product_id)

    if query.first():
        raise DuplicateError(f"Sản phẩm '{name}' đã tồn tại trong hệ thống!")


def add_product(name, price, stock_quantity, min_stock_level):
    """Thêm mới sản phẩm"""
    validate_product_input(name, price, stock_quantity, min_stock_level)

    p = Product(
        product_name=name.strip(),
        price=int(price),
        stock_quantity=int(stock_quantity),
        min_stock_level=int(min_stock_level)
    )

    db.session.add(p)
    try:
        db.session.commit()
        return p
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể thêm sản phẩm!")


def update_product(product_id, name, price, stock_quantity, min_stock_level):
    """Cập nhật thông tin sản phẩm"""
    p = get_product_by_id(product_id)
    if not p:
        raise NotFoundError("Không tìm thấy sản phẩm!")

    validate_product_input(name, price, stock_quantity, min_stock_level, is_update=True, product_id=product_id)

    p.product_name = name.strip()
    p.price = int(price)
    p.stock_quantity = int(stock_quantity)
    p.min_stock_level = int(min_stock_level)

    try:
        db.session.commit()
        return p
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể cập nhật sản phẩm!")


def delete_product(product_id):
    """Xóa mềm (Soft Delete) sản phẩm"""
    p = get_product_by_id(product_id)
    if not p:
        raise NotFoundError("Không tìm thấy sản phẩm!")

    p.active = False
    db.session.commit()
    return True


def check_low_stock_products():
    """Lấy danh sách các sản phẩm sắp hết hàng (stock_quantity <= min_stock_level)"""
    return Product.query.filter(
        Product.active.__eq__(True),
        Product.stock_quantity <= Product.min_stock_level
    ).all()


# =========================================================================
# Nghiệp vụ 3b: Nhập / Xuất kho
# =========================================================================

def _validate_stock_quantity(quantity):
    """Hàm bổ trợ: số lượng nhập/xuất phải là số nguyên dương"""
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        raise ValidationError("Số lượng phải là số nguyên!")
    if quantity <= 0:
        raise ValidationError("Số lượng phải lớn hơn 0!")
    return quantity


def import_stock(product_id, quantity):
    """Nhập kho: tăng stock_quantity của sản phẩm"""
    p = get_product_by_id(product_id)
    if not p:
        raise NotFoundError("Không tìm thấy sản phẩm!")

    quantity = _validate_stock_quantity(quantity)

    p.stock_quantity += quantity
    try:
        db.session.commit()
        return p
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể nhập kho!")


def export_stock(product_id, quantity):
    """Xuất kho: giảm stock_quantity của sản phẩm.
    Validate KHÔNG cho xuất âm: số lượng xuất không được vượt quá tồn kho hiện có."""
    p = get_product_by_id(product_id)
    if not p:
        raise NotFoundError("Không tìm thấy sản phẩm!")

    quantity = _validate_stock_quantity(quantity)

    if quantity > p.stock_quantity:
        raise ValidationError(
            f"Không đủ tồn kho để xuất! Tồn kho hiện tại: {p.stock_quantity}"
        )

    p.stock_quantity -= quantity
    try:
        db.session.commit()
        return p
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể xuất kho!")






