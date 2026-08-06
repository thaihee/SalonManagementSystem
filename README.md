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

## Cài đặt & chạy dự án

# Clone repository
git clone https://github.com/thaihee/SalonManagementSystem.git
cd SalonManagementSystem

# Tạo virtual environment
python -m venv venv
venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt

# Tạo database
# CREATE DATABASE salon_db CHARACTER SET utf8mb4;

# Chạy ứng dụng
python app/index.py

Truy cập ứng dụng tại `http://127.0.0.1:5000`

## Kiểm thử

Dự án được đảm bảo chất lượng qua nhiều tầng kiểm thử, kết hợp cả kiểm thử tự động và thủ công.

### Unit Test — Pytest

Kiểm tra logic nghiệp vụ ở tầng dữ liệu và xử lý (tính tiền hóa đơn, kiểm tra khung giờ trống, trừ tồn kho...), chạy tự động mỗi khi có thay đổi code thông qua CI/CD (GitHub Actions).

pytest rapp/test/

Ví dụ 1 test case:
def test_tinh_tong_tien_hoa_don():
    tong = tinh_tong_tien(dich_vu_gia=200000, san_pham_gia=50000, khuyen_mai=10)
    assert tong == 225000

### API Test — Postman

Kiểm thử trực tiếp các endpoint (đặt lịch, tạo hóa đơn, đăng nhập...) độc lập với giao diện, đảm bảo API trả đúng dữ liệu, đúng mã lỗi (400, 401, 404...) trong các tình huống hợp lệ và không hợp lệ.

Ví dụ: gửi request `POST /api/lichhen` với dữ liệu khung giờ đã có người đặt → kỳ vọng phản hồi `409 Conflict` kèm thông báo lỗi rõ ràng.

Collection Postman được lưu tại `FileTestCase/postman/`.

### UI Test tự động — Playwright

Mô phỏng thao tác thật của người dùng trên trình duyệt để kiểm tra toàn bộ luồng từ giao diện đến kết quả cuối, đặc biệt cho 2 luồng quan trọng nhất: **đặt lịch hẹn** và **thanh toán**.

def test_dat_lich_thanh_cong(page):
    page.goto("http://127.0.0.1:5000/dat-lich")
    page.select_option("#service-select", "Cắt tóc")
    page.fill("#appointment-date", "2026-08-20")
    page.click("#confirm-btn")
    assert page.locator("text=Đặt lịch thành công").is_visible()

### Kiểm thử bảo mật — OWASP ZAP

Quét tự động toàn hệ thống để phát hiện các lỗ hổng bảo mật phổ biến trên các form nhạy cảm (đăng nhập, đặt lịch, thanh toán):

- **SQL Injection** — kiểm tra hệ thống có chặn được các payload như `' OR '1'='1` khi nhập vào form đăng nhập/tìm kiếm
- **XSS (Cross-Site Scripting)** — kiểm tra dữ liệu nhập từ người dùng (VD ghi chú lịch hẹn) có bị escape đúng trước khi hiển thị lại hay không
- **CSRF (Cross-Site Request Forgery)** — kiểm tra các form thay đổi dữ liệu (đặt lịch, thanh toán) có yêu cầu CSRF token hợp lệ hay không

Kết quả quét được xuất báo cáo và lưu tại `FileTestCase/zap-reports/`.

### Quản lý test case & lỗi — Jira

Toàn bộ test case, tiến độ thực thi kiểm thử, và lỗi phát hiện được theo dõi tập trung trên Jira, đảm bảo mọi lỗi đều được ghi nhận, phân loại mức độ nghiêm trọng và xác nhận đã khắc phục trước khi phát hành.
