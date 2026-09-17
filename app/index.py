import math
from datetime import datetime, date, timedelta
from functools import wraps

from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user

from app import app, dao, login, db, admin
from app.exceptions import ValidationError, DuplicateError, NotFoundError
from app.models import User, UserRole, Service, InvoiceItemType, InvoiceStatus
from app.decorators import role_required



@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


@app.route('/')
def index():
    kw = request.args.get('kw')

    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 4)

    if page < 1:
        page = 1

    services = dao.load_services(
        kw=kw,
        page=page,
        page_size=page_size
    )

    total_services = dao.count_services(kw=kw)
    total_pages = (
        math.ceil(total_services / page_size)
        if total_services > 0
        else 1
    )

    if page > total_pages:
        page = total_pages

        services = dao.load_services(
            kw=kw,
            page=page,
            page_size=page_size
        )

    promo_page = request.args.get('promo_page', 1, type=int)

    promo_page_size = 6

    all_promos = (
        dao.get_active_promotions()
        if hasattr(dao, 'get_active_promotions')
        else []
    )

    all_promos = sorted(
        all_promos,
        key=lambda p: p.start_date,
        reverse=True
    )

    promo_total_items = len(all_promos)

    promo_total_pages = (
        math.ceil(promo_total_items / promo_page_size)
        if promo_total_items > 0
        else 1
    )

    # Chặn promo_page không hợp lệ
    if promo_page < 1:
        promo_page = 1

    if promo_page > promo_total_pages:
        promo_page = promo_total_pages

    promo_start = (promo_page - 1) * promo_page_size
    promo_end = promo_start + promo_page_size

    promotions_paged = all_promos[promo_start:promo_end]

    return render_template(
        "customer/index.html",

        services=services,
        total_pages=total_pages,
        page=page,
        kw=kw,

        promotions=promotions_paged,
        promo_page=promo_page,
        promo_total_pages=promo_total_pages

    ), 200

@app.route('/booking', methods=['GET'])
@login_required
def booking_view():
    service_id = request.args.get('service_id', type=int)

    services = dao.get_all_services()
    staff_list = dao.get_users(role=UserRole.STAFF)
    today_str = date.today().strftime('%Y-%m-%d')

    return render_template(
        'customer/booking.html',
        services=services,
        staff=staff_list,
        selected_service_id=service_id,
        min_date=today_str
    ), 200


@app.route('/login', methods=['GET'])
def login_view():
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('auth/login.html'), 200


