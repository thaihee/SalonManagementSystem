from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """
    Decorator kiểm tra quyền truy cập.
    Hỗ trợ truyền 1 hoặc nhiều role:
    @role_required(UserRole.ADMIN) hoặc @role_required(UserRole.STAFF, UserRole.ADMIN)
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator