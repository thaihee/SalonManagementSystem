import uuid

import pytest
from datetime import datetime, date, timedelta
from app import dao
from app.models import UserRole, InvoiceStatus


# =========================================================================
# 1. BẢO MẬT PHÂN QUYỀN RBAC (NON-ADMIN BLOCKING)
# =========================================================================
class TestAdminRBACAccess:

    def test_admin_dashboard_unauthenticated_redirects(self, client):
        """Khách chưa đăng nhập vào /admin -> Redirect sang /login"""
        response = client.get('/admin')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_admin_dashboard_staff_forbidden(self, staff_client):
        """Nhân viên (STAFF) truy cập trang Admin -> 403 Forbidden"""
        response = staff_client.get('/admin')
        assert response.status_code == 403

    def test_admin_dashboard_customer_forbidden(self, customer_client):
        """Khách hàng (CUSTOMER) truy cập trang Admin -> 403 Forbidden"""
        response = customer_client.get('/admin')
        assert response.status_code == 403

    def test_admin_dashboard_success(self, admin_client):
        """Admin truy cập /admin -> 200 OK"""
        response = admin_client.get('/admin')
        assert response.status_code == 200


# =========================================================================
# 2. QUẢN LÝ NHÂN SỰ & TÀI KHOẢN (/admin/users & /users)
# =========================================================================
class TestAdminUserManagementRoutes:

    def test_list_users_success(self, admin_client, staff_user):
        """Admin xem danh sách người dùng -> 200 OK"""
        response = admin_client.get('/admin/users')
        assert response.status_code == 200

    def test_get_user_detail_success(self, admin_client, staff_user):
        """Admin xem chi tiết 1 user qua GET /users/<id> -> 200 OK kèm JSON user"""
        response = admin_client.get(f'/users/{staff_user.id}')
        assert response.status_code == 200
        assert response.json['username'] == staff_user.username

    def test_get_user_detail_not_found(self, admin_client):
        """Xem user không tồn tại -> 404 Not Found"""
        response = admin_client.get('/users/99999')
        assert response.status_code == 404

    def test_create_staff_success(self, admin_client):
        """Admin tạo nhân viên STAFF thành công -> 201 Created"""
        suffix = uuid.uuid4().hex[:8]

        response = admin_client.post('/users', data={
            'full_name': 'Nhân Viên Mới',
            'username': f'newstaff{suffix}',
            'password': 'Password123',
            'phone': f"09{uuid.uuid4().int % 100000000:08d}",
            'email': f'newstaff{suffix}@gmail.com',
            'role': 'STAFF'
        })

        assert response.status_code == 201
        assert response.json['success'] is True

    def test_create_staff_invalid_role_raises_400(self, admin_client):
        suffix = uuid.uuid4().hex[:8]

        response = admin_client.post('/users', data={
            'full_name': 'Admin Mới',
            'username': f'newadmin{suffix}',
            'password': 'Password123',
            'phone': f"09{uuid.uuid4().int % 100000000:08d}",
            'email': f'newadmin{suffix}@gmail.com',
            'role': 'ADMIN'
        })

        assert response.status_code == 400
        assert (
                "Chỉ được tạo tài khoản với role STAFF hoặc RECEPTIONIST"
                in response.json['error']
        )

    def test_toggle_user_active_success(self, admin_client, staff_user):
        """Khóa / Mở khóa tài khoản người dùng -> 200 OK"""
        response = admin_client.patch(f'/users/{staff_user.id}/toggle-active')
        assert response.status_code == 200
        assert response.json['success'] is True


# =========================================================================
# 3. QUẢN LÝ DỊCH VỤ & ĐỊNH MỨC SẢN PHẨM (/admin/services)
# =========================================================================
class TestAdminServicesRoutes:

    def test_list_services_success(self, admin_client, sample_service):
        """Xem danh sách dịch vụ Admin -> 200 OK"""
        response = admin_client.get('/admin/services')
        assert response.status_code == 200

    def test_create_service_success(self, admin_client):
        """Tạo dịch vụ mới -> 201 Created"""
        suffix = uuid.uuid4().hex[:8]

        response = admin_client.post('/admin/services', data={
            'service_name': f'Uốn Tóc Test {suffix}',
            'price': 300000,
            'duration_minutes': 60,
            'description': 'Dịch vụ dùng cho integration test'
        })

        assert response.status_code == 201
        assert response.json['success'] is True

    def test_update_service_success(self, admin_client, sample_service):
        """Cập nhật dịch vụ -> 200 OK"""
        suffix = uuid.uuid4().hex[:8]

        response = admin_client.put(
            f'/admin/services/{sample_service.id}',
            json={
                'service_name': f'Service Updated {suffix}',
                'price': 120000,
                'duration_minutes': 35,
                'description': 'Mô tả cập nhật'
            }
        )

        assert response.status_code == 200
        assert response.json['success'] is True

    def test_create_service_product_mapping(self, admin_client, sample_service, sample_product):
        """Gán định mức sản phẩm cho dịch vụ -> 201 Created"""
        response = admin_client.post('/admin/service-products', data={
            'service_id': sample_service.id,
            'product_id': sample_product.id,
            'default_quantity': 2
        })
        assert response.status_code == 201
        assert response.json['success'] is True


