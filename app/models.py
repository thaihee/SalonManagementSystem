from app import db

class Services(db.Model):
    __tablename__ = 'services'
    ma_dv = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ten_dv = db.Column(db.String(100), nullable=False)
    gia = db.Column(db.Float, nullable=False)
    thoi_luong = db.Column(db.Integer)
    mo_ta = db.Column(db.String(255))