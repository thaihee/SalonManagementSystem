import os

import pytest
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf

from app import app as flask_app, db
import app.index
import app.admin

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost"
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test Client cơ bản"""
    return app.test_client()


# --- CSRF PROTECTION FIXTURES (Dùng cho test_security_csrf.py) ---
@pytest.fixture
def app_csrf_enabled():
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": True,
        "SECRET_KEY": "&(^&*^&*^U*HJBJKHJLHKJHK&*%^&5786985646858"
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        # db.session.remove()
        # db.drop_all()


@pytest.fixture
def client_csrf_enabled(app_csrf_enabled):
    return app_csrf_enabled.test_client()


@pytest.fixture
def valid_csrf_token(app_csrf_enabled, client_csrf_enabled):
    """Tạo CSRF token đồng thời duy trì Cookie Session chuẩn"""
    with app_csrf_enabled.test_request_context():
        client_csrf_enabled.get('/')
        with client_csrf_enabled.session_transaction() as sess:
            token = generate_csrf()
            sess['csrf_token'] = token
            return token