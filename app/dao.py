import hashlib
import re
from datetime import datetime, timedelta, time
from sqlalchemy.exc import IntegrityError
from app.models import User, UserRole, Service, Product, Appointment, AppointmentStatus, InvoiceDetail, InvoiceItemType, \
    Invoice, PaymentMethod, ProductUnit, ServiceProduct, InvoiceStatus, PromotionType, Promotion
from app import db, app
from app.exceptions import ValidationError, DuplicateError, NotFoundError



def get_user_by_id(user_id):
    return User.query.get(user_id)


def _validate_password_strength(password):
    if not password or len(password) < 8:
        raise ValidationError("Mật khẩu phải từ 8 ký tự trở lên!")
    if not re.search(r'[0-9]', password):
        raise ValidationError("Mật khẩu phải chứa ít nhất 1 chữ số!")
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Mật khẩu phải chứa ít nhất 1 ký tự hoa!")
    if not re.search(r'[a-z]', password):
        raise ValidationError("Mật khẩu phải chứa ít nhất 1 ký tự thường!")


def validate_user_input(full_name, username, password, phone, email, is_update=False, avatar=None):
    if not full_name or not full_name.strip():
        raise ValidationError("Vui lòng nhập họ tên!")
    if len(full_name.strip()) > 100:
        raise ValidationError("Họ tên không được quá 100 ký tự!")

    if avatar and len(avatar.strip()) > 255:
        raise ValidationError("Đường dẫn ảnh đại diện không được vượt quá 255 ký tự!")

    if phone is None or not re.match(r'^0[0-9]{9}$', phone.strip()):
        raise ValidationError("Số điện thoại không hợp lệ (phải gồm đúng 10 chữ số và bắt đầu bằng 0)!")

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

        _validate_password_strength(password)


def add_user(full_name, username, password, phone, email, role=UserRole.CUSTOMER, avatar=None):
    validate_user_input(full_name, username, password, phone, email, is_update=False, avatar=avatar)

    username = username.strip()
    email = email.strip()

    if User.query.filter(User.username == username).first():
        raise DuplicateError(f"Username '{username}' đã tồn tại!")
    if User.query.filter(User.email == email).first():
        raise DuplicateError(f"Email '{email}' đã tồn tại!")

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
    query = User.query
    if role:
        query = query.filter(User.role == role)
    return query.all()


def update_user_profile(user_id, full_name, phone, email, avatar=None):
    u = get_user_by_id(user_id)
    if not u:
        raise NotFoundError("Người dùng không tồn tại!")

    validate_user_input(full_name, u.username, None, phone, email, is_update=True, avatar=avatar)
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


def change_password(user_id, old_password, new_password):
    u = get_user_by_id(user_id)
    if not u:
        raise NotFoundError("Người dùng không tồn tại!")

    if not old_password:
        raise ValidationError("Vui lòng nhập mật khẩu hiện tại!")

    old_hashed = str(hashlib.md5(old_password.encode('utf-8')).hexdigest())
    if old_hashed != u.password:
        raise ValidationError("Mật khẩu hiện tại không chính xác!")

    if old_password == new_password:
        raise ValidationError("Mật khẩu mới không được trùng với mật khẩu hiện tại!")

    _validate_password_strength(new_password)

    new_hashed = str(hashlib.md5(new_password.strip().encode('utf-8')).hexdigest())
    if new_hashed == u.password:
        raise ValidationError("Mật khẩu mới không được trùng với mật khẩu hiện tại!")

    u.password = new_hashed
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể đổi mật khẩu!")
    return u


def toggle_user_active(user_id):
    u = get_user_by_id(user_id)
    if not u:
        raise NotFoundError("Người dùng không tồn tại!")

    u.active = not u.active
    db.session.commit()
    return u


def delete_user_soft(user_id):
    u = get_user_by_id(user_id)
    if not u:
        raise NotFoundError("Người dùng không tồn tại!")

    u.active = False
    db.session.commit()
    return u


def get_service_by_id(service_id):
    return Service.query.get(service_id)


def get_all_services():
    return Service.query.all()


def validate_service_input(name, price, duration, is_update=False, service_id=None, avatar=None):
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

    name = name.strip()
    query = Service.query.filter(Service.service_name == name)
    if is_update and service_id:
        query = query.filter(Service.id != service_id)

    if query.first():
        raise DuplicateError(f"Dịch vụ '{name}' đã tồn tại trong hệ thống!")


def load_services(kw=None, page=1, page_size=None):
    query = Service.query.filter(Service.active.__eq__(True))

    if kw and kw.strip():
        query = query.filter(Service.service_name.contains(kw.strip()))

    if page_size is None:
        page_size = app.config.get('PAGE_SIZE', 4)

    if page:
        start = (page - 1) * page_size
        query = query.offset(start).limit(page_size)

    return query.all()


def count_services(kw=None):
    query = Service.query.filter(Service.active.__eq__(True))
    if kw:
        query = query.filter(Service.service_name.contains(kw.strip()))
    return query.count()


def get_services_paged(page=1, page_size=10):
    query = Service.query.filter(Service.active == True)
    total_items = query.count()

    services = query.order_by(Service.id.asc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size).all()

    return services, total_items


def add_service(name, price, duration, description=None, avatar=None):
    validate_service_input(name, price, duration, avatar=avatar)

    s = Service(
        service_name=name.strip(),
        price=float(price),
        duration_minutes=int(duration),
        description=description.strip() if description else None,
        avatar=avatar.strip() if avatar else None
    )

    db.session.add(s)
    try:
        db.session.commit()
        return s
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể thêm dịch vụ!")


def update_service(service_id, name=None, price=None, duration=None, description=None, avatar=None):
    s = Service.query.get(service_id)
    if not s or not s.active:
        raise NotFoundError("Dịch vụ không tồn tại!")

    if name is not None and str(name).strip() != "":
        clean_name = str(name).strip()
        if clean_name != s.service_name:
            existing = Service.query.filter(
                Service.service_name == clean_name,
                Service.id != service_id,
                Service.active == True
            ).first()
            if existing:
                raise DuplicateError(f"Tên dịch vụ '{clean_name}' đã tồn tại!")
            s.service_name = clean_name

    if price is not None and str(price).strip() != "":
        try:
            s.price = float(price)
        except (ValueError, TypeError):
            raise ValidationError("Giá tiền không hợp lệ!")

    if duration is not None and str(duration).strip() != "":
        try:
            s.duration_minutes = int(float(duration))
        except (ValueError, TypeError):
            raise ValidationError("Thời lượng không hợp lệ!")

    if description is not None:
        s.description = str(description).strip() if str(description).strip() else None

    if avatar is not None:
        s.avatar = str(avatar).strip() if str(avatar).strip() else None

    db.session.commit()
    return s


def delete_service(service_id):
    s = get_service_by_id(service_id)
    if not s:
        raise NotFoundError("Không tìm thấy dịch vụ!")

    s.active = False
    db.session.commit()
    return True


def get_product_by_id(product_id):
    return Product.query.get(product_id)


def get_all_products():
    return Product.query.all()


def load_products(kw=None, page=None):
    query = Product.query.filter(Product.active.__eq__(True))
    if kw:
        query = query.filter(Product.product_name.contains(kw.strip()))

    page_size = app.config.get('PAGE_SIZE', 8)
    if page:
        start = (page - 1) * page_size
        query = query.offset(start).limit(page_size)

    return query.all()


def count_products(kw=None):
    query = Product.query.filter(Product.active.__eq__(True))
    if kw:
        query = query.filter(Product.product_name.contains(kw.strip()))
    return query.count()


def _validate_product_core(name, unit, min_stock, is_update=False, product_id=None):
    if not name or not name.strip():
        raise ValidationError("Tên sản phẩm không được để trống!")

    valid_units = ('CHAI', 'GOI', 'ML', 'GRAM')
    unit_str = unit.upper() if isinstance(unit, str) else (unit.name if unit else None)
    if unit_str not in valid_units:
        raise ValidationError(f"Đơn vị tính không hợp lệ! Chỉ chấp nhận: {', '.join(valid_units)}")

    try:
        min_stock = float(min_stock)
        if min_stock < 0:
            raise ValidationError("Mức tồn kho tối thiểu không được âm!")
    except (ValueError, TypeError):
        raise ValidationError("Mức tồn kho tối thiểu phải là số hợp lệ!")

    name = name.strip()
    query = Product.query.filter(Product.product_name == name)
    if is_update and product_id:
        query = query.filter(Product.id != product_id)
    if query.first():
        raise DuplicateError(f"Sản phẩm '{name}' đã tồn tại trong hệ thống!")

    return unit_str


def add_product(name, unit, stock_quantity, min_stock_level):
    unit_str = _validate_product_core(name, unit, min_stock_level)
    try:
        stock_quantity = float(stock_quantity)
        if stock_quantity < 0:
            raise ValidationError("Số lượng tồn kho không được âm!")
    except (ValueError, TypeError):
        raise ValidationError("Số lượng tồn kho phải là số hợp lệ!")

    p = Product(
        product_name=name.strip(),
        unit=ProductUnit[unit_str],
        stock_quantity=stock_quantity,
        min_stock_level=float(min_stock_level)
    )
    db.session.add(p)
    try:
        db.session.commit()
        return p
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể thêm sản phẩm!")


def update_product(product_id, name, unit, min_stock_level):
    p = get_product_by_id(product_id)
    if not p:
        raise NotFoundError("Không tìm thấy sản phẩm!")

    unit_str = _validate_product_core(name, unit, min_stock_level, is_update=True, product_id=product_id)

    p.product_name = name.strip()
    p.unit = ProductUnit[unit_str]
    p.min_stock_level = float(min_stock_level)
    try:
        db.session.commit()
        return p
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể cập nhật sản phẩm!")


def delete_product(product_id):
    p = get_product_by_id(product_id)
    if not p:
        raise NotFoundError("Không tìm thấy sản phẩm!")

    p.active = False
    db.session.commit()
    return True


def check_low_stock_products():
    return Product.query.filter(
        Product.active.__eq__(True),
        Product.stock_quantity <= Product.min_stock_level
    ).all()


def _validate_stock_quantity(quantity):
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        raise ValidationError("Số lượng phải là số nguyên!")
    if quantity <= 0:
        raise ValidationError("Số lượng phải lớn hơn 0!")
    return quantity


def import_stock(product_id, quantity):
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


def get_appointment_by_id(appointment_id):
    return Appointment.query.get(appointment_id)


def get_appointments_by_customer(customer_id):
    appts = Appointment.query.filter(
        Appointment.customer_id == customer_id,
        Appointment.active.__eq__(True)
    ).order_by(Appointment.appointment_date.desc()).all()

    for appt in appts:
        inv = Invoice.query.filter(Invoice.appointment_id == appt.id, Invoice.active.__eq__(True)).first()
        appt.has_invoice = True if inv else False

    return appts


def get_appointments_by_staff(staff_id, date_str=None, page=1, page_size=10):
    query = Appointment.query.filter(
        Appointment.staff_id == staff_id,
        Appointment.active.__eq__(True)
    )

    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Định dạng ngày không hợp lệ! Dùng YYYY-MM-DD")
        start_of_day = datetime.combine(target_date, time(0, 0, 0))
        end_of_day = datetime.combine(target_date, time(23, 59, 59))
        query = query.filter(
            Appointment.appointment_date >= start_of_day,
            Appointment.appointment_date <= end_of_day
        )

    total_items = query.count()

    query = query.order_by(Appointment.appointment_date.asc())

    if page:
        start = (page - 1) * page_size
        query = query.offset(start).limit(page_size)

    appointments = query.all()

    for appt in appointments:
        inv = Invoice.query.filter(Invoice.appointment_id == appt.id, Invoice.active.__eq__(True)).first()
        appt.has_invoice = True if inv else False

    return appointments, total_items


def get_appointments(date=None, staff_id=None, customer_id=None, status=None, page=1, page_size=None):
    query = Appointment.query.filter(Appointment.active.__eq__(True))

    if date:
        if isinstance(date, str):
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Định dạng ngày không hợp lệ! Dùng YYYY-MM-DD")
        elif isinstance(date, datetime):
            target_date = date.date()
        else:
            target_date = date

        start_of_day = datetime.combine(target_date, time(0, 0, 0))
        end_of_day = datetime.combine(target_date, time(23, 59, 59))
        query = query.filter(
            Appointment.appointment_date >= start_of_day,
            Appointment.appointment_date <= end_of_day
        )

    if staff_id:
        query = query.filter(Appointment.staff_id == staff_id)

    if customer_id:
        query = query.filter(Appointment.customer_id == customer_id)

    if status:
        try:
            status_enum = AppointmentStatus[status.upper()] if isinstance(status, str) else status
            query = query.filter(Appointment.status == status_enum)
        except KeyError:
            pass

    query = query.order_by(Appointment.appointment_date.asc())

    if page:
        page_size = page_size or app.config.get('PAGE_SIZE', 10)
        start = (page - 1) * page_size
        query = query.offset(start).limit(page_size)

    return query.all()


def get_available_slots(service_id, date_str, staff_id=None, exclude_appointment_id=None):
    service = get_service_by_id(service_id)
    if not service or not service.active:
        raise NotFoundError("Dịch vụ không tồn tại hoặc đã ngưng hoạt động!")

    if staff_id:
        staff = get_user_by_id(staff_id)
        if not staff or not staff.active or staff.role != UserRole.STAFF:
            raise NotFoundError("Nhân viên không tồn tại hoặc không hợp lệ!")

    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Định dạng ngày không hợp lệ! Dùng YYYY-MM-DD")

    now = datetime.now()

    if booking_date > now.date() + timedelta(days=30):
        raise ValidationError("Chỉ được đặt lịch hẹn trước tối đa 30 ngày!")
    if booking_date < now.date():
        return []

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

    target_appt = None
    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)
        target_appt = get_appointment_by_id(exclude_appointment_id)

    existing_appointments = query.all()

    booked_intervals = []
    for appt in existing_appointments:
        duration = appt.service.duration_minutes if appt.service else 30
        start = appt.appointment_date
        end = start + timedelta(minutes=duration)
        booked_intervals.append((start, end))

    start_work = datetime.combine(booking_date, time(8, 0))
    end_work = datetime.combine(booking_date, time(20, 0))
    service_duration = timedelta(minutes=service.duration_minutes)

    available_slots = []
    current_slot = start_work

    while current_slot < end_work:
        slot_end = current_slot + service_duration

        if slot_end > end_work:
            break

        if booking_date == now.date() and current_slot <= now:
            current_slot += timedelta(hours=1)
            continue

        is_overlapping = False
        for b_start, b_end in booked_intervals:
            if current_slot < b_end and slot_end > b_start:
                is_overlapping = True
                break

        if not is_overlapping:
            available_slots.append(current_slot.strftime("%H:%M"))

        current_slot += timedelta(hours=1)

    if target_appt and target_appt.appointment_date.date() == booking_date:
        original_time_str = target_appt.appointment_date.strftime("%H:%M")
        if original_time_str not in available_slots:
            available_slots.append(original_time_str)
            available_slots.sort()

    return available_slots


