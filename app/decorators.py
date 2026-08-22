from functools import wraps

from flask import abort, redirect, request, url_for
from flask_login import current_user


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            # Chưa đăng nhập → chuyển về trang login
            if not current_user.is_authenticated:
                return redirect(
                    url_for('login_view', next=request.full_path)
                )

            # Đã đăng nhập nhưng không đúng role
            if current_user.role not in roles:
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator