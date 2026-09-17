import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

import cloudinary

app = Flask(__name__)
app.secret_key = "&(^&*^&*^U*HJBJKHJLHKJHK&*%^&5786985646858"
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:root@localhost/salondb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 4
db = SQLAlchemy(app=app)
login = LoginManager(app=app)
login.login_view = 'login_view'
login.login_message = 'Vui lòng đăng nhập để tiếp tục đặt lịch hẹn!'
login.login_message_category = 'info'

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

csrf = CSRFProtect(app)
app.config['WTF_CSRF_ENABLED'] = True