def create_appointment(customer_id, service_id, staff_id=None, date_str=None, time_str=None, note=None):
    customer = User.query.get(customer_id)
    if not customer:
        raise NotFoundError("Khách hàng không tồn tại!")

    service = Service.query.filter_by(id=service_id, active=True).first()
    if not service:
        raise NotFoundError("Dịch vụ không tồn tại hoặc đã tạm ngưng!")

    try:
        booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValidationError("Định dạng ngày hoặc giờ không hợp lệ (đúng dạng YYYY-MM-DD HH:MM)!")

    if booking_datetime < datetime.now():
        raise ValidationError("Không thể đặt lịch hẹn trong quá khứ!")

    if booking_datetime.date() > datetime.now().date() + timedelta(days=30):
        raise ValidationError("Chỉ được đặt lịch hẹn trước tối đa 30 ngày!")

    available_slots = get_available_slots(
        service_id=service_id,
        date_str=date_str,
        staff_id=staff_id
    )

    if time_str not in available_slots:
        raise ValidationError("Khung giờ này đã được đặt hoặc không nằm trong ca làm việc!")

    assigned_staff_id = staff_id

    if staff_id:
        staff = User.query.filter_by(id=staff_id, role=UserRole.STAFF, active=True).first()
        if not staff:
            raise NotFoundError("Nhân viên không tồn tại hoặc không khả dụng!")
    else:
        all_staffs = User.query.filter_by(role=UserRole.STAFF, active=True).all()
        new_end = booking_datetime + timedelta(minutes=service.duration_minutes)
        assigned_staff_id = None

        for st in all_staffs:
            staff_appointments = Appointment.query.filter(
                Appointment.staff_id == st.id,
                Appointment.status != AppointmentStatus.CANCELLED,
                Appointment.active.__eq__(True)
            ).all()

            has_conflict = False

            for existing in staff_appointments:
                existing_duration = (
                    existing.service.duration_minutes
                    if existing.service else 30
                )

                existing_start = existing.appointment_date
                existing_end = existing_start + timedelta(
                    minutes=existing_duration
                )

                if (
                        booking_datetime < existing_end
                        and new_end > existing_start
                ):
                    has_conflict = True
                    break

            if not has_conflict:
                assigned_staff_id = st.id
                break

        if assigned_staff_id is None:
            raise ValidationError(
                "Không có stylist nào khả dụng trong khung giờ này!"
            )

    new_end = booking_datetime + timedelta(minutes=service.duration_minutes)
    existing_customer_appts = Appointment.query.filter(
        Appointment.customer_id == customer_id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.active.__eq__(True)
    ).all()

    for e in existing_customer_appts:
        e_duration = e.service.duration_minutes if e.service else 30
        e_end = e.appointment_date + timedelta(minutes=e_duration)
        if booking_datetime < e_end and new_end > e.appointment_date:
            raise ValidationError("Bạn đã có lịch hẹn khác trùng khung giờ này!")

    clean_note = note.strip()[:255] if note else None

    appointment = Appointment(
        customer_id=customer_id,
        service_id=service_id,
        staff_id=assigned_staff_id,
        appointment_date=booking_datetime,
        status=AppointmentStatus.CONFIRMED,
        note=clean_note
    )

    db.session.add(appointment)
    db.session.commit()

    return appointment


def cancel_appointment(appointment_id):
    appt = Appointment.query.get(appointment_id)
    if not appt or not appt.active:
        raise NotFoundError("Lịch hẹn không tồn tại!")

    if appt.appointment_date - datetime.now() < timedelta(hours=2):
        raise ValidationError(
            "Chỉ được hủy lịch hẹn trước giờ hẹn tối thiểu 2 giờ! Vui lòng liên hệ trực tiếp salon.")

    existing_invoice = Invoice.query.filter(Invoice.appointment_id == appt.id, Invoice.active.__eq__(True)).first()
    if existing_invoice:
        raise ValidationError("Lịch hẹn đã có hóa đơn, không thể sửa/hủy trực tuyến! Vui lòng liên hệ salon.")

    if appt.status == AppointmentStatus.CANCELLED:
        raise ValidationError("Lịch hẹn này đã được hủy trước đó!")
    if appt.status == AppointmentStatus.COMPLETED:
        raise ValidationError("Không thể hủy lịch hẹn đã hoàn thành!")

    appt.status = AppointmentStatus.CANCELLED
    db.session.commit()
    return appt


