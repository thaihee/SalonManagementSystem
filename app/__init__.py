import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

import cloudinary

app = Flask(__name__)
app.secret_key = "&(^&*^&*^U*HJBJKHJLHKJHK&*%^&5786985646858"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'salondb.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 4
db = SQLAlchemy(app=app)
login = LoginManager(app=app)

cloudinary.config(cloud_name='dphbawbuk',
api_key='466151686122924',
api_secret='dH86bZJEC8Z800SNhRZVQEw648k')

csrf = CSRFProtect(app)
app.config['WTF_CSRF_ENABLED'] = False   # TODO: bật lại khi làm frontend, gắn {{ csrf_token() }} vào form

# from app import admin