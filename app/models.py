import hashlib
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Column, String, Enum, Float, Text, DateTime, Integer, ForeignKey, UniqueConstraint, BigInteger
from sqlalchemy.orm import relationship

from app import db, app
from enum import Enum as UserEnum



class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    active = db.Column(db.Boolean, default=True)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class UserRole(UserEnum):
    ADMIN = 1
    STAFF = 2
    CUSTOMER = 3

class AppointmentStatus(UserEnum):
    PENDING = 1
    CONFIRMED = 2
    CANCELLED = 3
    COMPLETED = 4

class PaymentMethod(UserEnum):
    CASH = 1
    BANK_TRANSFER = 2
    CARD = 3

class InvoiceItemType(UserEnum):
    SERVICE = 1
    PRODUCT = 2

class User(BaseModel, UserMixin):
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(100), unique=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CUSTOMER)

    appointments_as_customer = relationship('Appointment', foreign_keys='Appointment.customer_id', backref='customer', lazy=True)
    appointments_as_staff = relationship('Appointment', foreign_keys='Appointment.staff_id', backref='staff', lazy=True)
    invoices_as_customer = relationship('Invoice', foreign_keys='Invoice.customer_id', backref='customer', lazy=True)
    invoices_as_staff = relationship('Invoice', foreign_keys='Invoice.staff_id', backref='staff', lazy=True)

    def __str__(self):
        return self.full_name


class Service(BaseModel):
    service_name = Column(String(100), nullable=False, unique=True)
    price = Column(Float, default=0, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)
    description = Column(Text, nullable=True)

    appointments = relationship('Appointment', backref='service', lazy=True)
    invoice_details = relationship('InvoiceDetail', backref='service', lazy=True)

    def __str__(self):
        return self.service_name


class Product(BaseModel):
    product_name = Column(String(100), nullable=False, unique=True)
    price = Column(BigInteger, default=0, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    min_stock_level = Column(Integer, default=5, nullable=False)

    invoice_details = relationship('InvoiceDetail', backref='product', lazy=True)

    def __str__(self):
        return self.product_name


class Appointment(BaseModel):
    appointment_date = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    note = Column(Text, nullable=True)

    customer_id = Column(Integer, ForeignKey(User.id), nullable=False)
    staff_id = Column(Integer, ForeignKey(User.id), nullable=True)
    service_id = Column(Integer, ForeignKey(Service.id), nullable=False)

    #Tạo ràng buộc mỗi nhân viên không được nhận trùng 2 lịch hẹn cùng 1 thời điểm
    __table_args__ = (
        UniqueConstraint('staff_id', 'appointment_date', name='unique_staff_appointment_time'),
    )

    def __str__(self):
        return self.appointment_date.strftime('%d/%m/%Y %H:%M')


class Invoice(BaseModel):
    invoice_date = Column(DateTime, default=datetime.now)
    total_amount = Column(Float, default=0, nullable=False)
    discount_percent = Column(Float, default=0, nullable=False)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH)

    customer_id = Column(Integer, ForeignKey(User.id), nullable=False)
    staff_id = Column(Integer, ForeignKey(User.id), nullable=False)
    appointment_id = Column(Integer, ForeignKey(Appointment.id), nullable=True)

    details = relationship('InvoiceDetail', backref='invoice', lazy=True)

    #Tạo ràng buộc mỗi lịch hẹn chỉ được lập tối đa 1 hóa đơn
    __table_args__ = (
        UniqueConstraint('appointment_id', name='unique_invoice_per_appointment'),
    )

    def __str__(self):
        return f'Hóa đơn #{self.id}'


class InvoiceDetail(BaseModel):
    item_type = Column(Enum(InvoiceItemType), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    invoice_id = Column(Integer, ForeignKey(Invoice.id), nullable=False)
    service_id = Column(Integer, ForeignKey(Service.id), nullable=True)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=True)

    def __str__(self):
        return f'Chi tiết hóa đơn #{self.id}'