def update_appointment(appointment_id, service_id=None, staff_id=None, date_str=None, time_str=None, note=None, status=None):
    appt = Appointment.query.get(appointment_id)
    if not appt or not appt.active:
        raise NotFoundError("Lịch hẹn không tồn tại!")

    if appt.appointment_date - datetime.now() < timedelta(hours=2):
        raise ValidationError(
            "Chỉ được sửa lịch hẹn trước giờ hẹn tối thiểu 2 giờ! Vui lòng liên hệ trực tiếp salon.")

    existing_invoice = Invoice.query.filter(Invoice.appointment_id == appt.id, Invoice.active.__eq__(True)).first()
    if existing_invoice:
        raise ValidationError("Lịch hẹn đã có hóa đơn, không thể sửa/hủy trực tuyến! Vui lòng liên hệ salon.")

    if appt.status == AppointmentStatus.CANCELLED:
        raise ValidationError("Không thể chỉnh sửa lịch hẹn đã hủy!")
    if appt.status == AppointmentStatus.COMPLETED:
        raise ValidationError("Không thể chỉnh sửa lịch hẹn đã hoàn thành!")

    if note is not None:
        appt.note = note.strip()[:255] if note else None

    if status:
        if isinstance(status, str):
            try:
                appt.status = AppointmentStatus[status.upper()]
            except KeyError:
                raise ValidationError("Trạng thái không hợp lệ! (Chỉ chấp nhận: CONFIRMED, CANCELLED, COMPLETED)")
        elif isinstance(status, AppointmentStatus):
            appt.status = status

    new_service_id = service_id or appt.service_id
    new_staff_id = staff_id or appt.staff_id

    if service_id and service_id != appt.service_id:
        service = Service.query.filter_by(id=service_id, active=True).first()
        if not service:
            raise NotFoundError("Dịch vụ mới không tồn tại hoặc đã tạm ngưng!")

    if staff_id and staff_id != appt.staff_id:
        staff = User.query.filter_by(id=staff_id, role=UserRole.STAFF, active=True).first()
        if not staff:
            raise NotFoundError("Nhân viên mới không tồn tại hoặc không khả dụng!")

    if date_str and time_str:
        try:
            new_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValidationError("Định dạng ngày hoặc giờ không hợp lệ!")
    else:
        new_dt = appt.appointment_date
        date_str = new_dt.strftime("%Y-%m-%d")
        time_str = new_dt.strftime("%H:%M")

    if new_dt != appt.appointment_date or new_service_id != appt.service_id or new_staff_id != appt.staff_id:
        if new_dt < datetime.now():
            raise ValidationError("Không thể chuyển lịch hẹn về thời gian trong quá khứ!")

        if new_dt.date() > datetime.now().date() + timedelta(days=30):
            raise ValidationError("Chỉ được đổi lịch hẹn trong vòng 30 ngày kể từ hôm nay!")

        slots = get_available_slots(
            new_service_id, date_str, new_staff_id,
            exclude_appointment_id=appointment_id
        )
        if time_str not in slots:
            raise ValidationError("Khung giờ mới chọn không khả dụng!")

        target_service = Service.query.get(new_service_id)
        duration = target_service.duration_minutes if target_service else 30
        new_end = new_dt + timedelta(minutes=duration)

        existing_appts = Appointment.query.filter(
            Appointment.customer_id == appt.customer_id,
            Appointment.id != appt.id,
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.active.__eq__(True)
        ).all()

        for e in existing_appts:
            e_duration = e.service.duration_minutes if e.service else 30
            e_end = e.appointment_date + timedelta(minutes=e_duration)
            if new_dt < e_end and new_end > e.appointment_date:
                raise ValidationError("Bạn đã có lịch hẹn khác trùng khung giờ này!")

        appt.appointment_date = new_dt
        appt.service_id = new_service_id
        appt.staff_id = new_staff_id

    db.session.commit()
    return appt


def _validate_invoice_participants(customer_id, staff_id):
    customer = User.query.filter_by(id=customer_id, role=UserRole.CUSTOMER, active=True).first()
    if not customer:
        raise NotFoundError("Khách hàng không tồn tại hoặc không hợp lệ!")
    staff = User.query.filter_by(id=staff_id, role=UserRole.STAFF, active=True).first()
    if not staff:
        raise NotFoundError("Nhân viên không tồn tại hoặc không hợp lệ!")
    return customer, staff


def _validate_invoice_appointment(appointment_id, staff_id):
    if not appointment_id:
        return None
    appointment = Appointment.query.get(appointment_id)
    if not appointment or not appointment.active:
        raise NotFoundError("Lịch hẹn không tồn tại!")
    if appointment.staff_id != staff_id:
        raise ValidationError("Bạn không được lập hóa đơn cho lịch hẹn không phải do mình phụ trách!")

    existing = Invoice.query.filter(Invoice.appointment_id == appointment_id, Invoice.active.__eq__(True)).first()
    if existing:
        raise DuplicateError("Lịch hẹn này đã có hóa đơn!")
    return appointment


def _validate_and_prepare_invoice_items(details_data, service_ids_in_invoice):
    if not details_data:
        raise ValidationError("Hóa đơn phải có ít nhất 1 dịch vụ!")

    validated_items = []
    gross_total = 0.0
    has_service = False

    for line in details_data:
        item_type_raw = line.get('item_type')
        item_id = line.get('item_id') or line.get('service_id') or line.get('product_id')
        quantity = line.get('quantity', 1)

        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValidationError("Số lượng phải lớn hơn 0!")
        except (ValueError, TypeError):
            raise ValidationError("Số lượng không hợp lệ!")

        if item_type_raw == 'SERVICE':
            service = Service.query.filter_by(id=item_id, active=True).first()
            if not service:
                raise NotFoundError(f"Dịch vụ ID {item_id} không tồn tại hoặc đã ngừng!")
            unit_price = float(service.price)
            subtotal = unit_price * quantity
            gross_total += subtotal
            has_service = True
            validated_items.append({
                "item_type": InvoiceItemType.SERVICE, "entity": service,
                "quantity": quantity, "unit_price": unit_price, "subtotal": subtotal
            })

        elif item_type_raw == 'PRODUCT_USED':
            product = Product.query.filter_by(id=item_id, active=True).first()
            if not product:
                raise NotFoundError(f"Sản phẩm ID {item_id} không tồn tại hoặc đã ngừng!")

            allowed = ServiceProduct.query.filter(
                ServiceProduct.product_id == product.id,
                ServiceProduct.service_id.in_(service_ids_in_invoice)
            ).first()
            if not allowed:
                raise ValidationError(
                    f"Sản phẩm '{product.product_name}' không nằm trong danh sách khả dụng cho (các) dịch vụ đã chọn!"
                )
            if product.stock_quantity < quantity:
                raise ValidationError(
                    f"Sản phẩm '{product.product_name}' không đủ tồn kho! (Tồn: {product.stock_quantity}, Yêu cầu: {quantity})"
                )
            validated_items.append({
                "item_type": InvoiceItemType.PRODUCT_USED, "entity": product,
                "quantity": quantity, "unit_price": 0.0, "subtotal": 0.0
            })
        else:
            raise ValidationError(f"item_type không hợp lệ: '{item_type_raw}' (chỉ SERVICE hoặc PRODUCT_USED)")

    if not has_service:
        raise ValidationError("Hóa đơn phải có ít nhất 1 dòng dịch vụ (SERVICE)!")

    return validated_items, gross_total


