from flask import request, jsonify
from flask_login import login_required

from app import app, dao
from app.index import role_required
from app.models import UserRole
from app.exceptions import ValidationError, DuplicateError, NotFoundError


#=========================Nghiệp vụ 2: CRUD Dịch vụ (Quản lý)==========================
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
        s = dao.add_service(
            service_name=data.get('service_name'),
            price=data.get('price'),
            duration_minutes=data.get('duration_minutes'),
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
        dao.update_service(
            service_id=service_id,
            service_name=data.get('service_name'),
            price=data.get('price'),
            duration_minutes=data.get('duration_minutes'),
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