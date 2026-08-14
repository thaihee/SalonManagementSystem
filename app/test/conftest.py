import pytest
from app import app as flask_app, db
import app.index


# =========================================================================
# FIXTURE: Cấu hình môi trường test độc lập
# =========================================================================
@pytest.fixture
def app():
    """Tạo môi trường Flask app riêng cho testing với SQLite in-memory"""
    flask_app.config.update({
        "TESTING": True,
        # Dùng SQLite trên RAM để test chạy nhanh và không ảnh hưởng DB thật
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False
    })

    with flask_app.app_context():
        db.create_all()  # Tạo các bảng tạm thời trên RAM
        yield flask_app
        db.session.remove()
        db.drop_all()  # Xóa sạch sau khi test xong


@pytest.fixture
def client(app):
    return app.test_client()