def get_invoice_by_id(invoice_id):
    return Invoice.query.get(invoice_id)


def get_invoices(staff_id=None, status=None, customer_id=None, from_date=None, to_date=None, page=1, page_size=None):
    query = Invoice.query.filter(Invoice.active.__eq__(True))

    if staff_id:
        query = query.filter(Invoice.staff_id == staff_id)
    if status:
        try:
            status_enum = InvoiceStatus[status.upper()] if isinstance(status, str) else status
            query = query.filter(Invoice.status == status_enum)
        except KeyError:
            pass
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if from_date:
        query = query.filter(Invoice.invoice_date >= from_date)
    if to_date:
        query = query.filter(Invoice.invoice_date <= to_date)

    query = query.order_by(Invoice.invoice_date.desc())

    total_items = query.count()

    if page:
        page_size = page_size or app.config.get('PAGE_SIZE', 10)
        start = (page - 1) * page_size
        query = query.offset(start).limit(page_size)

    invoices = query.all()
    return invoices, total_items


def create_invoice(customer_id, staff_id, details_data, appointment_id=None):
    try:
        _validate_invoice_participants(customer_id, staff_id)
        appointment = _validate_invoice_appointment(appointment_id, staff_id)

        service_ids_in_invoice = {
            line.get('item_id') or line.get('service_id')
            for line in details_data if line.get('item_type') == 'SERVICE'
        }

        validated_items, gross_total = _validate_and_prepare_invoice_items(details_data, service_ids_in_invoice)

        invoice_details = [
            InvoiceDetail(
                item_type=item["item_type"], quantity=item["quantity"],
                unit_price=item["unit_price"], subtotal=item["subtotal"],
                service_id=item["entity"].id if item["item_type"] == InvoiceItemType.SERVICE else None,
                product_id=item["entity"].id if item["item_type"] == InvoiceItemType.PRODUCT_USED else None
            ) for item in validated_items
        ]

        invoice = Invoice(
            customer_id=customer_id, staff_id=staff_id, appointment_id=appointment_id,
            status=InvoiceStatus.DRAFT, total_amount=gross_total, details=invoice_details
        )

        db.session.add(invoice)

        if appointment:
            appointment.status = AppointmentStatus.COMPLETED
            db.session.add(appointment)
        elif appointment_id:
            appt = Appointment.query.get(appointment_id)
            if appt:
                appt.status = AppointmentStatus.COMPLETED
                db.session.add(appt)

        db.session.commit()
        return invoice

    except IntegrityError:
        db.session.rollback()
        raise DuplicateError("Lịch hẹn này đã có hóa đơn (trùng lặp)!")

    except Exception as ex:
        db.session.rollback()
        raise ex


def confirm_invoice_payment(invoice_id, receptionist_id, payment_method, promotion_id=None):
    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice or not invoice.active:
            raise NotFoundError("Hóa đơn không tồn tại!")
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValidationError("Hóa đơn không ở trạng thái nháp, không thể xác nhận thanh toán!")

        receptionist = User.query.filter_by(id=receptionist_id, role=UserRole.RECEPTIONIST, active=True).first()
        if not receptionist:
            receptionist = User.query.filter_by(id=receptionist_id, role=UserRole.ADMIN, active=True).first()
            if not receptionist:
                raise NotFoundError("Người xác nhận không hợp lệ!")

        try:
            payment_enum = PaymentMethod[payment_method.upper()] if isinstance(payment_method, str) else payment_method
        except KeyError:
            raise ValidationError(f"Hình thức thanh toán '{payment_method}' không hợp lệ!")

        final_amount = invoice.total_amount

        if promotion_id:
            promo = Promotion.query.filter_by(id=promotion_id, active=True).first()
            if not promo:
                raise NotFoundError("Khuyến mãi không tồn tại!")
            now = datetime.now()
            if now < promo.start_date or now > promo.end_date:
                raise ValidationError(f"Khuyến mãi '{promo.promo_code}' đã hết hiệu lực!")

            if promo.promo_type == PromotionType.PERCENT:
                final_amount = invoice.total_amount * (1 - promo.value / 100.0)
            else:
                final_amount = max(invoice.total_amount - promo.value, 0)

            invoice.promotion_id = promo.id

        for detail in invoice.details:
            if detail.item_type == InvoiceItemType.PRODUCT_USED and detail.product_id:
                product = Product.query.get(detail.product_id)
                if not product or product.stock_quantity < detail.quantity:
                    raise ValidationError(
                        f"Sản phẩm '{product.product_name if product else detail.product_id}' không còn đủ tồn kho để hoàn tất hóa đơn!"
                    )
                product.stock_quantity -= detail.quantity

        invoice.status = InvoiceStatus.PAID
        invoice.payment_method = payment_enum
        invoice.receptionist_id = receptionist_id
        invoice.total_amount = final_amount

        db.session.commit()
        return invoice

    except Exception as ex:
        db.session.rollback()
        raise ex


