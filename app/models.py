import hashlib
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Column, String, Enum, Float, Text, DateTime, Integer, ForeignKey, UniqueConstraint, BigInteger, Boolean
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
    RECEPTIONIST = 4


class AppointmentStatus(UserEnum):
    CONFIRMED = 1
    CANCELLED = 2
    COMPLETED = 3


class PaymentMethod(UserEnum):
    CASH = 1
    BANK_TRANSFER = 2
    CARD = 3


class InvoiceStatus(UserEnum):
    DRAFT = 1
    PAID = 2
    CANCELLED = 3


class InvoiceItemType(UserEnum):
    SERVICE = 1
    PRODUCT_USED = 2


class ProductUnit(UserEnum):
    CHAI = 1
    GOI = 2
    ML = 3
    GRAM = 4


class PromotionType(UserEnum):
    PERCENT = 1
    FIXED = 2


class User(BaseModel, UserMixin):
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False, unique=True)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    avatar = Column(String(255), nullable=True,
                    default="https://res.cloudinary.com/dxxwcby8l/image/upload/v1647056401/ipmsmnxjydrhsrthx0bd.jpg")


    appointments_as_customer = relationship('Appointment', foreign_keys='Appointment.customer_id', backref='customer', lazy=True)
    appointments_as_staff = relationship('Appointment', foreign_keys='Appointment.staff_id', backref='staff', lazy=True)
    invoices_as_customer = relationship('Invoice', foreign_keys='Invoice.customer_id', backref='customer', lazy=True)
    invoices_as_staff = relationship('Invoice', foreign_keys='Invoice.staff_id', backref='staff', lazy=True)
    invoices_as_receptionist = relationship('Invoice', foreign_keys='Invoice.receptionist_id', backref='receptionist', lazy=True)

    def __str__(self):
        return self.full_name


class Service(BaseModel):
    service_name = Column(String(100), nullable=False, unique=True)
    price = Column(Float, default=0, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)
    description = Column(Text, nullable=True)
    avatar = Column(String(255), nullable=True,
                    default="https://res.cloudinary.com/dxxwcby8l/image/upload/v1683162354/placeholder-image_q8mpxv.png")

    appointments = relationship('Appointment', backref='service', lazy=True)
    invoice_details = relationship('InvoiceDetail', backref='service', lazy=True)

    def __str__(self):
        return self.service_name


class Product(BaseModel):
    product_name = Column(String(100), nullable=False, unique=True)
    unit = Column(Enum(ProductUnit), default=ProductUnit.CHAI, nullable=False)
    stock_quantity = Column(Float, default=0, nullable=False)
    min_stock_level = Column(Float, default=5, nullable=False)

    invoice_details = relationship('InvoiceDetail', backref='product', lazy=True)

    def __str__(self):
        return f"{self.product_name} ({self.unit.name})"


class ServiceProduct(BaseModel):
    service_id = Column(Integer, ForeignKey(Service.id), nullable=False)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=False)
    default_quantity = Column(Float, default=0, nullable=False)   # định mức gợi ý, VD: 30 (ml)

    service = relationship('Service', backref='available_products')
    product = relationship('Product', backref='used_in_services')

    __table_args__ = (
        UniqueConstraint('service_id', 'product_id', name='unique_service_product'),
    )

    def __str__(self):
        return f"{self.service.service_name} - {self.product.product_name}"


class Appointment(BaseModel):
    appointment_date = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.CONFIRMED)
    note = Column(Text, nullable=True)

    customer_id = Column(Integer, ForeignKey(User.id), nullable=False)
    staff_id = Column(Integer, ForeignKey(User.id), nullable=True)
    service_id = Column(Integer, ForeignKey(Service.id), nullable=False)

    __table_args__ = (
        UniqueConstraint('staff_id', 'appointment_date', name='unique_staff_appointment_time'),
    )

    def __str__(self):
        return self.appointment_date.strftime('%d/%m/%Y %H:%M')


class Promotion(BaseModel):
    promo_code = Column(String(50), nullable=False, unique=True)
    promo_type = Column(Enum(PromotionType), nullable=False, default=PromotionType.PERCENT)
    value = Column(Float, nullable=False)   # % (0-100) hoặc số tiền cố định tùy promo_type
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    invoices = relationship('Invoice', backref='promotion', lazy=True)

    def __str__(self):
        return self.promo_code


class Invoice(BaseModel):
    invoice_date = Column(DateTime, default=datetime.now)
    total_amount = Column(Float, default=0, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=True)

    customer_id = Column(Integer, ForeignKey(User.id), nullable=False)
    staff_id = Column(Integer, ForeignKey(User.id), nullable=False)
    receptionist_id = Column(Integer, ForeignKey(User.id), nullable=True)
    appointment_id = Column(Integer, ForeignKey(Appointment.id), nullable=True)
    promotion_id = Column(Integer, ForeignKey(Promotion.id), nullable=True)

    details = relationship('InvoiceDetail', backref='invoice', lazy=True)

    __table_args__ = (
        UniqueConstraint('appointment_id', name='unique_invoice_per_appointment'),
    )

    def __str__(self):
        return f'Hóa đơn #{self.id}'


class InvoiceDetail(BaseModel):
    item_type = Column(Enum(InvoiceItemType), nullable=False)
    quantity = Column(Float, default=1, nullable=False)
    unit_price = Column(Float, default=0, nullable=False)
    subtotal = Column(Float, default=0, nullable=False)

    invoice_id = Column(Integer, ForeignKey(Invoice.id), nullable=False)
    service_id = Column(Integer, ForeignKey(Service.id), nullable=True)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=True)

    def __str__(self):
        return f'Chi tiết hóa đơn #{self.id}'


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        password = str(hashlib.md5('123456'.encode('utf-8')).hexdigest())

        admin = User(full_name="Nguyễn Văn Quản Lý", username="admin", password=password,
                     role=UserRole.ADMIN, phone="0900000000", email="admin@salon.com")

        staff1 = User(full_name="Trần Thị Hằng", username="staff1", password=password,
                      role=UserRole.STAFF, phone="0911111111", email="staff1@salon.com")

        staff2 = User(full_name="Lê Văn Tuấn", username="staff2", password=password,
                      role=UserRole.STAFF, phone="0911111112", email="staff2@salon.com")

        receptionist1 = User(full_name="Đỗ Thị Mai", username="letan1", password=password,
                      role=UserRole.RECEPTIONIST, phone="0933333331", email="letan1@salon.com")

        cus1 = User(full_name="Phạm Thị Lan", username="customer1", password=password,
                    role=UserRole.CUSTOMER, phone="0922222221", email="cus1@salon.com")

        cus2 = User(full_name="Hoàng Văn Nam", username="customer2", password=password,
                    role=UserRole.CUSTOMER, phone="0922222222", email="cus2@salon.com")

        db.session.add_all([admin, staff1, staff2, receptionist1, cus1, cus2])
        db.session.flush()


        services_data = [
            Service(service_name='Cắt tóc nam', price=100000, duration_minutes=30,
                    description='Cắt tóc nam cơ bản'),
            Service(service_name='Gội đầu dưỡng sinh', price=120000, duration_minutes=40,
                    description='Gội đầu kết hợp massage thư giãn'),
            Service(service_name='Uốn tóc', price=350000, duration_minutes=90,
                    description='Uốn tóc kèm dưỡng'),
            Service(service_name='Nhuộm tóc', price=280000, duration_minutes=75,
                    description='Nhuộm màu theo yêu cầu'),
            Service(service_name='Duỗi tóc', price=320000, duration_minutes=90,
                    description='Duỗi tóc thẳng mượt'),
            Service(service_name='Hấp dầu phục hồi', price=150000, duration_minutes=45,
                    description='Hấp dầu phục hồi tóc hư tổn'),
            Service(service_name='Cạo mặt tạo kiểu râu', price=80000, duration_minutes=20,
                    description='Cạo mặt, tỉa và tạo kiểu râu'),
            Service(service_name='Massage da đầu', price=100000, duration_minutes=30,
                    description='Massage thư giãn da đầu'),
            Service(service_name='Nối mi tạo kiểu', price=200000, duration_minutes=60,
                    description='Nối mi tạo kiểu tự nhiên'),
            Service(service_name='Combo cắt gội tạo kiểu', price=180000, duration_minutes=60,
                    description='Combo cắt tóc, gội đầu và tạo kiểu'),
        ]
        db.session.add_all(services_data)


        products_data = [
            Product(product_name='Dầu gội', unit=ProductUnit.ML, stock_quantity=5000, min_stock_level=500),
            Product(product_name='Dầu xả', unit=ProductUnit.ML, stock_quantity=3000, min_stock_level=300),
            Product(product_name='Thuốc uốn', unit=ProductUnit.GOI, stock_quantity=30, min_stock_level=5),
            Product(product_name='Dầu dưỡng sau uốn', unit=ProductUnit.ML, stock_quantity=2000, min_stock_level=200),
            Product(product_name='Thuốc nhuộm', unit=ProductUnit.GOI, stock_quantity=40, min_stock_level=5),
            Product(product_name='Oxy trợ nhuộm', unit=ProductUnit.ML, stock_quantity=3000, min_stock_level=300),
            Product(product_name='Thuốc duỗi', unit=ProductUnit.GOI, stock_quantity=25, min_stock_level=5),
            Product(product_name='Kem ủ dưỡng', unit=ProductUnit.GRAM, stock_quantity=4000, min_stock_level=400),
            Product(product_name='Kem cạo', unit=ProductUnit.ML, stock_quantity=1000, min_stock_level=100),
            Product(product_name='Tinh dầu massage', unit=ProductUnit.ML, stock_quantity=1000, min_stock_level=100),
            Product(product_name='Keo nối mi', unit=ProductUnit.ML, stock_quantity=200, min_stock_level=20),
            Product(product_name='Gel tạo kiểu', unit=ProductUnit.GRAM, stock_quantity=2000, min_stock_level=200),
        ]
        db.session.add_all(products_data)
        db.session.flush()


        svc = {s.service_name: s for s in services_data}
        prd = {p.product_name: p for p in products_data}


        service_products_data = [

            ServiceProduct(service_id=svc['Gội đầu dưỡng sinh'].id, product_id=prd['Dầu gội'].id, default_quantity=30),
            ServiceProduct(service_id=svc['Gội đầu dưỡng sinh'].id, product_id=prd['Dầu xả'].id, default_quantity=15),

            ServiceProduct(service_id=svc['Uốn tóc'].id, product_id=prd['Thuốc uốn'].id, default_quantity=1),
            ServiceProduct(service_id=svc['Uốn tóc'].id, product_id=prd['Dầu dưỡng sau uốn'].id, default_quantity=20),

            ServiceProduct(service_id=svc['Nhuộm tóc'].id, product_id=prd['Thuốc nhuộm'].id, default_quantity=1),
            ServiceProduct(service_id=svc['Nhuộm tóc'].id, product_id=prd['Oxy trợ nhuộm'].id, default_quantity=50),

            ServiceProduct(service_id=svc['Duỗi tóc'].id, product_id=prd['Thuốc duỗi'].id, default_quantity=1),
            ServiceProduct(service_id=svc['Duỗi tóc'].id, product_id=prd['Kem ủ dưỡng'].id, default_quantity=30),

            ServiceProduct(service_id=svc['Hấp dầu phục hồi'].id, product_id=prd['Kem ủ dưỡng'].id, default_quantity=50),

            ServiceProduct(service_id=svc['Cạo mặt tạo kiểu râu'].id, product_id=prd['Kem cạo'].id, default_quantity=10),

            ServiceProduct(service_id=svc['Massage da đầu'].id, product_id=prd['Tinh dầu massage'].id, default_quantity=15),

            ServiceProduct(service_id=svc['Nối mi tạo kiểu'].id, product_id=prd['Keo nối mi'].id, default_quantity=2),

            ServiceProduct(service_id=svc['Combo cắt gội tạo kiểu'].id, product_id=prd['Dầu gội'].id, default_quantity=30),
            ServiceProduct(service_id=svc['Combo cắt gội tạo kiểu'].id, product_id=prd['Gel tạo kiểu'].id, default_quantity=10),
        ]
        db.session.add_all(service_products_data)

        promo1 = Promotion(promo_code='SALON10', promo_type=PromotionType.PERCENT, value=10,
                           start_date=datetime(2026, 1, 1), end_date=datetime(2026, 12, 31))
        db.session.add(promo1)

        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        appointments_data = [
            Appointment(appointment_date=now.replace(hour=14), status=AppointmentStatus.COMPLETED,
                        customer_id=cus1.id, staff_id=staff1.id, service_id=svc['Cắt tóc nam'].id),
            Appointment(appointment_date=now.replace(hour=16), status=AppointmentStatus.CONFIRMED,
                        customer_id=cus2.id, staff_id=staff2.id, service_id=svc['Uốn tóc'].id),
        ]
        db.session.add_all(appointments_data)
        db.session.flush()

        invoice1 = Invoice(status=InvoiceStatus.DRAFT,
                           customer_id=cus1.id, staff_id=staff1.id,
                           appointment_id=appointments_data[0].id)
        db.session.add(invoice1)
        db.session.flush()

        invoice_details_data = [
            InvoiceDetail(item_type=InvoiceItemType.SERVICE, quantity=1,
                          unit_price=svc['Cắt tóc nam'].price, subtotal=svc['Cắt tóc nam'].price,
                          invoice_id=invoice1.id, service_id=svc['Cắt tóc nam'].id),
        ]
        db.session.add_all(invoice_details_data)

        invoice1.total_amount = svc['Cắt tóc nam'].price

        db.session.commit()