@app.route('/login', methods=['POST'])
def login_process():
    username = request.form.get('username')
    password = request.form.get('password')

    next_page = request.args.get('next') or request.form.get('next')

    try:
        user = dao.auth_user(username=username, password=password)
        login_user(user=user)

        if next_page:
            return redirect(next_page), 302

        if user.role == UserRole.ADMIN:
            return redirect('/admin'), 302
        elif user.role == UserRole.RECEPTIONIST:
            return redirect('/reception/appointments'), 302
        elif user.role == UserRole.STAFF:
            return redirect('/staff/appointments'), 302

        return redirect('/'), 302

    except ValidationError as val:
        return render_template('auth/login.html', err_msg=str(val)), 401
    except Exception as ex:
        app.logger.exception(ex)
        return render_template('auth/login.html', err_msg="Có lỗi hệ thống xảy ra!"), 500

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout_process():
    logout_user()
    return redirect('/login'), 302


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
        return render_template('auth/register.html', err_msg=str(ex)), 400
    except DuplicateError as ex:
        return render_template('auth/register.html', err_msg=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return render_template('auth/register.html', err_msg="Lỗi hệ thống khi đăng ký!"), 500


@app.route('/users/me', methods=['GET'])
@login_required
def users_me_view():
    return render_template('auth/profile.html', user=current_user), 200


@app.route('/users/me', methods=['PUT'])
@login_required
def users_me_update():
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


@app.route('/appointments/available-slots', methods=['GET'])
@login_required
def get_available_slots_route():
    service_id = request.args.get('service_id')
    date_str = request.args.get('date')
    staff_id = request.args.get('staff_id')
    appointment_id = request.args.get('appointment_id')

    if not service_id or not date_str:
        return jsonify({"error": "Thiếu service_id hoặc date!"}), 400

    try:
        slots = dao.get_available_slots(
            service_id=int(service_id),
            date_str=date_str,
            staff_id=int(staff_id) if staff_id else None,
            exclude_appointment_id=int(appointment_id) if appointment_id else None
        )
        return jsonify({"date": date_str, "available_slots": slots}), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Lỗi hệ thống!"}), 500


@app.route('/appointments', methods=['POST'])
@login_required
def create_appointment_route():
    data = request.get_json(silent=True) or request.form

    service_id = data.get('service_id')
    staff_id = data.get('staff_id')
    date_str = data.get('date')
    time_str = data.get('time')
    note = data.get('note', '')

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
        return jsonify({"error": str(ex)}), 400

    except NotFoundError as ex:
        return jsonify({"error": str(ex)}), 404

    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Lỗi hệ thống khi tạo lịch hẹn!"}), 500


@app.route('/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
def update_appointment_route(appointment_id):
    data = request.get_json(silent=True) or request.form

    appt = dao.get_appointment_by_id(appointment_id)
    if not appt or not appt.active:
        return jsonify({"error": "Lịch hẹn không tồn tại!"}), 404

    if current_user.role == UserRole.CUSTOMER and appt.customer_id != current_user.id:
        return jsonify({"error": "Bạn không có quyền sửa lịch hẹn này!"}), 403
    if current_user.role == UserRole.STAFF and appt.staff_id != current_user.id:
        return jsonify({"error": "Bạn không có quyền sửa lịch hẹn này!"}), 403

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


@app.route('/appointments/<int:appointment_id>/cancel', methods=['PATCH', 'POST'])
@login_required
def cancel_appointment_route(appointment_id):
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


@app.route('/invoices', methods=['POST'])
@role_required(UserRole.STAFF, UserRole.ADMIN)
def create_invoice_route():
    data = request.get_json(silent=True) or request.form

    customer_id = data.get('customer_id')
    appointment_id = data.get('appointment_id')
    details = data.get('details', [])

    staff_id = current_user.id

    if not customer_id or not details:
        return jsonify({"error": "Vui lòng cung cấp customer_id và danh sách chi tiết (details)!"}), 400

    try:
        invoice = dao.create_invoice(
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


@app.route('/invoices/<int:invoice_id>', methods=['GET'])
@login_required
def get_invoice_detail_route(invoice_id):
    invoice = dao.get_invoice_by_id(invoice_id)
    if not invoice:
        abort(404)

    if current_user.role == UserRole.CUSTOMER and invoice.customer_id != current_user.id:
        abort(403)

    return render_template('receptionist/invoice_detail.html', invoice=invoice), 200


@app.route('/invoices/me', methods=['GET'])
@login_required
def my_invoices_view():
    kw = request.args.get('kw', '').strip()
    status_str = request.args.get('status', 'ALL')
    date_str = request.args.get('date', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    all_invoices, _ = dao.get_invoices(customer_id=current_user.id, page=None)

    if status_str and status_str != 'ALL':
        all_invoices = [inv for inv in all_invoices if inv.status.name == status_str]

    if date_str:
        all_invoices = [
            inv for inv in all_invoices
            if inv.invoice_date.strftime('%Y-%m-%d') == date_str
        ]

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


@app.route('/staff/create-invoice', methods=['GET'])
@role_required(UserRole.STAFF, UserRole.ADMIN)
def create_invoice_view():
    appointment_id = request.args.get('appointment_id', type=int)
    customer_id = request.args.get('customer_id', type=int)
    service_id = request.args.get('service_id', type=int)

    selected_customer = None
    if customer_id:
        selected_customer = dao.get_user_by_id(customer_id)

    services = dao.get_all_services()

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


@app.route('/staff/invoices', methods=['GET'])
@role_required(UserRole.STAFF, UserRole.ADMIN)
def staff_invoices_view():
    status_str = request.args.get('status', 'ALL')
    date_str = request.args.get('date', '').strip()
    kw = request.args.get('kw', '').strip()

    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    from_date = None
    to_date = None

    if date_str:
        try:
            selected_dt = datetime.strptime(date_str, '%Y-%m-%d')

            from_date = datetime.combine(
                selected_dt,
                datetime.min.time()
            )

            to_date = datetime.combine(
                selected_dt,
                datetime.max.time()
            )

        except ValueError:
            pass

    staff_id_filter = (
        current_user.id
        if current_user.role == UserRole.STAFF
        else None
    )

    all_invoices, _ = dao.get_invoices(
        staff_id=staff_id_filter,
        from_date=from_date,
        to_date=to_date,
        page=None
    )

    filtered_invoices = all_invoices

    if status_str != 'ALL':
        filtered_invoices = [
            inv for inv in filtered_invoices
            if inv.status.name == status_str
        ]

    if kw:
        kw_lower = kw.lower()

        filtered_invoices = [
            inv for inv in filtered_invoices
            if (
                kw_lower in str(inv.id).lower()

                or (
                    inv.customer
                    and inv.customer.full_name
                    and kw_lower in inv.customer.full_name.lower()
                )

                or (
                    inv.customer
                    and inv.customer.phone
                    and kw_lower in inv.customer.phone.lower()
                )
            )
        ]

    total_items = len(filtered_invoices)

    total_pages = (
        math.ceil(total_items / page_size)
        if total_items > 0
        else 1
    )

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size

    invoices_paged = filtered_invoices[start:end]

    return render_template(
        'staff/draft_invoice_list.html',

        invoices=invoices_paged,

        all_invoices=all_invoices,

        selected_status=status_str,
        selected_date=date_str,
        kw=kw,

        page=page,
        total_pages=total_pages
    ), 200


@app.route('/reception/invoices', methods=['GET'])
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def reception_invoices_view():
    date_str = request.args.get('date', '').strip()
    status_str = request.args.get('status', 'ALL')
    kw = request.args.get('kw', '').strip()
    staff_id = request.args.get('staff_id', type=int)

    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    from_date = None
    to_date = None

    if date_str:
        try:
            selected_dt = datetime.strptime(date_str, '%Y-%m-%d')
            from_date = datetime.combine(
                selected_dt,
                datetime.min.time()
            )
            to_date = datetime.combine(
                selected_dt,
                datetime.max.time()
            )
        except ValueError:
            pass

    all_invoices, _ = dao.get_invoices(
        status=None,
        from_date=from_date,
        to_date=to_date,
        page=None
    )

    filtered_invoices = all_invoices

    if status_str != 'ALL':
        filtered_invoices = [
            inv for inv in filtered_invoices
            if inv.status.name == status_str
        ]

    if staff_id:
        filtered_invoices = [
            inv for inv in filtered_invoices
            if inv.staff_id == staff_id
        ]

    if kw:
        kw_lower = kw.lower()

        filtered_invoices = [
            inv for inv in filtered_invoices
            if (
                kw_lower in str(inv.id).lower()
                or (
                    inv.customer
                    and inv.customer.full_name
                    and kw_lower in inv.customer.full_name.lower()
                )
                or (
                    inv.customer
                    and inv.customer.phone
                    and kw_lower in inv.customer.phone.lower()
                )
                or (
                    inv.staff
                    and inv.staff.full_name
                    and kw_lower in inv.staff.full_name.lower()
                )
            )
        ]

    total_items = len(filtered_invoices)

    total_pages = (
        math.ceil(total_items / page_size)
        if total_items > 0
        else 1
    )

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size

    invoices_paged = filtered_invoices[start:end]

    staff_list = dao.get_users(role=UserRole.STAFF)

    return render_template(
        'receptionist/recept_invoice_list.html',

        invoices=invoices_paged,
        all_invoices=all_invoices,
        staff_list=staff_list,

        selected_date=date_str,
        selected_status=status_str,
        selected_staff_id=staff_id,
        kw=kw,

        page=page,
        total_pages=total_pages
    ), 200


@app.route('/reception/appointments', methods=['GET'])
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def reception_appointments_view():
    date_str = request.args.get('date', '').strip()
    kw = request.args.get('kw', '').strip()
    staff_id = request.args.get('staff_id', type=int)

    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    selected_date = None

    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            selected_date = None

    all_appointments = dao.get_appointments(
        date=selected_date,
        staff_id=staff_id,
        page=None
    )

    if kw:
        kw_lower = kw.lower()

        filtered_appointments = []

        for apt in all_appointments:
            customer_name = (
                apt.customer.full_name.lower()
                if apt.customer and apt.customer.full_name
                else ''
            )

            customer_phone = (
                apt.customer.phone.lower()
                if apt.customer and apt.customer.phone
                else ''
            )

            appointment_id = str(apt.id)

            if (
                kw_lower in customer_name
                or kw_lower in customer_phone
                or kw_lower in appointment_id
            ):
                filtered_appointments.append(apt)

        all_appointments = filtered_appointments

    total_items = len(all_appointments)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size

    appointments_paged = all_appointments[start:end]

    staff_list = dao.get_users(role=UserRole.STAFF)

    return render_template(
        'receptionist/appointment_list.html',
        appointments=appointments_paged,
        staff_list=staff_list,
        selected_date=date_str,
        selected_staff_id=staff_id,
        kw=kw,
        page=page,
        total_pages=total_pages
    ), 200


@app.route('/invoices/<int:invoice_id>/confirm-payment', methods=['PATCH'])
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def confirm_invoice_payment_route(invoice_id):
    data = request.get_json(silent=True) or request.form
    payment_method = data.get('payment_method')
    promotion_id = data.get('promotion_id')

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
@role_required(UserRole.RECEPTIONIST, UserRole.ADMIN)
def invoice_checkout_view(invoice_id):
    invoice = dao.get_invoice_by_id(invoice_id)
    if not invoice or invoice.status != InvoiceStatus.DRAFT:
        flash("Hóa đơn không hợp lệ hoặc đã thanh toán!", "error")
        return redirect('/reception/invoices')

    active_promos = dao.get_active_promotions()

    return render_template(
        'receptionist/invoice_checkout.html',
        invoice=invoice,
        promotions=active_promos
    ), 200


@app.route('/users/change-password', methods=['POST'])
@login_required
def change_password_route():
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


@app.route('/appointments/me', methods=['GET'])
@login_required
def my_appointments_view():
    kw = request.args.get('kw', '').strip()
    status_str = request.args.get('status', 'ALL')
    date_str = request.args.get('date', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    all_appts = dao.get_appointments_by_customer(current_user.id)

    if kw:
        kw_lower = kw.lower()
        all_appts = [
            a for a in all_appts
            if a.service and kw_lower in a.service.service_name.lower()
        ]

    if status_str and status_str != 'ALL':
        all_appts = [a for a in all_appts if a.status.name == status_str]

    if date_str:
        all_appts = [
            a for a in all_appts
            if a.appointment_date.strftime('%Y-%m-%d') == date_str
        ]

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
        datetime=datetime,
        timedelta=timedelta
    ), 200


@app.route('/staff/appointments', methods=['GET'])
@role_required(UserRole.STAFF, UserRole.ADMIN)
def staff_appointments_view():
    date_str = request.args.get(
        'date',
        date.today().strftime('%Y-%m-%d')
    ).strip()

    kw = request.args.get('kw', '').strip()
    status_str = request.args.get('status', 'ALL')

    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    staff_id = (
        current_user.id
        if current_user.role == UserRole.STAFF
        else request.args.get('staff_id', type=int)
    )

    if staff_id:
        all_appointments, _ = dao.get_appointments_by_staff(
            staff_id=staff_id,
            date_str=date_str,
            page=None
        )
    else:
        all_appointments = []

    count_total = len(all_appointments)

    count_confirmed = sum(
        1 for a in all_appointments
        if a.status.name == 'CONFIRMED'
    )

    count_completed = sum(
        1 for a in all_appointments
        if a.status.name == 'COMPLETED'
    )

    count_cancelled = sum(
        1 for a in all_appointments
        if a.status.name == 'CANCELLED'
    )

    filtered_appointments = all_appointments

    if status_str != 'ALL':
        filtered_appointments = [
            a for a in filtered_appointments
            if a.status.name == status_str
        ]

    if kw:
        kw_lower = kw.lower()

        filtered_appointments = [
            a for a in filtered_appointments
            if (
                (
                    a.customer
                    and a.customer.full_name
                    and kw_lower in a.customer.full_name.lower()
                )
                or (
                    a.customer
                    and a.customer.phone
                    and kw_lower in a.customer.phone.lower()
                )
            )
        ]

    total_items = len(filtered_appointments)

    total_pages = (
        math.ceil(total_items / page_size)
        if total_items > 0
        else 1
    )

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size

    appointments_paged = filtered_appointments[start:end]

    return render_template(
        'staff/staff_appointments.html',

        appointments=appointments_paged,

        selected_date=date_str,
        selected_status=status_str,
        kw=kw,

        count_total=count_total,
        count_confirmed=count_confirmed,
        count_completed=count_completed,
        count_cancelled=count_cancelled,

        page=page,
        total_pages=total_pages
    ), 200


@app.route('/api/staff/appointments', methods=['GET'])
@role_required(UserRole.STAFF, UserRole.ADMIN)
def staff_appointments_api():
    date_str = request.args.get('date')
    staff_id = request.args.get('staff_id', type=int)

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


@app.route('/customers/search', methods=['GET'])
@role_required(UserRole.STAFF, UserRole.ADMIN)
def search_customers_route():
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


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error/404.html'), 404


if __name__ == "__main__":
    app.run(debug=True)