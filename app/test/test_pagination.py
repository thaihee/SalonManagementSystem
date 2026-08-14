import pytest
from app import dao


# =========================================================================
# TEST SUITE: Phân trang & Tìm kiếm - Dịch vụ (Service)
# =========================================================================

def test_load_services_pagination(app):
    """Phân trang danh sách dịch vụ đúng số lượng theo từng trang"""
    for i in range(1, 6):  # tạo 5 dịch vụ
        dao.add_service(name=f"Dịch vụ số {i}", price=100000, duration=30)

    page1 = dao.load_services(page=1, page_size=2)
    page2 = dao.load_services(page=2, page_size=2)
    page3 = dao.load_services(page=3, page_size=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1

    # Không trùng lặp giữa các trang
    all_ids = [s.id for s in page1] + [s.id for s in page2] + [s.id for s in page3]
    assert len(all_ids) == len(set(all_ids)) == 5


def test_load_services_search_keyword(app):
    """Tìm kiếm dịch vụ theo từ khóa (kw) trong tên"""
    dao.add_service(name="Cắt tóc nam", price=100000, duration=30)
    dao.add_service(name="Cắt tóc nữ", price=150000, duration=45)
    dao.add_service(name="Uốn tóc", price=300000, duration=90)

    result = dao.load_services(kw="Cắt tóc", page=1, page_size=10)
    names = [s.service_name for s in result]

    assert len(result) == 2
    assert "Cắt tóc nam" in names
    assert "Cắt tóc nữ" in names
    assert "Uốn tóc" not in names


def test_load_services_excludes_inactive(app):
    """Danh sách dịch vụ không hiển thị dịch vụ đã bị soft-delete"""
    s1 = dao.add_service(name="Dịch vụ còn hoạt động", price=100000, duration=30)
    s2 = dao.add_service(name="Dịch vụ đã xóa", price=100000, duration=30)
    dao.delete_service(s2.id)

    result = dao.load_services(page=1, page_size=10)
    names = [s.service_name for s in result]

    assert "Dịch vụ còn hoạt động" in names
    assert "Dịch vụ đã xóa" not in names


def test_count_services(app):
    """Đếm tổng số dịch vụ active"""
    for i in range(1, 4):
        dao.add_service(name=f"Đếm dịch vụ {i}", price=100000, duration=30)

    assert dao.count_services() == 3


def test_count_services_with_keyword(app):
    """Đếm số dịch vụ khớp từ khóa tìm kiếm"""
    dao.add_service(name="Massage mặt", price=100000, duration=30)
    dao.add_service(name="Massage lưng", price=120000, duration=40)
    dao.add_service(name="Nhuộm tóc", price=200000, duration=60)

    assert dao.count_services(kw="Massage") == 2


def test_count_services_excludes_inactive(app):
    """Đếm dịch vụ không tính dịch vụ đã bị soft-delete"""
    s1 = dao.add_service(name="Dịch vụ A", price=100000, duration=30)
    s2 = dao.add_service(name="Dịch vụ B", price=100000, duration=30)
    dao.delete_service(s2.id)

    assert dao.count_services() == 1


# =========================================================================
# TEST SUITE: Phân trang & Tìm kiếm - Sản phẩm (Product)
# =========================================================================

def test_load_products_pagination(app):
    """Phân trang danh sách sản phẩm đúng số lượng theo từng trang (dùng app.config['PAGE_SIZE'])"""
    app.config['PAGE_SIZE'] = 2

    for i in range(1, 6):  # tạo 5 sản phẩm
        dao.add_product(name=f"Sản phẩm số {i}", price=100000, stock_quantity=10, min_stock_level=5)

    page1 = dao.load_products(page=1)
    page2 = dao.load_products(page=2)
    page3 = dao.load_products(page=3)

    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1

    all_ids = [p.id for p in page1] + [p.id for p in page2] + [p.id for p in page3]
    assert len(all_ids) == len(set(all_ids)) == 5


def test_load_products_no_page_returns_all(app):
    """Không truyền page -> trả về toàn bộ sản phẩm active, không giới hạn"""
    app.config['PAGE_SIZE'] = 2  # cố tình để nhỏ để chắc chắn không giới hạn nếu page=None

    for i in range(1, 6):
        dao.add_product(name=f"SP không phân trang {i}", price=100000, stock_quantity=10, min_stock_level=5)

    result = dao.load_products()
    assert len(result) == 5


def test_load_products_search_keyword(app):
    """Tìm kiếm sản phẩm theo từ khóa (kw) trong tên"""
    dao.add_product(name="Dầu gội thảo dược", price=100000, stock_quantity=10, min_stock_level=5)
    dao.add_product(name="Dầu xả thảo dược", price=100000, stock_quantity=10, min_stock_level=5)
    dao.add_product(name="Sáp vuốt tóc", price=90000, stock_quantity=10, min_stock_level=5)

    result = dao.load_products(kw="thảo dược")
    names = [p.product_name for p in result]

    assert len(result) == 2
    assert "Dầu gội thảo dược" in names
    assert "Dầu xả thảo dược" in names
    assert "Sáp vuốt tóc" not in names


def test_count_products(app):
    """Đếm tổng số sản phẩm active"""
    for i in range(1, 4):
        dao.add_product(name=f"Đếm sản phẩm {i}", price=100000, stock_quantity=10, min_stock_level=5)

    assert dao.count_products() == 3


def test_count_products_with_keyword(app):
    """Đếm số sản phẩm khớp từ khóa tìm kiếm"""
    dao.add_product(name="Gel tạo kiểu tóc", price=70000, stock_quantity=10, min_stock_level=5)
    dao.add_product(name="Gel vuốt tóc bóng", price=80000, stock_quantity=10, min_stock_level=5)
    dao.add_product(name="Dầu gội", price=100000, stock_quantity=10, min_stock_level=5)

    assert dao.count_products(kw="Gel") == 2


def test_count_products_excludes_inactive(app):
    """Đếm sản phẩm không tính sản phẩm đã bị soft-delete"""
    p1 = dao.add_product(name="SP còn 1", price=100000, stock_quantity=10, min_stock_level=5)
    p2 = dao.add_product(name="SP còn 2", price=100000, stock_quantity=10, min_stock_level=5)
    dao.delete_product(p2.id)

    assert dao.count_products() == 1