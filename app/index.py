import math
from datetime import datetime
from functools import wraps

from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user

from app import app, dao, login, db
from app.exceptions import ValidationError, DuplicateError, NotFoundError
from app.models import User, UserRole, Service


# =========================================================================
# 0. FLASK-LOGIN USER LOADER + PHÂN QUYỀN
# =========================================================================
@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


def role_required(*roles):
    """Decorator chặn truy cập route nếu user chưa đăng nhập hoặc sai vai trò.
    Dùng ở index.py và admin.py: @role_required(UserRole.ADMIN, UserRole.STAFF)"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# =========================================================================
# 1. TRANG CHỦ SALON (INDEX - HIỂN THỊ DANH SÁCH DỊCH VỤ)
# =========================================================================
@app.route('/')
def index():
    kw = request.args.get('kw')
    page = int(request.args.get('page', 1))

    # Lấy danh sách dịch vụ và tính số trang
    services = dao.load_services(kw=kw, page=page)
    total_services = dao.count_services(kw=kw)
    page_size = app.config.get('PAGE_SIZE', 8)
    total_pages = math.ceil(total_services / page_size) if total_services > 0 else 1

    return render_template(
        "index.html",
        services=services,
        pages=total_pages,
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

    if password != confirm:
        return render_template('register.html', err_msg="Mật khẩu xác nhận không khớp!"), 400

    try:
        dao.add_user(
            full_name=data.get('full_name'),
            username=data.get('username'),
            password=password,
            phone=data.get('phone'),
            email=data.get('email'),
            role=UserRole.CUSTOMER
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
# 5. HỒ SƠ CÁ NHÂN (USER PROFILE)
# =========================================================================
@app.route('/profile', methods=['GET'])
@login_required
def profile_view():
    return render_template('profile.html'), 200


@app.route('/profile', methods=['POST'])
@login_required
def update_profile_process():
    data = request.form
    try:
        dao.update_user_profile(
            user_id=current_user.id,
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            email=data.get('email')
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
# CHẠY ỨNG DỤNG
# =========================================================================
if __name__ == "__main__":
    app.run(debug=True)