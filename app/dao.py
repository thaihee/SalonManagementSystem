import hashlib
import re
from datetime import datetime, timedelta, time

from sqlalchemy.exc import IntegrityError

from app.models import User, UserRole, Service, Product, Appointment, AppointmentStatus, InvoiceDetail, InvoiceItemType, \
    Invoice, PaymentMethod
from app import db, app
from app.exceptions import ValidationError, DuplicateError, NotFoundError


def get_user_by_id(user_id):
    return User.query.get(user_id)

def validate_user_input(full_name, username, password, phone, email, is_update=False, avatar=None):
    """Hàm bổ trợ kiểm tra định dạng dữ liệu đầu vào"""
    if not full_name or not full_name.strip():
        raise ValidationError("Vui lòng nhập họ tên!")
    if len(full_name.strip()) > 100:
        raise ValidationError("Họ tên không được quá 100 ký tự!")

    if avatar and len(avatar.strip()) > 255:
        raise ValidationError("Đường dẫn ảnh đại diện không được vượt quá 255 ký tự!")

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

def add_user(full_name, username, password, phone, email, role=UserRole.CUSTOMER, avatar=None):
    """Đăng ký tài khoản (Khách hàng) hoặc tạo nhân viên (Admin)"""
    validate_user_input(full_name, username, password, phone, email, is_update=False, avatar=avatar)

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
        role=role,
        avatar=avatar
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


def update_user_profile(user_id, full_name, phone, email, avatar=None):
    """Cập nhật thông tin bản thân (User/Staff/Admin)"""
    u = get_user_by_id(user_id)
    if not u:
        raise NotFoundError("Người dùng không tồn tại!")

    validate_user_input(full_name, u.username, None, phone, email, is_update=True, avatar=avatar)

    # Kiểm tra email trùng với người khác
    existing_email = User.query.filter(User.email == email.strip(), User.id != user_id).first()
    if existing_email:
        raise DuplicateError(f"Email '{email}' đã được sử dụng bởi tài khoản khác!")

    u.full_name = full_name.strip()
    u.phone = phone.strip()
    u.email = email.strip()

    if avatar:
        u.avatar = avatar.strip()

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


def load_services(kw=None, page=1, page_size=None):
    """Lấy danh sách dịch vụ Salon hiển thị ở trang chủ (có tìm kiếm & phân trang)"""
    query = Service.query.filter(Service.active.__eq__(True))

    # Kiểm tra kw khác None và không rỗng
    if kw and kw.strip():
        query = query.filter(Service.service_name.contains(kw.strip()))

    # Lấy page_size từ config nếu không truyền vào (mặc định là 4)
    if page_size is None:
        page_size = app.config.get('PAGE_SIZE', 4)

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


def validate_service_input(name, price, duration, is_update=False, service_id=None, avatar=None):
    """Hàm kiểm tra dữ liệu đầu vào cho Dịch vụ"""
    if not name or not name.strip():
        raise ValidationError("Tên dịch vụ không được để trống!")

    if avatar and len(avatar.strip()) > 255:
        raise ValidationError("Đường dẫn ảnh dịch vụ không được vượt quá 255 ký tự!")

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


def add_service(name, price, duration, description=None, avatar=None):
    """Thêm mới dịch vụ"""
    validate_service_input(name, price, duration, avatar=avatar)

    s = Service(
        service_name=name.strip(),
        price=float(price),
        duration_minutes=int(duration),
        description=description.strip() if description else None,
        avatar = avatar
    )

    db.session.add(s)
    try:
        db.session.commit()
        return s
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể thêm dịch vụ!")


def update_service(service_id, name, price, duration, description=None, avatar=None):
    """Cập nhật dịch vụ"""
    s = get_service_by_id(service_id)
    if not s:
        raise NotFoundError("Không tìm thấy dịch vụ!")

    validate_service_input(name, price, duration, is_update=True, service_id=service_id, avatar=avatar)

    s.service_name = name.strip()
    s.price = float(price)
    s.duration_minutes = int(duration)
    s.description = description.strip() if description else None
    if avatar:  # <--- Nếu có ảnh mới thì cập nhật
        s.avatar = avatar

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


# =========================================================================
# Nghiệp vụ 4: Quản lý Lịch hẹn (Appointment)
# =========================================================================

