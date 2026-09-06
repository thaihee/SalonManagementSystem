class ValidationError(Exception):
    # Lỗi do người dùng nhập sai định dạng hoặc dữ liệu không hợp lệ -> HTTP 400
    pass

class DuplicateError(Exception):
    # Lỗi do bị trùng dữ liệu -> HTTP 409 Conflict
    pass

class NotFoundError(Exception):
    # Lỗi do không tìm thấy dữ liệu được yêu cầu -> HTTP 404
    pass