def cancel_invoice_draft(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice or not invoice.active:
        raise NotFoundError("Hóa đơn không tồn tại!")

    if invoice.status != InvoiceStatus.DRAFT:
        raise ValidationError("Chỉ được hủy hóa đơn ở trạng thái nháp! Hóa đơn đã hoàn tất không thể hủy.")

    invoice.status = InvoiceStatus.CANCELLED
    invoice.active = False
    invoice.appointment_id = None

    try:
        db.session.commit()
        return invoice
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể hủy hóa đơn!")


def update_invoice_draft(invoice_id, details_data):
    invoice = Invoice.query.get(invoice_id)
    if not invoice or not invoice.active:
        raise NotFoundError("Hóa đơn không tồn tại!")

    if invoice.status != InvoiceStatus.DRAFT:
        raise ValidationError("Chỉ được sửa hóa đơn ở trạng thái nháp! Hóa đơn đã hoàn tất không thể sửa.")

    try:
        service_ids_in_invoice = {
            line.get('item_id') or line.get('service_id')
            for line in details_data if line.get('item_type') == 'SERVICE'
        }
        validated_items, gross_total = _validate_and_prepare_invoice_items(details_data, service_ids_in_invoice)

        for old_detail in list(invoice.details):
            db.session.delete(old_detail)

        new_details = [
            InvoiceDetail(
                item_type=item["item_type"], quantity=item["quantity"],
                unit_price=item["unit_price"], subtotal=item["subtotal"],
                service_id=item["entity"].id if item["item_type"] == InvoiceItemType.SERVICE else None,
                product_id=item["entity"].id if item["item_type"] == InvoiceItemType.PRODUCT_USED else None,
                invoice_id=invoice.id
            ) for item in validated_items
        ]
        db.session.add_all(new_details)

        invoice.total_amount = gross_total
        db.session.commit()
        return invoice

    except Exception as ex:
        db.session.rollback()
        raise ex


def _get_period_key(invoice_date, period_type):
    if period_type == 'day':
        return invoice_date.strftime('%Y-%m-%d')
    elif period_type == 'month':
        return invoice_date.strftime('%Y-%m')
    elif period_type == 'quarter':
        quarter = (invoice_date.month - 1) // 3 + 1
        return f"{invoice_date.year}-Q{quarter}"
    elif period_type == 'year':
        return str(invoice_date.year)


def _parse_date_bound(date_str, is_end_of_day=False):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(hour=23, minute=59, second=59) if is_end_of_day else dt
    except ValueError:
        raise ValidationError("Định dạng ngày không hợp lệ! Vui lòng dùng YYYY-MM-DD.")


def get_revenue_report(period_type='day', from_date_str=None, to_date_str=None):
    valid_periods = ['day', 'month', 'quarter', 'year']
    if period_type not in valid_periods:
        raise ValidationError(
            f"period_type '{period_type}' không hợp lệ! Chỉ chấp nhận: {', '.join(valid_periods)}"
        )

    from_date = _parse_date_bound(from_date_str, is_end_of_day=False)
    to_date = _parse_date_bound(to_date_str, is_end_of_day=True)

    query = Invoice.query.filter(Invoice.status == InvoiceStatus.PAID)
    if from_date:
        query = query.filter(Invoice.invoice_date >= from_date)
    if to_date:
        query = query.filter(Invoice.invoice_date <= to_date)

    invoices = query.all()

    groups = {}
    for inv in invoices:
        key = _get_period_key(inv.invoice_date, period_type)
        if key not in groups:
            groups[key] = {"period": key, "total_invoices": 0, "total_revenue": 0.0}
        groups[key]["total_invoices"] += 1
        groups[key]["total_revenue"] += float(inv.total_amount or 0)

    return sorted(groups.values(), key=lambda x: x["period"], reverse=True)


def get_service_products(service_id):
    service = get_service_by_id(service_id)
    if not service:
        raise NotFoundError("Dịch vụ không tồn tại!")
    return ServiceProduct.query.filter(ServiceProduct.service_id == service_id).all()


def get_service_product_by_id(sp_id):
    return ServiceProduct.query.get(sp_id)


def add_service_product(service_id, product_id, default_quantity):
    service = Service.query.filter_by(id=service_id, active=True).first()
    if not service:
        raise NotFoundError("Dịch vụ không tồn tại hoặc đã ngừng hoạt động!")

    product = Product.query.filter_by(id=product_id, active=True).first()
    if not product:
        raise NotFoundError("Sản phẩm không tồn tại hoặc đã ngừng hoạt động!")

    try:
        default_quantity = float(default_quantity)
        if default_quantity <= 0:
            raise ValidationError("Định mức gợi ý phải lớn hơn 0!")
    except (ValueError, TypeError):
        raise ValidationError("Định mức gợi ý phải là số hợp lệ!")

    existing = ServiceProduct.query.filter_by(service_id=service_id, product_id=product_id).first()
    if existing:
        raise DuplicateError("Sản phẩm này đã được cấu hình cho dịch vụ này rồi!")

    sp = ServiceProduct(
        service_id=service_id,
        product_id=product_id,
        default_quantity=default_quantity
    )
    db.session.add(sp)
    try:
        db.session.commit()
        return sp
    except IntegrityError:
        db.session.rollback()
        raise DuplicateError("Sản phẩm này đã được cấu hình cho dịch vụ này rồi!")


def update_service_product(sp_id, default_quantity):
    sp = get_service_product_by_id(sp_id)
    if not sp:
        raise NotFoundError("Không tìm thấy định mức sản phẩm!")

    try:
        default_quantity = float(default_quantity)
        if default_quantity <= 0:
            raise ValidationError("Định mức gợi ý phải lớn hơn 0!")
    except (ValueError, TypeError):
        raise ValidationError("Định mức gợi ý phải là số hợp lệ!")

    sp.default_quantity = default_quantity
    try:
        db.session.commit()
        return sp
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể cập nhật định mức sản phẩm!")


def delete_service_product(sp_id):
    sp = get_service_product_by_id(sp_id)
    if not sp:
        raise NotFoundError("Không tìm thấy định mức sản phẩm!")

    db.session.delete(sp)
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể xóa định mức sản phẩm!")


def get_promotion_by_id(promo_id):
    return Promotion.query.get(promo_id)


def get_all_promotions():
    return Promotion.query.order_by(Promotion.start_date.desc()).all()


def get_active_promotions():
    now = datetime.now()
    return Promotion.query.filter(
        Promotion.active.__eq__(True),
        Promotion.start_date <= now,
        Promotion.end_date >= now
    ).all()


def _validate_promotion_input(promo_code, promo_type, value, start_date, end_date, is_update=False, promo_id=None):
    if not promo_code or not promo_code.strip():
        raise ValidationError("Mã khuyến mãi không được để trống!")
    promo_code = promo_code.strip()

    try:
        promo_type_enum = PromotionType[promo_type.upper()] if isinstance(promo_type, str) else promo_type
    except KeyError:
        raise ValidationError("Loại khuyến mãi không hợp lệ! Chỉ chấp nhận: PERCENT hoặc FIXED")

    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValidationError("Giá trị khuyến mãi phải là số hợp lệ!")

    if promo_type_enum == PromotionType.PERCENT:
        if not (0 < value <= 100):
            raise ValidationError("Khuyến mãi theo % phải lớn hơn 0 và không vượt quá 100!")
    else:
        if value <= 0:
            raise ValidationError("Khuyến mãi theo số tiền cố định phải lớn hơn 0!")

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if isinstance(start_date, str) else start_date
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if isinstance(end_date, str) else end_date
    except ValueError:
        raise ValidationError("Định dạng ngày không hợp lệ! Dùng YYYY-MM-DD")

    if not start_dt or not end_dt:
        raise ValidationError("Vui lòng cung cấp đầy đủ ngày bắt đầu và ngày kết thúc!")
    if start_dt >= end_dt:
        raise ValidationError("Ngày bắt đầu phải trước ngày kết thúc!")

    query = Promotion.query.filter(Promotion.promo_code == promo_code)
    if is_update and promo_id:
        query = query.filter(Promotion.id != promo_id)
    if query.first():
        raise DuplicateError(f"Mã khuyến mãi '{promo_code}' đã tồn tại!")

    return promo_code, promo_type_enum, value, start_dt, end_dt


def add_promotion(promo_code, promo_type, value, start_date, end_date):
    promo_code, promo_type_enum, value, start_dt, end_dt = _validate_promotion_input(
        promo_code, promo_type, value, start_date, end_date
    )

    promo = Promotion(
        promo_code=promo_code,
        promo_type=promo_type_enum,
        value=value,
        start_date=start_dt,
        end_date=end_dt
    )
    db.session.add(promo)
    try:
        db.session.commit()
        return promo
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể thêm khuyến mãi!")


def update_promotion(promo_id, promo_code, promo_type, value, start_date, end_date):
    promo = get_promotion_by_id(promo_id)
    if not promo:
        raise NotFoundError("Không tìm thấy khuyến mãi!")

    promo_code, promo_type_enum, value, start_dt, end_dt = _validate_promotion_input(
        promo_code, promo_type, value, start_date, end_date, is_update=True, promo_id=promo_id
    )

    promo.promo_code = promo_code
    promo.promo_type = promo_type_enum
    promo.value = value
    promo.start_date = start_dt
    promo.end_date = end_dt

    try:
        db.session.commit()
        return promo
    except IntegrityError:
        db.session.rollback()
        raise Exception("Lỗi hệ thống: Không thể cập nhật khuyến mãi!")


def delete_promotion(promo_id):
    promo = get_promotion_by_id(promo_id)
    if not promo:
        raise NotFoundError("Không tìm thấy khuyến mãi!")

    used_in_invoice = Invoice.query.filter_by(promotion_id=promo_id).first()

    try:
        if used_in_invoice:
            promo.active = False
        else:
            db.session.delete(promo)

        db.session.commit()
        return True
    except Exception as ex:
        db.session.rollback()
        app.logger.exception("LỖI XÓA PROMOTION: %s", ex)
        raise Exception("Không thể thực hiện xóa khuyến mãi này!")