if __name__ == '__main__':
    with app.app_context():
        #db.drop_all()

        # 1. Khởi tạo bảng
        db.create_all()

        # 2. Thêm Người dùng (User)
        password = str(hashlib.md5('123456'.encode('utf-8')).hexdigest())

        admin = User(full_name="Nguyễn Văn Quản Lý", username="admin", password=password,
                     role=UserRole.ADMIN, phone="0900000000", email="admin@salon.com")

        staff1 = User(full_name="Trần Thị Hằng", username="staff1", password=password,
                      role=UserRole.STAFF, phone="0911111111", email="staff1@salon.com")

        staff2 = User(full_name="Lê Văn Tuấn", username="staff2", password=password,
                      role=UserRole.STAFF, phone="0911111112", email="staff2@salon.com")

        cus1 = User(full_name="Phạm Thị Lan", username="customer1", password=password,
                    role=UserRole.CUSTOMER, phone="0922222221", email="cus1@salon.com")

        #Tạo thêm customer2
        cus2 = User(full_name="Hoàng Văn Nam", username="customer2", password=password,
                    role=UserRole.CUSTOMER, phone="0922222222", email="cus2@salon.com")

        db.session.add_all([admin, staff1, staff2, cus1, cus2])
        db.session.flush()

        # 3. Thêm Dịch vụ (Service)
        services_data = [
            Service(service_name='Cắt tóc nam', price=100000, duration_minutes=30,
                    description='Cắt tóc nam cơ bản'),
            Service(service_name='Uốn tóc', price=350000, duration_minutes=90,
                    description='Uốn tóc kèm dưỡng'),
            Service(service_name='Nhuộm tóc', price=280000, duration_minutes=75,
                    description='Nhuộm màu theo yêu cầu'),
            Service(service_name='Gội đầu dưỡng sinh', price=120000, duration_minutes=40,
                    description='Gội đầu kết hợp massage thư giãn'),
        ]
        db.session.add_all(services_data)

        # 4. Thêm Sản phẩm (Product)
        products_data = [
            Product(product_name='Dầu gội dưỡng ẩm', price=150000, stock_quantity=20, min_stock_level=5),
            Product(product_name='Gel vuốt tóc', price=80000, stock_quantity=15, min_stock_level=5),
            Product(product_name='Thuốc uốn tóc', price=200000, stock_quantity=8, min_stock_level=3),
            Product(product_name='Sáp vuốt tóc', price=90000, stock_quantity=3, min_stock_level=5),
        ]
        db.session.add_all(products_data)

        db.session.flush()

        # 5. Thêm Lịch hẹn (Appointment)
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        appointments_data = [
            Appointment(appointment_date=now.replace(hour=14), status=AppointmentStatus.CONFIRMED,
                        customer_id=cus1.id, staff_id=staff1.id, service_id=services_data[0].id),
            Appointment(appointment_date=now.replace(hour=16), status=AppointmentStatus.PENDING,
                        customer_id=cus2.id, staff_id=staff2.id, service_id=services_data[1].id),
        ]
        db.session.add_all(appointments_data)
        db.session.flush()

        # 6. Thêm Hóa đơn (Invoice) + Chi tiết hóa đơn (InvoiceDetail)
        invoice1 = Invoice(total_amount=180000, discount_percent=0, payment_method=PaymentMethod.CASH,
                           customer_id=cus1.id, staff_id=staff1.id, appointment_id=appointments_data[0].id)
        db.session.add(invoice1)
        db.session.flush()

        invoice_details_data = [
            InvoiceDetail(item_type=InvoiceItemType.SERVICE, quantity=1,
                          unit_price=services_data[0].price, subtotal=services_data[0].price,
                          invoice_id=invoice1.id, service_id=services_data[0].id),
            InvoiceDetail(item_type=InvoiceItemType.PRODUCT, quantity=1,
                          unit_price=products_data[1].price, subtotal=products_data[1].price,
                          invoice_id=invoice1.id, product_id=products_data[1].id),
        ]
        db.session.add_all(invoice_details_data)

        db.session.commit()