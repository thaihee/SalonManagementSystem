import pytest
from app.models import UserRole


# =========================================================================
# 1. KHÁCH HÀNG (CUSTOMER) CỐ TÌNH TRUY CẬP ROUTE NỘI BỘ -> 403 FORBIDDEN
# =========================================================================
class TestCustomerAccessRestrictions:

    def test_customer_cannot_access_admin_dashboard(self, customer_client):
        response = customer_client.get('/admin')
        assert response.status_code == 403

    def test_customer_cannot_access_admin_user_management(self, customer_client):
        response = customer_client.get('/admin/users')
        assert response.status_code == 403

    def test_customer_cannot_access_admin_reports(self, customer_client):
        response = customer_client.get('/admin/reports/revenue')
        assert response.status_code == 403

    def test_customer_cannot_access_staff_appointments(self, customer_client):
        response = customer_client.get('/staff/appointments')
        assert response.status_code == 403

    def test_customer_cannot_create_invoice(self, customer_client):
        response = customer_client.post('/invoices', json={'customer_id': 1, 'details': []})
        assert response.status_code == 403

    def test_customer_cannot_confirm_payment(self, customer_client, sample_invoice):
        response = customer_client.patch(f'/invoices/{sample_invoice.id}/confirm-payment', json={'payment_method': 'CASH'})
        assert response.status_code == 403

    def test_customer_cannot_access_reception_appointments(self, customer_client):
        response = customer_client.get('/reception/appointments')
        assert response.status_code == 403


# =========================================================================
# 2. NHÂN VIÊN (STAFF) CỐ TÌNH TRUY CẬP ROUTE QUẢN TRỊ/LỄ TÂN -> 403 FORBIDDEN
# =========================================================================
class TestStaffAccessRestrictions:

    def test_staff_cannot_access_admin_dashboard(self, staff_client):
        response = staff_client.get('/admin')
        assert response.status_code == 403

    def test_staff_cannot_access_admin_services(self, staff_client):
        response = staff_client.get('/admin/services')
        assert response.status_code == 403

    def test_staff_cannot_create_staff_user(self, staff_client):
        response = staff_client.post('/users', data={'full_name': 'Hack Staff'})
        assert response.status_code == 403

    def test_staff_cannot_access_revenue_reports(self, staff_client):
        response = staff_client.get('/admin/reports/revenue')
        assert response.status_code == 403

    def test_staff_cannot_confirm_invoice_payment(self, staff_client, sample_invoice):
        """Duyệt thanh toán là việc của Lễ tân/Admin, Staff không có quyền duyệt"""
        response = staff_client.patch(f'/invoices/{sample_invoice.id}/confirm-payment', json={'payment_method': 'CASH'})
        assert response.status_code == 403

    def test_staff_cannot_access_reception_invoices(self, staff_client):
        response = staff_client.get('/reception/invoices')
        assert response.status_code == 403


# =========================================================================
# 3. LỄ TÂN (RECEPTIONIST) CỐ TÌNH TRUY CẬP ROUTE QUẢN TRỊ/STAFF -> 403 FORBIDDEN
# =========================================================================
class TestReceptionistAccessRestrictions:

    def test_receptionist_cannot_access_admin_dashboard(self, receptionist_client):
        response = receptionist_client.get('/admin')
        assert response.status_code == 403

    def test_receptionist_cannot_access_admin_products(self, receptionist_client):
        response = receptionist_client.get('/admin/products')
        assert response.status_code == 403

    def test_receptionist_cannot_import_stock(self, receptionist_client, sample_product):
        response = receptionist_client.post(f'/admin/products/{sample_product.id}/import', data={'quantity': 10})
        assert response.status_code == 403

    def test_receptionist_cannot_export_revenue_excel(self, receptionist_client):
        response = receptionist_client.get('/admin/reports/revenue/export')
        assert response.status_code == 403

    def test_receptionist_cannot_access_staff_create_invoice_view(self, receptionist_client):
        """Trang lập đơn nháp là việc của Staff, Lễ tân chỉ duyệt đơn nháp tại quầy"""
        response = receptionist_client.get('/staff/create-invoice')
        assert response.status_code == 403


# =========================================================================
# 4. CHUYỂN HƯỚNG BẮT BỘC KHI CHƯA ĐĂNG NHẬP (GUEST / ANONYMOUS -> 302 REDIRECT)
# =========================================================================
class TestUnauthenticatedAccessRestrictions:

    @pytest.mark.parametrize("protected_url", [
        '/booking',
        '/users/me',
        '/appointments/me',
        '/staff/appointments',
        '/staff/create-invoice',
        '/reception/appointments',
        '/reception/invoices',
        '/admin',
        '/admin/services',
        '/admin/products',
        '/admin/users',
        '/admin/reports/revenue'
    ])
    def test_unauthenticated_access_redirects_to_login(self, client, protected_url):
        """Khách chưa đăng nhập vào bất kỳ trang bảo mật nào -> Đều phải bị Redirect sang /login (302)"""
        response = client.get(protected_url)
        assert response.status_code == 302
        assert '/login' in response.location