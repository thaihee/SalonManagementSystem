from datetime import datetime, timedelta
import pytest
from app import dao
from app.models import UserRole


# =========================================================================
# HELPER: Đăng nhập giả lập qua session
# =========================================================================
@pytest.fixture
def login_as(client):
  def _login_as(user):
    with client.session_transaction() as sess:
      sess['user_id'] = str(user.id)
      sess['_user_id'] = str(user.id)
      sess['_fresh'] = True
    return client

  return _login_as


# =========================================================================
# USERS FIXTURES
# =========================================================================
@pytest.fixture
def admin_user(app):
  user = dao.add_user(
      'Admin Test',
      'admintest',
      'Admin123',
      '0900000001',
      'admin@test.com',
      role=UserRole.ADMIN,
  )
  user.raw_password = 'Admin123'
  return user


@pytest.fixture
def staff_user(app):
  user = dao.add_user(
      'Staff Test',
      'stafftest',
      'Staff123',
      '0900000002',
      'staff@test.com',
      role=UserRole.STAFF,
  )
  user.raw_password = 'Staff123'
  return user


@pytest.fixture
def receptionist_user(app):
  user = dao.add_user(
      'Reception Test',
      'receptiontest',
      'Recep123',
      '0900000003',
      'reception@test.com',
      role=UserRole.RECEPTIONIST,
  )
  user.raw_password = 'Recep123'
  return user


@pytest.fixture
def customer_user(app):
  user = dao.add_user(
      'Customer Test',
      'customertest',
      'Customer123',
      '0900000004',
      'customer@test.com',
      role=UserRole.CUSTOMER,
  )
  user.raw_password = 'Customer123'
  return user


# =========================================================================
# CLIENTS FIXTURES
# =========================================================================
@pytest.fixture
def admin_client(client, login_as, admin_user):
  return login_as(admin_user)


@pytest.fixture
def staff_client(client, login_as, staff_user):
  return login_as(staff_user)


@pytest.fixture
def receptionist_client(client, login_as, receptionist_user):
  return login_as(receptionist_user)


@pytest.fixture
def customer_client(client, login_as, customer_user):
  return login_as(customer_user)


# =========================================================================
# SAMPLE DATA FIXTURES DÙNG CHO INTEGRATION TESTS
# =========================================================================
@pytest.fixture
def sample_service(app):
  return dao.add_service(
      name='Cắt tóc nam', price=100000, duration=30, description='Cắt tóc nam'
  )


@pytest.fixture
def sample_product(app):
  return dao.add_product(
      name='Dầu gội', unit='CHAI', stock_quantity=50, min_stock_level=10
  )


@pytest.fixture
def sample_service_product(app, sample_service, sample_product):
  return dao.add_service_product(
      service_id=sample_service.id,
      product_id=sample_product.id,
      default_quantity=1,
  )


@pytest.fixture
def sample_appointment(app, customer_user, staff_user, sample_service):
  """Tạo sẵn 1 lịch hẹn mẫu trong tương lai cho các test case update/cancel/view"""
  target_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
  return dao.create_appointment(
      customer_id=customer_user.id,
      service_id=sample_service.id,
      staff_id=staff_user.id,
      date_str=target_date,
      time_str='09:00',
  )


@pytest.fixture
def sample_promotion(app):
  today = datetime.now().date()
  return dao.add_promotion(
      promo_code='SALE10',
      promo_type='PERCENT',
      value=10,
      start_date=today.strftime('%Y-%m-%d'),
      end_date=(today + timedelta(days=30)).strftime('%Y-%m-%d'),
  )


@pytest.fixture
def sample_invoice(app, customer_user, staff_user, sample_service):
  details_data = [
      {'item_type': 'SERVICE', 'item_id': sample_service.id, 'quantity': 1}
  ]
  return dao.create_invoice(
      customer_id=customer_user.id,
      staff_id=staff_user.id,
      details_data=details_data,
  )