# =========================================================================
# 4. QUẢN LÝ SẢN PHẨM & XUẤT/NHẬP KHO (/admin/products)
# =========================================================================
class TestAdminProductAndStockRoutes:

    def test_list_products_success(self, admin_client, sample_product):
        """Xem danh sách sản phẩm -> 200 OK"""
        response = admin_client.get('/admin/products')
        assert response.status_code == 200

    def test_import_stock_success(self, admin_client, sample_product):
        """Nhập kho sản phẩm -> 200 OK"""
        response = admin_client.post(f'/admin/products/{sample_product.id}/import', data={
            'quantity': 20
        })
        assert response.status_code == 200
        assert response.json['stock_quantity'] == 70  # 50 + 20

    def test_export_stock_success(self, admin_client, sample_product):
        """Xuất kho sản phẩm -> 200 OK"""
        response = admin_client.post(f'/admin/products/{sample_product.id}/export', data={
            'quantity': 10
        })
        assert response.status_code == 200
        assert response.json['stock_quantity'] == 40  # 50 - 10

    def test_get_low_stock_products(self, admin_client, sample_product):
        """Lấy danh sách cảnh báo tồn kho thấp -> 200 OK"""
        response = admin_client.get('/admin/products/low-stock')
        assert response.status_code == 200
        assert isinstance(response.json, list)


# =========================================================================
# 5. QUẢN LÝ KHUYẾN MÃI (/admin/promotions)
# =========================================================================
class TestAdminPromotionRoutes:

    def test_list_promotions_success(self, admin_client, sample_promotion):
        """Xem danh sách mã khuyến mãi -> 200 OK"""
        response = admin_client.get('/admin/promotions')
        assert response.status_code == 200

    def test_create_promotion_success(self, admin_client):
        """Tạo khuyến mãi mới -> 201 Created"""
        today = date.today()
        suffix = uuid.uuid4().hex[:8].upper()

        response = admin_client.post('/admin/promotions', json={
            'promo_code': f'SALE{suffix}',
            'promo_type': 'PERCENT',
            'value': 15,
            'start_date': today.strftime('%Y-%m-%d'),
            'end_date': (
                    today + timedelta(days=10)
            ).strftime('%Y-%m-%d')
        })

        assert response.status_code == 201
        assert response.json['success'] is True


# =========================================================================
# 6. XỬ LÝ HÓA ĐƠN NHÁP & BÁO CÁO DOANH THU EXCEL
# =========================================================================
class TestAdminInvoiceDraftAndReports:

    def test_get_invoice_draft_detail_success(self, admin_client, sample_invoice):
        """Admin lấy thông tin chi tiết hóa đơn nháp để sửa -> 200 OK"""
        response = admin_client.get(f'/admin/invoices/{sample_invoice.id}/draft-detail')
        assert response.status_code == 200
        assert response.json['success'] is True
        assert 'details' in response.json['invoice']

    def test_cancel_invoice_draft_success(self, admin_client, sample_invoice):
        """Admin hủy hóa đơn nháp -> 200 OK"""
        response = admin_client.patch(f'/admin/invoices/{sample_invoice.id}/cancel')
        assert response.status_code == 200
        assert response.json['success'] is True

    def test_revenue_report_view_success(self, admin_client):
        """Xem báo cáo doanh thu -> 200 OK"""
        response = admin_client.get('/admin/reports/revenue?period_type=day')
        assert response.status_code == 200

    def test_export_revenue_report_excel(self, admin_client, sample_invoice, receptionist_user):
        """Xuất file Excel Báo cáo doanh thu -> 200 OK kèm File Binary Download"""
        # Xác nhận 1 hóa đơn PAID để có dữ liệu xuất Excel
        dao.confirm_invoice_payment(sample_invoice.id, receptionist_user.id, payment_method="CASH")

        today_str = date.today().strftime('%Y-%m-%d')
        response = admin_client.get(f'/admin/reports/revenue/export?from_date={today_str}&to_date={today_str}')

        assert response.status_code == 200
        assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert response.headers['Content-Disposition'].startswith('attachment;')