# Salon Management System

Hệ thống quản lý salon tóc/spa toàn diện, hỗ trợ đặt lịch hẹn trực tuyến, quản lý dịch vụ - sản phẩm - tồn kho, và xử lý giao dịch thanh toán, giúp salon vận hành chuyên nghiệp và giảm thiểu sai sót từ quy trình thủ công.

## Tính năng nổi bật

**Dành cho khách hàng**
- Đăng ký tài khoản, đặt lịch hẹn trực tuyến theo khung giờ trống thực tế
- Chỉnh sửa hoặc hủy lịch hẹn linh hoạt
- Xem lại lịch sử sử dụng dịch vụ

**Dành cho nhân viên**
- Xem lịch làm việc và lịch hẹn được phân công
- Lập hóa đơn và ghi nhận thanh toán nhanh chóng

**Dành cho quản lý**
- Quản lý danh mục dịch vụ và sản phẩm
- Theo dõi và cảnh báo tồn kho tự động
- Quản lý thông tin nhân viên
- Xem báo cáo doanh thu theo thời gian thực

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Backend | Python (Flask) |
| Database | MySQL |
| Frontend | HTML/CSS |
| Kiểm thử tự động | Pytest, Playwright, Postman |
| Kiểm thử bảo mật | OWASP ZAP |
| CI/CD | GitHub Actions |

## Cài đặt & chạy dự án

\`\`\`bash
# Clone repository
git clone https://github.com/thaihee/SalonManagementSystem.git
cd SalonManagementSystem

# Tạo virtual environment
python -m venv venv
venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt

# Tạo database
# CREATE DATABASE salondb CHARACTER SET utf8mb4;

# Chạy ứng dụng
python app/index.py
\`\`\`

Truy cập ứng dụng tại `http://127.0.0.1:5000`

## Kiểm thử

Dự án được kiểm thử toàn diện ở nhiều tầng: kiểm thử đơn vị (unit test), kiểm thử API, kiểm thử giao diện tự động (Playwright), và kiểm thử bảo mật (OWASP ZAP) cho các lỗ hổng phổ biến như SQL Injection, XSS, CSRF.

\`\`\`bash
# Chạy unit test
pytest app/test/
\`\`\`
