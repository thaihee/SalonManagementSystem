from flask import request, jsonify
from flask_login import login_required

from app import app, dao
from app.decorators import role_required
from app.models import UserRole
from app.exceptions import ValidationError, DuplicateError, NotFoundError


# =========================Nghiệp vụ 2: CRUD Dịch vụ (Quản lý)==========================
# Trả JSON vì chưa làm giao diện - sẽ nối template sau khi có frontend

@app.route('/admin/services', methods=['GET'])
@role_required(UserRole.ADMIN)
def list_services():
    services = dao.get_all_services()
    return jsonify([{
        "id": s.id,
        "service_name": s.service_name,
        "price": s.price,
        "duration_minutes": s.duration_minutes,
        "description": s.description,
        "active": s.active
    } for s in services]), 200


@app.route('/admin/services', methods=['POST'])
@role_required(UserRole.ADMIN)
def create_service():
    data = request.form
    try:
        # FIX: dao.add_service() nhận tham số (name, price, duration, description)
        # chứ không phải (service_name, duration_minutes) -- trước đây gọi sai tên
        # keyword argument sẽ ném TypeError.
        s = dao.add_service(
            name=data.get('service_name'),
            price=data.get('price'),
            duration=data.get('duration_minutes'),
            description=data.get('description')
        )
        return jsonify(success=True, id=s.id), 201
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi thêm dịch vụ!"), 500


@app.route('/admin/services/<int:service_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_service_route(service_id):
    data = request.form
    try:
        # FIX: cùng lỗi keyword argument như create_service() ở trên
        dao.update_service(
            service_id=service_id,
            name=data.get('service_name'),
            price=data.get('price'),
            duration=data.get('duration_minutes'),
            description=data.get('description')
        )
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi cập nhật dịch vụ!"), 500


@app.route('/admin/services/<int:service_id>', methods=['DELETE'])
@role_required(UserRole.ADMIN)
def delete_service_route(service_id):
    try:
        dao.delete_service(service_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi xóa dịch vụ!"), 500


# =========================Nghiệp vụ 3b: Nhập / Xuất kho (Quản lý)==========================

@app.route('/admin/products/<int:product_id>/import', methods=['POST'])
@role_required(UserRole.ADMIN)
def import_stock_route(product_id):
    data = request.form
    try:
        p = dao.import_stock(product_id, data.get('quantity'))
        return jsonify(success=True, product_id=p.id, stock_quantity=p.stock_quantity), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi nhập kho!"), 500


@app.route('/admin/products/<int:product_id>/export', methods=['POST'])
@role_required(UserRole.ADMIN)
def export_stock_route(product_id):
    data = request.form
    try:
        p = dao.export_stock(product_id, data.get('quantity'))
        return jsonify(success=True, product_id=p.id, stock_quantity=p.stock_quantity), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        # Bắt cả 2 case: số lượng <= 0 và xuất vượt tồn kho (không cho xuất âm)
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi xuất kho!"), 500


# =========================Nghiệp vụ 3c: Cảnh báo tồn kho thấp==========================

@app.route('/admin/products/low-stock', methods=['GET'])
@role_required(UserRole.ADMIN)
def low_stock_products_route():
    products = dao.check_low_stock_products()
    return jsonify([{
        "id": p.id,
        "product_name": p.product_name,
        "stock_quantity": p.stock_quantity,
        "min_stock_level": p.min_stock_level
    } for p in products]), 200


# =========================Nghiệp vụ 1b: Admin quản lý User/Nhân viên==========================

def _serialize_user(u):
    return {
        "id": u.id,
        "full_name": u.full_name,
        "username": u.username,
        "phone": u.phone,
        "email": u.email,
        "role": u.role.name,
        "active": u.active
    }


@app.route('/users', methods=['GET'])
@role_required(UserRole.ADMIN)
def list_users_route():
    role_param = request.args.get('role')
    role = None
    if role_param:
        try:
            role = UserRole[role_param.upper()]
        except KeyError:
            return jsonify(success=False, error=f"Role '{role_param}' không hợp lệ!"), 400

    users = dao.get_users(role=role)
    return jsonify([_serialize_user(u) for u in users]), 200


@app.route('/users/<int:user_id>', methods=['GET'])
@role_required(UserRole.ADMIN)
def get_user_detail_route(user_id):
    u = dao.get_user_by_id(user_id)
    if not u:
        return jsonify(success=False, error="Không tìm thấy người dùng!"), 404
    return jsonify(_serialize_user(u)), 200


@app.route('/users', methods=['POST'])
@role_required(UserRole.ADMIN)
def create_staff_route():
    """Admin tạo tài khoản nhân viên (role=STAFF)"""
    data = request.form
    try:
        u = dao.add_user(
            full_name=data.get('full_name'),
            username=data.get('username'),
            password=data.get('password'),
            phone=data.get('phone'),
            email=data.get('email'),
            role=UserRole.STAFF
        )
        return jsonify(success=True, user=_serialize_user(u)), 201
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi tạo tài khoản nhân viên!"), 500


@app.route('/users/<int:user_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_staff_route(user_id):
    data = request.form
    try:
        u = dao.update_user_profile(
            user_id=user_id,
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        return jsonify(success=True, user=_serialize_user(u)), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi cập nhật nhân viên!"), 500


@app.route('/users/<int:user_id>', methods=['DELETE'])
@role_required(UserRole.ADMIN)
def deactivate_user_route(user_id):
    """Vô hiệu hóa nhân viên (soft delete qua active)"""
    try:
        dao.delete_user_soft(user_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi vô hiệu hóa tài khoản!"), 500