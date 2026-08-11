class ValidationError(Exception):
    # Lỗi do người dùng nhập sai định dạng hoặc dữ liệu không hợp lệ -> HTTP 400
    pass

class DuplicateError(Exception):
    # Lỗi do bị trùng dữ liệu (username, email...) -> HTTP 409 Conflict
    pass

class NotFoundError(Exception):
    # Lỗi do không tìm thấy dữ liệu được yêu cầu (user, dịch vụ, lịch hẹn...) -> HTTP 404
    pass