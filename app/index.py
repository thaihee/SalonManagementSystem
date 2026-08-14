import math
from datetime import datetime
from functools import wraps

from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user

from app import app, dao, login, db, admin
from app.exceptions import ValidationError, DuplicateError, NotFoundError
from app.models import User, UserRole, Service
from app.decorators import role_required

# =========================================================================
# 0. FLASK-LOGIN USER LOADER + PHÂN QUYỀN
# =========================================================================
@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)

# =========================================================================
# 1. TRANG CHỦ SALON (INDEX - HIỂN THỊ DANH SÁCH DỊCH VỤ)
# =========================================================================
@app.route('/')
def index():
    kw = request.args.get('kw')
    page = request.args.get('page', 1, type=int)

    # 1. Lấy page_size từ config trước
    page_size = app.config.get('PAGE_SIZE', 4)

    # 2. Truyền page_size vào hàm load_services
    services = dao.load_services(kw=kw, page=page, page_size=page_size)
    total_services = dao.count_services(kw=kw)
    total_pages = math.ceil(total_services / page_size) if total_services > 0 else 1

    return render_template(
        "index.html",
        services=services,
        total_pages=total_pages,
        page=page,
        kw=kw
    ), 200


# =========================================================================
# 2. XÁC THỰC: ĐĂNG NHẬP (LOGIN)
# =========================================================================
@app.route('/login', methods=['GET'])
def login_view():
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('login.html'), 200


@app.route('/login', methods=['POST'])
def login_process():
    username = request.form.get('username')
    password = request.form.get('password')

    try:
        user = dao.auth_user(username=username, password=password)
        login_user(user=user)
        next_page = request.args.get('next')
        return redirect(next_page if next_page else '/'), 302

    except ValidationError as val:
        # HTTP 401 Unauthorized khi sai thông tin tài khoản
        return render_template('login.html', err_msg=str(val)), 401
    except Exception as ex:
        # HTTP 500 khi gặp lỗi hệ thống
        app.logger.exception(ex)
        return render_template('login.html', err_msg="Có lỗi hệ thống xảy ra!"), 500


# =========================================================================
# 3. XÁC THỰC: ĐĂNG XUẤT (LOGOUT)
# =========================================================================
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout_process():
    logout_user()
    return redirect('/login'), 302


# =========================================================================
# 4. XÁC THỰC: ĐĂNG KÝ TÀI KHOẢN KHÁCH HÀNG (REGISTER)
# =========================================================================
@app.route('/register', methods=['GET'])
def register_view():
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('register.html'), 200


