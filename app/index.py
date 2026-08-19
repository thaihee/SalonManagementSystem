import math
from datetime import datetime, date, timedelta
from functools import wraps

from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user

from app import app, dao, login, db, admin
from app.exceptions import ValidationError, DuplicateError, NotFoundError
from app.models import User, UserRole, Service, InvoiceItemType, InvoiceStatus
from app.decorators import role_required




# ==========================0. FLASK-LOGIN USER LOADER + PHÂN QUYỀN==========================

@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


# ==========================1. TRANG CHỦ SALON (INDEX - HIỂN THỊ DANH SÁCH DỊCH VỤ & KHUYẾN MÃI)==========================

@app.route('/')
def index():
    kw = request.args.get('kw')
    page = request.args.get('page', 1, type=int)

    # 1. Lấy page_size từ config
    page_size = app.config.get('PAGE_SIZE', 4)

    # 2. Lấy danh sách dịch vụ
    services = dao.load_services(kw=kw, page=page, page_size=page_size)
    total_services = dao.count_services(kw=kw)
    total_pages = math.ceil(total_services / page_size) if total_services > 0 else 1

    # 3. LẤY DANH SÁCH KHUYẾN MÃI ACTIVE & SẮP XẾP MỚI NHẤT TRƯỚC
    all_promos = dao.get_active_promotions() if hasattr(dao, 'get_active_promotions') else []

    # Sắp xếp các mã khuyến mãi theo ngày bắt đầu giảm dần (mã mới nhất lên đầu)
    all_promos = sorted(all_promos, key=lambda p: p.start_date, reverse=True)

    return render_template(
        "customer/index.html",
        services=services,
        promotions=all_promos,  # Pass mảng đã sắp xếp
        total_pages=total_pages,
        page=page,
        kw=kw
    ), 200


# TRANG ĐẶT LỊCH HẸN (BOOKING)
@app.route('/booking', methods=['GET'])
@login_required
def booking_view():
    # Cho phép chọn sẵn dịch vụ nếu người dùng bấm "Đặt lịch" từ 1 service card cụ thể
    service_id = request.args.get('service_id', type=int)

    services = dao.get_all_services() # Lấy toàn bộ dịch vụ để hiện trong form chọn
    staff_list = dao.get_users(role=UserRole.STAFF)
    today_str = date.today().strftime('%Y-%m-%d')

    return render_template(
        'customer/booking.html',
        services=services,
        staff=staff_list,
        selected_service_id=service_id,
        min_date=today_str
    ), 200


# ==========================2. XÁC THỰC: ĐĂNG NHẬP (LOGIN)==========================

@app.route('/login', methods=['GET'])
def login_view():
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('auth/login.html'), 200


@app.route('/login', methods=['POST'])
def login_process():
    username = request.form.get('username')
    password = request.form.get('password')

    # Ưu tiên lấy 'next' từ URL Query String, nếu không có thì lấy từ Form Hidden Field
    next_page = request.args.get('next') or request.form.get('next')

    try:
        user = dao.auth_user(username=username, password=password)
        login_user(user=user)

        # 1. Nếu có 'next' (ví dụ user truy cập đường dẫn bảo mật trước đó), ưu tiên quay lại đó
        if next_page:
            return redirect(next_page), 302

        # 2. Nếu không có 'next', điều hướng theo vai trò (Role)
        if user.role == UserRole.ADMIN:
            return redirect('/admin'), 302
        elif user.role == UserRole.RECEPTIONIST:
            return redirect('/reception/appointments'), 302
        elif user.role == UserRole.STAFF:
            return redirect('/staff/appointments'), 302

        # Khách hàng (CUSTOMER) về trang chủ
        return redirect('/'), 302

    except ValidationError as val:
        return render_template('auth/login.html', err_msg=str(val)), 401
    except Exception as ex:
        app.logger.exception(ex)
        return render_template('auth/login.html', err_msg="Có lỗi hệ thống xảy ra!"), 500


# ==========================3. XÁC THỰC: ĐĂNG XUẤT (LOGOUT)==========================

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout_process():
    logout_user()
    return redirect('/login'), 302


# ==========================4. XÁC THỰC: ĐĂNG KÝ TÀI KHOẢN KHÁCH HÀNG (REGISTER)==========================

@app.route('/register', methods=['GET'])
def register_view():
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('auth/register.html'), 200


