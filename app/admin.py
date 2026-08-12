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