@app.route('/register', methods=['POST'])
def register_process():
    data = request.form
    password = data.get("password")
    confirm = data.get("confirm")
    avatar = data.get("avatar")

    if password != confirm:
        return render_template('register.html', err_msg="Mật khẩu xác nhận không khớp!"), 400

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
        return render_template('register.html', err_msg=str(ex)), 400
    except DuplicateError as ex:
        # HTTP 409 Conflict: username/email đã tồn tại
        return render_template('register.html', err_msg=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return render_template('register.html', err_msg="Lỗi hệ thống khi đăng ký!"), 500


# =========================================================================
# 5. HỒ SƠ CÁ NHÂN (USER PROFILE) — /users/me theo đúng API spec
# =========================================================================
@app.route('/users/me', methods=['GET'])
@login_required
def users_me_view():
    return render_template('profile.html'), 200


@app.route('/users/me', methods=['PUT'])
@login_required
def users_me_update():
    data = request.form
    avatar = data.get("avatar")
    try:
        dao.update_user_profile(
            user_id=current_user.id,
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            email=data.get('email'),
            avatar=avatar
        )
        return render_template('profile.html', succ_msg="Cập nhật thông tin thành công!"), 200
    except NotFoundError as ex:
        return render_template('profile.html', err_msg=str(ex)), 404
    except ValidationError as ex:
        return render_template('profile.html', err_msg=str(ex)), 400
    except DuplicateError as ex:
        return render_template('profile.html', err_msg=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return render_template('profile.html', err_msg="Không thể cập nhật hồ sơ!"), 500


# =========================================================================
# 6. LỊCH HẸN
# =========================================================================
# GET /appointments/available-slots?staff_id=1&service_id=2&date=2026-08-20
@app.route('/appointments/available-slots', methods=['GET'])
def get_available_slots_route():
    service_id = request.args.get('service_id')
    date_str = request.args.get('date')
    staff_id = request.args.get('staff_id')

    if not service_id or not date_str:
        return jsonify({"error": "Thiếu service_id hoặc date!"}), 400

    try:
        slots = dao.get_available_slots(
            service_id=int(service_id),
            date_str=date_str,
            staff_id=int(staff_id) if staff_id else None
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

    # Mặc định lấy id của user đang đăng nhập (KH đặt cho chính mình),
    # Hoặc nếu là Lễ tân/Admin thì có thể truyền customer_id đặt hộ.
    customer_id = data.get('customer_id', current_user.id)

    # Validate các trường dữ liệu bắt buộc
    if not all([service_id, staff_id, date_str, time_str]):
        return jsonify({"error": "Vui lòng cung cấp đầy đủ: service_id, staff_id, date, time!"}), 400

    try:
        appointment = dao.create_appointment(
            customer_id=int(customer_id),
            service_id=int(service_id),
            staff_id=int(staff_id),
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

    try:
        appt = dao.update_appointment(
            appointment_id=appointment_id,
            service_id=int(data.get('service_id')) if data.get('service_id') else None,
            staff_id=int(data.get('staff_id')) if data.get('staff_id') else None,
            date_str=data.get('date'),
            time_str=data.get('time'),
            note=data.get('note'),
            status=data.get('status')
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


# =========================================================================
# 7. QUẢN LÝ HÓA ĐƠN & THANH TOÁN (INVOICES)
# =========================================================================

# POST /invoices - API Thanh toán & Tạo hóa đơn
@app.route('/invoices', methods=['POST'])
@login_required
def create_invoice_route():
    data = request.get_json(silent=True) or request.form

    customer_id = data.get('customer_id')
    appointment_id = data.get('appointment_id')
    payment_method = data.get('payment_method', 'CASH')
    discount_percent = data.get('discount_percent', 0)
    details = data.get('details', [])

    # Nhân viên lập hóa đơn chính là tài khoản staff/admin đang đăng nhập
    staff_id = current_user.id

    if not customer_id or not details:
        return jsonify({"error": "Vui lòng cung cấp customer_id và danh sách chi tiết (details)!"}), 400

    try:
        invoice = dao.create_invoice(
            customer_id=int(customer_id),
            staff_id=int(staff_id),
            payment_method=payment_method,
            details_data=details,
            discount_percent=discount_percent,
            appointment_id=int(appointment_id) if appointment_id else None
        )

        return jsonify({
            "message": "Tạo hóa đơn & thanh toán thành công!",
            "invoice": {
                "id": invoice.id,
                "customer_id": invoice.customer_id,
                "staff_id": invoice.staff_id,
                "appointment_id": invoice.appointment_id,
                "discount_percent": invoice.discount_percent,
                "total_amount": invoice.total_amount,
                "payment_method": invoice.payment_method.name,
                "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 201

    except ValidationError as ex:
        return jsonify({"error": str(ex)}), 400
    except NotFoundError as ex:
        return jsonify({"error": str(ex)}), 404
    except DuplicateError as ex:
        return jsonify({"error": str(ex)}), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify({"error": "Lỗi hệ thống khi thanh toán hóa đơn!"}), 500


# =========================================================================
# CHẠY ỨNG DỤNG
# =========================================================================
if __name__ == "__main__":
    app.run(debug=True)