def get_available_slots(service_id, date_str, staff_id=None):
    """
    Tìm danh sách các khung giờ trống trong ngày (8:00 - 20:00)
    Đã rào chắn: Lịch quá khứ, validate Staff, N+1 Query, Index Optimization.
    """
    # 1. Validate Dịch vụ
    service = get_service_by_id(service_id)
    if not service or not service.active:
        raise NotFoundError("Dịch vụ không tồn tại hoặc đã ngưng hoạt động!")

    # 2. Validate Nhân viên (RÀO MỚI)
    if staff_id:
        staff = get_user_by_id(staff_id)
        if not staff or not staff.active or staff.role != UserRole.STAFF:
            raise NotFoundError("Nhân viên không tồn tại hoặc không hợp lệ!")

    # 3. Validate Ngày
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Định dạng ngày không hợp lệ! Dùng YYYY-MM-DD")

    now = datetime.now()

    # RÀO MỚI: Nếu chọn ngày trong quá khứ -> Trả về danh sách rỗng
    if booking_date < now.date():
        return []

    # 4. Lấy lịch hẹn trong ngày (Tối ưu Index bằng Range Query thay vì db.func.date)
    start_of_day = datetime.combine(booking_date, time(0, 0, 0))
    end_of_day = datetime.combine(booking_date, time(23, 59, 59))

    query = Appointment.query.filter(
        Appointment.appointment_date >= start_of_day,
        Appointment.appointment_date <= end_of_day,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.active.__eq__(True)
    )

    if staff_id:
        query = query.filter(Appointment.staff_id == staff_id)

    existing_appointments = query.all()

    # 5. Tạo danh sách các khoảng giờ đã bị chiếm [start, end]
    # (Khắc phục lỗi N+1 Query: dùng appt.service trực tiếp)
    booked_intervals = []
    for appt in existing_appointments:
        duration = appt.service.duration_minutes if appt.service else 30
        start = appt.appointment_date
        end = start + timedelta(minutes=duration)
        booked_intervals.append((start, end))

    # 6. Duyệt các khung giờ từ 08:00 đến 20:00
    start_work = datetime.combine(booking_date, time(8, 0))
    end_work = datetime.combine(booking_date, time(20, 0))
    service_duration = timedelta(minutes=service.duration_minutes)

    available_slots = []
    current_slot = start_work

    while current_slot < end_work:
        slot_end = current_slot + service_duration

        # Edge Case 1: Vượt quá giờ đóng cửa (20:00)
        if slot_end > end_work:
            break

        # RÀO MỚI: Nếu là NGÀY HÔM NAY, không lấy các slot đã qua trong ngày
        if booking_date == now.date() and current_slot <= now:
            current_slot += timedelta(minutes=30)
            continue

        # Edge Case 2: Kiểm tra va chạm khung giờ (Overlap Check)
        is_overlapping = False
        for b_start, b_end in booked_intervals:
            if current_slot < b_end and slot_end > b_start:
                is_overlapping = True
                break

        if not is_overlapping:
            available_slots.append(current_slot.strftime("%H:%M"))

        current_slot += timedelta(minutes=30)

    return available_slots


def create_appointment(customer_id, service_id, staff_id, date_str, time_str, note=None):
    # 1. Validate Khách hàng tồn tại
    customer = User.query.get(customer_id)
    if not customer:
        raise NotFoundError("Khách hàng không tồn tại!")

    # 2. Validate Dịch vụ tồn tại & đang hoạt động
    service = Service.query.filter_by(id=service_id, active=True).first()
    if not service:
        raise NotFoundError("Dịch vụ không tồn tại hoặc đã tạm ngưng!")

    # 3. Validate Nhân viên tồn tại, có role STAFF & đang hoạt động
    staff = User.query.filter_by(id=staff_id, role=UserRole.STAFF, active=True).first()
    if not staff:
        raise NotFoundError("Nhân viên không tồn tại hoặc không khả dụng!")

    # 4. Parse thời gian & Validate định dạng
    try:
        booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValidationError("Định dạng ngày hoặc giờ không hợp lệ (đúng dạng YYYY-MM-DD HH:MM)!")

    # 5. Validate Giờ trống (Slot khả dụng)
    available_slots = get_available_slots(
        service_id=service_id,
        date_str=date_str,
        staff_id=staff_id
    )

    if time_str not in available_slots:
        raise ValidationError("Khung giờ này đã được đặt hoặc không nằm trong ca làm việc!")

    # 6. Tạo record Lịch hẹn
    appointment = Appointment(
        customer_id=customer_id,
        service_id=service_id,
        staff_id=staff_id,
        appointment_date=booking_datetime,
        status=AppointmentStatus.CONFIRMED,
        note=note
    )

    db.session.add(appointment)
    db.session.commit()

    return appointment