@app.route('/register', methods=['POST'])
def register_process():
    data = request.form
    password = data.get("password")
    confirm = data.get("confirm")
    avatar = data.get("avatar")

    if password != confirm:
        return render_template('auth/register.html', err_msg="Mật khẩu xác nhận không khớp!"), 400

    try:
        dao.add_user(
            full_name=data.get('full_name'),
            username=data.get('username'),
            password=password,
            phone=data.get('phone'),
            email=data.get('email'),
            role=UserRole.CUSTOMER,
            avatar=avatar
        )
        flash("Đăng ký tài khoản thành công! Vui lòng đăng nhập.", "success")
        return redirect('/login'), 302

    except ValidationError as ex:
        # HTTP 400 Bad Request: dữ liệu sai định dạng
        return render_template('auth/register.html', err_msg=str(ex)), 400
    except DuplicateError as ex:
        # HTTP 409 Conflict: username/email đã tồn tại
        return render_template('auth/register.html', err_msg=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return render_template('auth/register.html', err_msg="Lỗi hệ thống khi đăng ký!"), 500


# ==========================5. HỒ SƠ CÁ NHÂN==========================

@app.route('/users/me', methods=['GET'])
@login_required
def users_me_view():
    return render_template('auth/profile.html', user=current_user), 200


@app.route('/users/me', methods=['PUT'])
@login_required
def users_me_update():
    # FIX: PUT không thể được gọi từ HTML form thuần (form chỉ hỗ trợ GET/POST),
    # nên route này chỉ được gọi qua JS fetch() => phải trả JSON, không phải HTML.
    data = request.get_json(silent=True) or request.form
    avatar = data.get("avatar")

    try:
        dao.update_user_profile(
            user_id=current_user.id,
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            email=data.get('email'),
            avatar=avatar
        )
        return jsonify({"message": "Cập nhật thông tin cá nhân thành công!"}), 200

    except NotFoundError as ex:
        return jsonify({"error": str(ex)}), 404
    except ValidationError as ex:
        return jsonify({"error": str(ex)}), 400
    except DuplicateError as ex:
        return jsonify({"error": str(ex)}), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Không thể cập nhật hồ sơ!"}), 500


# ==========================6. LỊCH HẸN==========================

# GET /appointments/available-slots?staff_id=1&service_id=2&date=2026-08-16&appointment_id=5
@app.route('/appointments/available-slots', methods=['GET'])
def get_available_slots_route():
    service_id = request.args.get('service_id')
    date_str = request.args.get('date')
    staff_id = request.args.get('staff_id')
    appointment_id = request.args.get('appointment_id') # <--- THÊM DÒNG NÀY

    if not service_id or not date_str:
        return jsonify({"error": "Thiếu service_id hoặc date!"}), 400

    try:
        slots = dao.get_available_slots(
            service_id=int(service_id),
            date_str=date_str,
            staff_id=int(staff_id) if staff_id else None,
            exclude_appointment_id=int(appointment_id) if appointment_id else None # <--- THÊM TRUYỀN PARAM NÀY
        )
        return jsonify({"date": date_str, "available_slots": slots}), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Lỗi hệ thống!"}), 500

# POST /appointments - API Tạo lịch hẹn mới
@app.route('/appointments', methods=['POST'])
@login_required
def create_appointment_route():
    # Nhận dữ liệu từ JSON body hoặc Form-data
    data = request.get_json(silent=True) or request.form

    service_id = data.get('service_id')
    staff_id = data.get('staff_id')
    date_str = data.get('date')      # Định dạng: YYYY-MM-DD
    time_str = data.get('time')      # Định dạng: HH:MM
    note = data.get('note', '')

    # FIX (IDOR): Customer CHỈ được đặt lịch cho chính mình, không được truyền
    # customer_id để đặt hộ người khác. Chỉ Staff/Admin (đặt tại quầy) mới
    # được chỉ định customer_id khác chính họ.
    if current_user.role == UserRole.CUSTOMER:
        customer_id = current_user.id
    else:
        customer_id = data.get('customer_id', current_user.id)

    if not all([service_id, date_str, time_str]):
        return jsonify({"error": "Vui lòng cung cấp đầy đủ: dịch vụ, ngày và giờ hẹn!"}), 400

    try:
        appointment = dao.create_appointment(
            customer_id=int(customer_id),
            service_id=int(service_id),
            staff_id=int(staff_id) if staff_id else None,
            date_str=str(date_str),
            time_str=str(time_str),
            note=note
        )

        return jsonify({
            "message": "Đặt lịch hẹn thành công!",
            "appointment": {
                "id": appointment.id,
                "customer_id": appointment.customer_id,
                "staff_id": appointment.staff_id,
                "service_id": appointment.service_id,
                "appointment_date": appointment.appointment_date.strftime("%Y-%m-%d %H:%M"),
                "status": appointment.status.name if hasattr(appointment.status, 'name') else str(appointment.status)
            }
        }), 201

    except ValidationError as ex:
        # HTTP 400 Bad Request: Lỗi dữ liệu / Giờ trùng / Sai định dạng
        return jsonify({"error": str(ex)}), 400

    except NotFoundError as ex:
        # HTTP 404 Not Found: Khách hàng / Nhân viên / Dịch vụ không tồn tại
        return jsonify({"error": str(ex)}), 404

    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Lỗi hệ thống khi tạo lịch hẹn!"}), 500

# PUT /appointments/<id> - Sửa lịch hẹn
@app.route('/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
def update_appointment_route(appointment_id):
    data = request.get_json(silent=True) or request.form

    # FIX (IDOR): lấy lịch hẹn ra trước để check quyền sở hữu
    appt = dao.get_appointment_by_id(appointment_id)
    if not appt or not appt.active:
        return jsonify({"error": "Lịch hẹn không tồn tại!"}), 404

    if current_user.role == UserRole.CUSTOMER and appt.customer_id != current_user.id:
        return jsonify({"error": "Bạn không có quyền sửa lịch hẹn này!"}), 403
    if current_user.role == UserRole.STAFF and appt.staff_id != current_user.id:
        return jsonify({"error": "Bạn không có quyền sửa lịch hẹn này!"}), 403

    # FIX: chỉ Staff/Admin được phép đổi trạng thái lịch hẹn, Customer không được tự đổi
    status = data.get('status')
    if status and current_user.role == UserRole.CUSTOMER:
        return jsonify({"error": "Bạn không có quyền thay đổi trạng thái lịch hẹn!"}), 403

    try:
        appt = dao.update_appointment(
            appointment_id=appointment_id,
            service_id=int(data.get('service_id')) if data.get('service_id') else None,
            staff_id=int(data.get('staff_id')) if data.get('staff_id') else None,
            date_str=data.get('date'),
            time_str=data.get('time'),
            note=data.get('note'),
            status=status
        )

        return jsonify({
            "message": "Cập nhật lịch hẹn thành công!",
            "appointment": {
                "id": appt.id,
                "appointment_date": appt.appointment_date.strftime("%Y-%m-%d %H:%M"),
                "status": appt.status.name,
                "note": appt.note
            }
        }), 200

    except ValidationError as ex:
        return jsonify({"error": str(ex)}), 400
    except NotFoundError as ex:
        return jsonify({"error": str(ex)}), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Lỗi hệ thống khi cập nhật lịch hẹn!"}), 500


# PATCH /appointments/<id>/cancel - Hủy lịch hẹn
@app.route('/appointments/<int:appointment_id>/cancel', methods=['PATCH', 'POST'])
@login_required
def cancel_appointment_route(appointment_id):
    # FIX (IDOR): lấy lịch hẹn ra trước để check quyền sở hữu
    appt = dao.get_appointment_by_id(appointment_id)
    if not appt or not appt.active:
        return jsonify({"error": "Lịch hẹn không tồn tại!"}), 404

    if current_user.role == UserRole.CUSTOMER and appt.customer_id != current_user.id:
        return jsonify({"error": "Bạn không có quyền hủy lịch hẹn này!"}), 403
    if current_user.role == UserRole.STAFF and appt.staff_id != current_user.id:
        return jsonify({"error": "Bạn không có quyền hủy lịch hẹn này!"}), 403

    try:
        appt = dao.cancel_appointment(appointment_id)

        return jsonify({
            "message": "Hủy lịch hẹn thành công!",
            "appointment_id": appt.id,
            "status": appt.status.name
        }), 200

    except ValidationError as ex:
        return jsonify({"error": str(ex)}), 400
    except NotFoundError as ex:
        return jsonify({"error": str(ex)}), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Lỗi hệ thống khi hủy lịch hẹn!"}), 500


# ==========================7. QUẢN LÝ HÓA ĐƠN & THANH TOÁN (INVOICES API)==========================

# 7.1 POST /invoices - Tạo hóa đơn
@app.route('/invoices', methods=['POST'])
@login_required
@role_required(UserRole.STAFF, UserRole.ADMIN)
def create_invoice_route():
    data = request.get_json(silent=True) or request.form

    customer_id = data.get('customer_id')
    appointment_id = data.get('appointment_id')
    details = data.get('details', [])   # gồm cả dòng SERVICE và PRODUCT_USED

    staff_id = current_user.id

    if not customer_id or not details:
        return jsonify({"error": "Vui lòng cung cấp customer_id và danh sách chi tiết (details)!"}), 400

    try:
        invoice = dao.create_invoice(   # giờ chỉ tạo DRAFT
            customer_id=int(customer_id),
            staff_id=int(staff_id),
            details_data=details,
            appointment_id=int(appointment_id) if appointment_id else None
        )
        return jsonify({
            "message": "Tạo hóa đơn nháp thành công! Chờ Lễ tân xác nhận thanh toán.",
            "invoice": {"id": invoice.id, "status": invoice.status.name}
        }), 201
    except ValidationError as ex:
        return jsonify({"error": str(ex)}), 400
    except NotFoundError as ex:
        return jsonify({"error": str(ex)}), 404
    except DuplicateError as ex:
        return jsonify({"error": str(ex)}), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Lỗi hệ thống khi lập hóa đơn!"}), 500


# 7.2 GET /invoices/<id> - Xem chi tiết 1 hóa đơn (Biên nhận thanh toán)
@app.route('/invoices/<int:invoice_id>', methods=['GET'])
@login_required
def get_invoice_detail_route(invoice_id):
    invoice = dao.get_invoice_by_id(invoice_id)
    if not invoice:
        abort(404)

    # Ràng buộc bảo mật IDOR
    if current_user.role == UserRole.CUSTOMER and invoice.customer_id != current_user.id:
        abort(403)

    return render_template('receptionist/invoice_detail.html', invoice=invoice), 200


# Khách hàng xem lịch sử hóa đơn của mình (Có Lọc & Phân trang)
@app.route('/invoices/me', methods=['GET'])
@login_required
def my_invoices_view():
    kw = request.args.get('kw', '').strip()
    status_str = request.args.get('status', 'ALL')
    date_str = request.args.get('date', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    # 1. Lấy toàn bộ hóa đơn của khách hàng hiện tại
    all_invoices, _ = dao.get_invoices(customer_id=current_user.id, page=None)

    # 3. Lọc theo trạng thái (DRAFT / PAID / CANCELLED)
    if status_str and status_str != 'ALL':
        all_invoices = [inv for inv in all_invoices if inv.status.name == status_str]

    # 4. Lọc theo ngày tháng (YYYY-MM-DD)
    if date_str:
        all_invoices = [
            inv for inv in all_invoices
            if inv.invoice_date.strftime('%Y-%m-%d') == date_str
        ]

    # 5. Phân trang
    total_items = len(all_invoices)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size
    invoices_paged = all_invoices[start:end]

    return render_template(
        'customer/my_invoices.html',
        invoices=invoices_paged,
        kw=kw,
        selected_status=status_str,
        selected_date=date_str,
        page=page,
        total_pages=total_pages
    ), 200


# Giao diện lập hóa đơn nháp (Nhân viên)
@app.route('/staff/create-invoice', methods=['GET'])
@login_required
@role_required(UserRole.STAFF, UserRole.ADMIN)
def create_invoice_view():
    appointment_id = request.args.get('appointment_id', type=int)
    customer_id = request.args.get('customer_id', type=int)
    service_id = request.args.get('service_id', type=int)

    selected_customer = None
    if customer_id:
        selected_customer = dao.get_user_by_id(customer_id)

    services = dao.get_all_services()

    # Lấy toàn bộ ServiceProduct để tạo bản đồ Định Mức Sản Phẩm theo Dịch Vụ
    # Cấu trúc: { service_id: [ { product_id, product_name, unit_name, default_quantity, stock_quantity }, ... ] }
    service_products_map = {}
    for svc in services:
        s_prods = dao.get_service_products(svc.id)
        service_products_map[svc.id] = [
            {
                'product_id': sp.product.id,
                'product_name': sp.product.product_name,
                'unit_name': sp.product.unit.name,
                'default_quantity': sp.default_quantity,
                'stock_quantity': sp.product.stock_quantity
            }
            for sp in s_prods if sp.product and sp.product.active
        ]

    return render_template(
        'staff/create_invoice.html',
        services=services,
        selected_customer=selected_customer,
        selected_appointment_id=appointment_id,
        selected_service_id=service_id,
        service_products_map=service_products_map
    ), 200


# Giao diện danh sách hóa đơn do Nhân viên lập
@app.route('/staff/invoices', methods=['GET'])
@login_required
@role_required(UserRole.STAFF, UserRole.ADMIN)
def staff_invoices_view():
    status_str = request.args.get('status', 'ALL')
    date_str = request.args.get('date')
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    from_date = None
    to_date = None

    if date_str:
        try:
            selected_dt = datetime.strptime(date_str, '%Y-%m-%d')
            from_date = datetime.combine(selected_dt, datetime.min.time())
            to_date = datetime.combine(selected_dt, datetime.max.time())
        except ValueError:
            pass

    staff_id_filter = current_user.id if current_user.role == UserRole.STAFF else None

    # Lấy danh sách hóa đơn theo trạng thái và trang
    status_filter = None if status_str == 'ALL' else status_str

    invoices, total_items = dao.get_invoices(
        staff_id=staff_id_filter,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size
    )

    # Lấy tổng số hóa đơn để hiển thị trên 3 thẻ thống kê trên cùng
    all_invoices, _ = dao.get_invoices(
        staff_id=staff_id_filter,
        from_date=from_date,
        to_date=to_date,
        page=None
    )

    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    return render_template(
        'staff/draft_invoice_list.html',
        invoices=invoices,
        all_invoices=all_invoices,
        selected_status=status_str,
        selected_date=date_str,
        page=page,
        total_pages=total_pages
    ), 200


# Lễ tân quản lý toàn bộ danh sách hóa đơn (Xem nháp, Xem đã thanh toán)
@app.route('/reception/invoices', methods=['GET'])
@login_required
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def reception_invoices_view():
    date_str = request.args.get('date')
    status_str = request.args.get('status', 'ALL')
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10) # 10 hóa đơn / trang

    from_date = None
    to_date = None

    if date_str:
        try:
            selected_dt = datetime.strptime(date_str, '%Y-%m-%d')
            from_date = datetime.combine(selected_dt, datetime.min.time())
            to_date = datetime.combine(selected_dt, datetime.max.time())
        except ValueError:
            pass

    # 1. Lấy toàn bộ danh sách hóa đơn không phân trang để tính tổng cho 3 thẻ Thống kê
    all_invoices, _ = dao.get_invoices(
        status=None,
        from_date=from_date,
        to_date=to_date,
        page=None
    )

    # 2. Lọc theo trạng thái status nếu chọn Tab
    if status_str != 'ALL':
        filtered_invoices = [inv for inv in all_invoices if inv.status.name == status_str]
    else:
        filtered_invoices = all_invoices

    # 3. Tính toán phân trang bằng Python trên danh sách đã lọc
    total_items = len(filtered_invoices)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    # Cắt danh sách hóa đơn cho trang hiện tại
    start = (page - 1) * page_size
    end = start + page_size
    invoices_paged = filtered_invoices[start:end]

    staff_list = dao.get_users(role=UserRole.STAFF)

    return render_template(
        'receptionist/recept_invoice_list.html',
        invoices=invoices_paged,          # Danh sách 10 mục của trang hiện tại
        all_invoices=all_invoices,        # Dùng để tính tổng 3 thẻ thống kê
        staff_list=staff_list,
        selected_date=date_str,
        selected_status=status_str,
        page=page,
        total_pages=total_pages
    ), 200


# Lễ tân xem và tra cứu toàn bộ lịch hẹn của Salon (Đã hỗ trợ phân trang)
@app.route('/reception/appointments', methods=['GET'])
@login_required
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def reception_appointments_view():
    date_str = request.args.get('date')
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)  # 10 lịch hẹn / trang

    selected_date = None
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            pass

    # 1. Lấy toàn bộ danh sách lịch hẹn theo ngày
    all_appointments = dao.get_appointments(
        date=selected_date,
        page=None
    )

    # 2. Tính toán phân trang
    total_items = len(all_appointments)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    # 3. Cắt danh sách cho trang hiện tại
    start = (page - 1) * page_size
    end = start + page_size
    appointments_paged = all_appointments[start:end]

    staff_list = dao.get_users(role=UserRole.STAFF)

    return render_template(
        'receptionist/appointment_list.html',
        appointments=appointments_paged,
        staff_list=staff_list,
        selected_date=date_str,
        page=page,
        total_pages=total_pages
    ), 200

# PATCH /invoices/<id>/confirm-payment - Lễ tân xác nhận thanh toán (DRAFT -> PAID)
@app.route('/invoices/<int:invoice_id>/confirm-payment', methods=['PATCH'])
@login_required
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def confirm_invoice_payment_route(invoice_id):
    data = request.get_json(silent=True) or request.form
    payment_method = data.get('payment_method')
    promotion_id = data.get('promotion_id')  # optional

    if not payment_method:
        return jsonify({"error": "Vui lòng chọn hình thức thanh toán!"}), 400

    try:
        invoice = dao.confirm_invoice_payment(
            invoice_id=invoice_id,
            receptionist_id=current_user.id,
            payment_method=payment_method,
            promotion_id=int(promotion_id) if promotion_id else None
        )
        return jsonify({
            "message": "Xác nhận thanh toán thành công!",
            "invoice": {
                "id": invoice.id,
                "status": invoice.status.name,
                "total_amount": invoice.total_amount,
                "payment_method": invoice.payment_method.name
            }
        }), 200
    except ValidationError as ex:
        return jsonify({"error": str(ex)}), 400
    except NotFoundError as ex:
        return jsonify({"error": str(ex)}), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Lỗi hệ thống khi xác nhận thanh toán!"}), 500


@app.route('/reception/invoice/<int:invoice_id>/checkout', methods=['GET'])
@login_required
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def invoice_checkout_view(invoice_id):
    invoice = dao.get_invoice_by_id(invoice_id)
    if not invoice or invoice.status != InvoiceStatus.DRAFT:
        flash("Hóa đơn không hợp lệ hoặc đã thanh toán!", "error")
        # Đã cập nhật sang đường dẫn quản lý hóa đơn mới
        return redirect('/reception/invoices')

    # Lấy danh sách khuyến mãi còn hạn truyền thẳng vào Template Jinja2
    active_promos = dao.get_active_promotions()

    return render_template(
        'receptionist/invoice_checkout.html',
        invoice=invoice,
        promotions=active_promos
    ), 200


# =========================================================================
# 8. ĐỔI MẬT KHẨU
# =========================================================================
@app.route('/users/change-password', methods=['POST'])
@login_required
def change_password_route():
    # Sửa từ request.form thành request.get_json(silent=True) or request.form để nhận diện đúng JSON từ fetch
    data = request.get_json(silent=True) or request.form
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if new_password != confirm_password:
        return jsonify(success=False, error="Mật khẩu mới xác nhận không khớp!"), 400

    try:
        dao.change_password(
            user_id=current_user.id,
            old_password=old_password,
            new_password=new_password
        )
        return jsonify(success=True, message="Đổi mật khẩu thành công!"), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi đổi mật khẩu!"), 500


# =========================================================================
# 9. LỊCH HẸN CỦA TÔI (KHÁCH HÀNG) / LỊCH HẸN ĐƯỢC GIAO (NHÂN VIÊN)
# =========================================================================

# Lịch hẹn cá nhân của Khách hàng (Có Lọc & Phân trang)
@app.route('/appointments/me', methods=['GET'])
@login_required
def my_appointments_view():
    kw = request.args.get('kw', '').strip()
    status_str = request.args.get('status', 'ALL')
    date_str = request.args.get('date', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    # 1. Lấy tất cả lịch hẹn của khách hàng này
    all_appts = dao.get_appointments_by_customer(current_user.id)

    # 2. Lọc theo từ khóa (Tên dịch vụ)
    if kw:
        kw_lower = kw.lower()
        all_appts = [
            a for a in all_appts
            if a.service and kw_lower in a.service.service_name.lower()
        ]

    # 3. Lọc theo trạng thái (CONFIRMED / COMPLETED / CANCELLED)
    if status_str and status_str != 'ALL':
        all_appts = [a for a in all_appts if a.status.name == status_str]

    # 4. Lọc theo ngày tháng (YYYY-MM-DD)
    if date_str:
        all_appts = [
            a for a in all_appts
            if a.appointment_date.strftime('%Y-%m-%d') == date_str
        ]

    # 5. Phân trang
    total_items = len(all_appts)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size
    appts_paged = all_appts[start:end]

    services = dao.get_all_services()
    staff_list = dao.get_users(role=UserRole.STAFF)

    return render_template(
        'customer/my_appointments.html',
        appointments=appts_paged,
        services=services,
        staff=staff_list,
        kw=kw,
        selected_status=status_str,
        selected_date=date_str,
        page=page,
        total_pages=total_pages,
        datetime=datetime,  # Bổ sung truyền sang Jinja2
        timedelta=timedelta
    ), 200


# Nhân viên xem danh sách lịch hẹn được giao
@app.route('/staff/appointments', methods=['GET'])
@login_required
@role_required(UserRole.STAFF, UserRole.ADMIN)
def staff_appointments_view():
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    staff_id = current_user.id if current_user.role == UserRole.STAFF else request.args.get('staff_id', type=int)

    if staff_id:
        appointments, total_items = dao.get_appointments_by_staff(
            staff_id=staff_id,
            date_str=date_str,
            page=page,
            page_size=page_size
        )
    else:
        appointments, total_items = [], 0

    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    return render_template(
        'staff/staff_appointments.html',
        appointments=appointments,
        selected_date=date_str,
        page=page,
        total_pages=total_pages
    ), 200


# API trả về danh sách dữ liệu JSON cho JS fetch
@app.route('/api/staff/appointments', methods=['GET'])
@login_required
@role_required(UserRole.STAFF, UserRole.ADMIN)
def staff_appointments_api():
    date_str = request.args.get('date')
    staff_id = request.args.get('staff_id', type=int)

    # Staff chỉ xem được lịch của chính mình; Admin phải chỉ định staff_id cần xem
    if current_user.role == UserRole.STAFF:
        staff_id = current_user.id
    elif not staff_id:
        return jsonify({"error": "Admin cần truyền staff_id để xem lịch của nhân viên cụ thể!"}), 400

    try:
        appointments, _ = dao.get_appointments_by_staff(staff_id, date_str=date_str)
        return jsonify({
            "appointments": [
                {
                    "id": a.id,
                    "customer_name": a.customer.full_name if a.customer else None,
                    "service_name": a.service.service_name if a.service else None,
                    "appointment_date": a.appointment_date.strftime("%Y-%m-%d %H:%M"),
                    "status": a.status.name,
                    "note": a.note
                } for a in appointments
            ]
        }), 200
    except ValidationError as ex:
        return jsonify({"error": str(ex)}), 400


# =========================================================================
# 10. TRA CỨU KHÁCH HÀNG (NHÂN VIÊN / QUẢN LÝ)
# =========================================================================
@app.route('/customers/search', methods=['GET'])
@login_required
@role_required(UserRole.STAFF, UserRole.ADMIN)
def search_customers_route():
    """Nhân viên tra cứu khách hàng theo tên hoặc SĐT khi lập hóa đơn.
    Không dùng chung /users (route đó chỉ dành cho Admin quản lý toàn bộ user,
    bao gồm cả Staff/Admin khác - lộ thông tin không cần thiết cho Nhân viên)."""
    kw = request.args.get('kw', '').strip()

    customers = dao.get_users(role=UserRole.CUSTOMER)

    if kw:
        kw_lower = kw.lower()
        customers = [
            c for c in customers
            if kw_lower in c.full_name.lower() or kw_lower in c.phone
        ]

    return jsonify({
        "customers": [
            {
                "id": c.id,
                "full_name": c.full_name,
                "phone": c.phone,
                "email": c.email
            } for c in customers if c.active
        ]
    }), 200



# =========================================================================
# XỬ LÝ LỖI TRANG (ERROR HANDLERS)
# =========================================================================

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error/404.html'), 404


# =========================================================================
# CHẠY ỨNG DỤNG
# =========================================================================
if __name__ == "__main__":
    app.run(debug=True)