def cancel_appointment(appointment_id):
    """Hủy lịch hẹn"""
    appt = Appointment.query.get(appointment_id)
    if not appt or not appt.active:
        raise NotFoundError("Lịch hẹn không tồn tại!")

    if appt.status == AppointmentStatus.CANCELLED:
        raise ValidationError("Lịch hẹn này đã được hủy trước đó!")
    if appt.status == AppointmentStatus.COMPLETED:
        raise ValidationError("Không thể hủy lịch hẹn đã hoàn thành!")

    appt.status = AppointmentStatus.CANCELLED
    db.session.commit()
    return appt


def update_appointment(appointment_id, service_id=None, staff_id=None, date_str=None, time_str=None, note=None, status=None):
    """Sửa lịch hẹn (đổi giờ, nhân viên, dịch vụ, trạng thái, ghi chú)"""
    appt = Appointment.query.get(appointment_id)
    if not appt or not appt.active:
        raise NotFoundError("Lịch hẹn không tồn tại!")

    if appt.status == AppointmentStatus.CANCELLED:
        raise ValidationError("Không thể chỉnh sửa lịch hẹn đã hủy!")
    if appt.status == AppointmentStatus.COMPLETED:
        raise ValidationError("Không thể chỉnh sửa lịch hẹn đã hoàn thành!")

    if note is not None:
        appt.note = note

    if status:
        if isinstance(status, str):
            try:
                appt.status = AppointmentStatus[status.upper()]
            except KeyError:
                raise ValidationError("Trạng thái không hợp lệ! (Chỉ chấp nhận: CONFIRMED, CANCELLED, COMPLETED)")
        elif isinstance(status, AppointmentStatus):
            appt.status = status

    # Kiểm tra nếu đổi ngày/giờ/nhân viên/dịch vụ
    new_service_id = service_id or appt.service_id
    new_staff_id = staff_id or appt.staff_id

    if date_str and time_str:
        try:
            new_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValidationError("Định dạng ngày hoặc giờ không hợp lệ!")

        # Nếu thời gian hoặc nhân viên/dịch vụ bị thay đổi -> Kiểm tra slot trống
        if new_dt != appt.appointment_date or new_service_id != appt.service_id or new_staff_id != appt.staff_id:
            slots = get_available_slots(new_service_id, date_str, new_staff_id)
            if time_str not in slots:
                raise ValidationError("Khung giờ mới chọn không khả dụng!")

            appt.appointment_date = new_dt
            appt.service_id = new_service_id
            appt.staff_id = new_staff_id

    db.session.commit()
    return appt


# =========================================================================
# Nghiệp vụ 5: Quản lý Hóa đơn & Thanh toán (Invoice)
# =========================================================================

def get_invoice_by_id(invoice_id):
    return Invoice.query.get(invoice_id)


def create_invoice(customer_id, staff_id, payment_method, details_data, discount_percent=0, appointment_id=None):
    """
    Tạo hóa đơn, tính tổng tiền, áp dụng giảm giá, trừ tồn kho và đổi trạng thái Lịch hẹn.

    details_data format:
    [
        {"item_type": "SERVICE", "id": 1, "quantity": 1},
        {"item_type": "PRODUCT", "id": 2, "quantity": 2}
    ]
    """
    # 1. Validate Khách hàng & Nhân viên
    customer = get_user_by_id(customer_id)
    if not customer:
        raise NotFoundError("Khách hàng không tồn tại!")

    staff = get_user_by_id(staff_id)
    if not staff or staff.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise ValidationError("Nhân viên thực hiện không hợp lệ!")

    # 2. Validate Giảm giá
    try:
        discount_percent = float(discount_percent)
        if not (0 <= discount_percent <= 100):
            raise ValidationError("Khuyến mãi/giảm giá phải nằm trong khoảng từ 0% đến 100%!")
    except (ValueError, TypeError):
        raise ValidationError("Phần trăm giảm giá không hợp lệ!")

    # 3. Validate Phương thức thanh toán
    if isinstance(payment_method, str):
        try:
            payment_method = PaymentMethod[payment_method.upper()]
        except KeyError:
            raise ValidationError("Phương thức thanh toán không hợp lệ! (Chấp nhận: CASH, BANK_TRANSFER, CARD)")

    # 4. Validate Lịch hẹn (nếu hóa đơn này xuất từ Lịch hẹn)
    appointment = None
    if appointment_id:
        appointment = Appointment.query.get(appointment_id)
        if not appointment or not appointment.active:
            raise NotFoundError("Lịch hẹn không tồn tại!")
        if appointment.status == AppointmentStatus.CANCELLED:
            raise ValidationError("Không thể lập hóa đơn cho lịch hẹn đã hủy!")

        # Kiểm tra lịch hẹn đã lập hóa đơn chưa
        existing_inv = Invoice.query.filter_by(appointment_id=appointment_id).first()
        if existing_inv:
            raise DuplicateError("Lịch hẹn này đã được lập hóa đơn và thanh toán trước đó!")

    if not details_data or not isinstance(details_data, list):
        raise ValidationError("Danh sách dịch vụ/sản phẩm thanh toán không được để trống!")

    gross_total = 0.0
    invoice_details = []

    # 5. Duyệt danh sách chi tiết & Tính tiền + Trừ tồn kho
    for item in details_data:
        item_type_str = str(item.get('item_type', '')).upper()
        item_id = item.get('id')

        try:
            quantity = int(item.get('quantity', 1))
            if quantity <= 0:
                raise ValidationError("Số lượng phải lớn hơn 0!")
        except (ValueError, TypeError):
            raise ValidationError("Số lượng mặt hàng phải là số nguyên!")

        if item_type_str == 'SERVICE':
            service = Service.query.get(item_id)
            if not service or not service.active:
                raise NotFoundError(f"Dịch vụ ID {item_id} không tồn tại hoặc đã bị ngừng!")

            unit_price = float(service.price)
            subtotal = unit_price * quantity
            gross_total += subtotal

            detail = InvoiceDetail(
                item_type=InvoiceItemType.SERVICE,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                service_id=service.id
            )
            invoice_details.append(detail)

        elif item_type_str == 'PRODUCT':
            product = Product.query.get(item_id)
            if not product or not product.active:
                raise NotFoundError(f"Sản phẩm ID {item_id} không tồn tại hoặc đã ngừng kinh doanh!")

            # Kiểm tra tồn kho
            if product.stock_quantity < quantity:
                raise ValidationError(
                    f"Sản phẩm '{product.product_name}' không đủ hàng trong kho! (Tồn: {product.stock_quantity}, Yêu cầu: {quantity})")

            # Tự động trừ kho
            product.stock_quantity -= quantity

            unit_price = float(product.price)
            subtotal = unit_price * quantity
            gross_total += subtotal

            detail = InvoiceDetail(
                item_type=InvoiceItemType.PRODUCT,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                product_id=product.id
            )
            invoice_details.append(detail)
        else:
            raise ValidationError("Loại thanh toán phải là SERVICE hoặc PRODUCT!")

    # 6. Tính tổng tiền sau khi giảm giá
    total_amount = gross_total * (1.0 - (discount_percent / 100.0))

    # 7. Khởi tạo đối tượng Hóa đơn
    invoice = Invoice(
        customer_id=customer_id,
        staff_id=staff_id,
        appointment_id=appointment_id,
        payment_method=payment_method,
        discount_percent=discount_percent,
        total_amount=total_amount,
        details=invoice_details
    )

    # 8. Cập nhật trạng thái Lịch hẹn -> COMPLETED
    if appointment:
        appointment.status = AppointmentStatus.COMPLETED

    db.session.add(invoice)
    try:
        db.session.commit()
        return invoice
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể lưu hóa đơn!")

