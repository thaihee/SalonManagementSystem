import base64
import uuid
from datetime import date, timedelta, datetime

import pytest
from playwright.sync_api import Page, expect, Browser
from app import app, db
from app.models import Appointment, User, Service, AppointmentStatus, ServiceProduct, Invoice, InvoiceDetail, Product, \
    Promotion, PaymentMethod, InvoiceStatus, InvoiceItemType
from test.e2e.utils.pagination import find_row_across_pages
from pathlib import Path


PASSWORD = "123456"

# =========================================================
# E2E REPORT - SCREENSHOT KHI TEST FAIL
# =========================================================

SCREENSHOT_DIR = Path("reports/screenshots")

def pytest_html_report_title(report):
    report.title = (
        "Minimalist Muse — E2E Automation Test Report"
    )

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    # Chỉ xử lý khi phần test chính bị FAIL
    if report.when != "call" or not report.failed:
        return

    SCREENSHOT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Tìm Playwright Page mà test đang sử dụng
    page_fixture_names = [
        "admin_page",
        "receptionist_page",
        "staff_page",
        "staff2_page",
        "customer_page",
    ]

    page = None

    for fixture_name in page_fixture_names:
        candidate = item.funcargs.get(
            fixture_name
        )

        if isinstance(candidate, Page):
            page = candidate
            break

    if page is None:
        return

    # Tạo tên file an toàn
    safe_name = (
        item.nodeid
        .replace("/", "_")
        .replace("\\", "_")
        .replace("::", "__")
        .replace("[", "_")
        .replace("]", "")
    )

    screenshot_path = (
        SCREENSHOT_DIR /
        f"{safe_name}.png"
    )

    try:
        # ==========================================
        # 1. Chụp screenshot
        # ==========================================

        page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        print(
            f"\n[SCREENSHOT] Test FAIL - đã lưu: "
            f"{screenshot_path}"
        )

        # ==========================================
        # 2. Nhúng screenshot vào HTML report
        # ==========================================

        pytest_html = (
            item.config.pluginmanager.getplugin(
                "html"
            )
        )

        if pytest_html is not None:
            extras = getattr(
                report,
                "extras",
                []
            )

            with open(
                    screenshot_path,
                    "rb"
            ) as image_file:
                image_base64 = (
                    base64.b64encode(
                        image_file.read()
                    ).decode("utf-8")
                )

            extras.append(
                pytest_html.extras.html(
                    f"""
                    <div style="margin-top: 10px;">
                        <div style="
                            font-weight: 600;
                            margin-bottom: 8px;
                        ">
                            Screenshot khi test FAIL
                        </div>

                        <img
                            src="data:image/png;base64,{image_base64}"
                            style="
                                max-width: 900px;
                                width: 100%;
                                border: 1px solid #ddd;
                                border-radius: 8px;
                            "
                        />
                    </div>
                    """
                )
            )

            report.extras = extras

    except Exception as exc:
        print(
            f"\n[SCREENSHOT] Không thể "
            f"chụp/đính ảnh: {exc}"
        )


# @pytest.fixture(scope="session")
# def browser_type_launch_args(browser_type_launch_args):
#     return {
#         **browser_type_launch_args,
#         "slow_mo": 700,
#     }


def login(page, base_url, username):
    page.goto(f"{base_url}/login")

    page.locator("#username").fill(username)
    page.locator("#password").fill(PASSWORD)
    page.locator("button[type='submit']").click()


@pytest.fixture
def customer_page(browser: Browser, base_url):
    context = browser.new_context()
    page = context.new_page()

    login(page, base_url, "customer1")

    yield page

    context.close()


@pytest.fixture
def staff_page(browser: Browser, base_url):
    context = browser.new_context()
    page = context.new_page()

    login(page, base_url, "staff1")

    yield page

    context.close()


@pytest.fixture
def receptionist_page(browser: Browser, base_url):
    context = browser.new_context()
    page = context.new_page()

    login(page, base_url, "letan1")

    yield page

    context.close()


@pytest.fixture
def admin_page(browser: Browser, base_url):
    context = browser.new_context()
    page = context.new_page()

    login(page, base_url, "admin")

    yield page

    context.close()


@pytest.fixture
def staff2_page(browser: Browser, base_url):
    context = browser.new_context()
    page = context.new_page()

    login(page, base_url, "staff2")

    yield page

    context.close()


@pytest.fixture
def customer_booking(customer_page, base_url):
    # =========================================================
    # SETUP - TẠO APPOINTMENT TEST QUA UI
    # =========================================================

    customer_page.goto(f"{base_url}/booking")

    booking_date = (
        date.today() + timedelta(days=2)
    ).strftime("%Y-%m-%d")

    # Chọn ngày
    customer_page.locator("#date").fill(booking_date)

    # Chờ danh sách giờ trống
    first_slot = customer_page.locator(".slot-btn").first
    expect(first_slot).to_be_visible(timeout=10000)

    booking_time = first_slot.get_attribute("data-time")

    # Chọn giờ
    first_slot.click()

    # Ghi chú để dễ nhận diện dữ liệu automation
    customer_page.locator("#note").fill(
        "E2E_AUTOMATION_BOOKING"
    )

    # Bắt response POST /appointments
    with customer_page.expect_response(
        lambda response:
            response.url.endswith("/appointments")
            and response.request.method == "POST"
    ) as response_info:

        customer_page.locator(
            "#btn-submit-booking"
        ).click()

    create_response = response_info.value

    # Appointment phải được tạo thành công
    assert create_response.status == 201


    body = create_response.json()
    body = create_response.json()

    assert body["appointment"]["id"] is not None

    assert body["appointment"]["staff_id"] is not None, (
        "Hệ thống không tự động gán stylist "
        "khi khách chọn 'Salon tự xếp'"
    )

    booking = {
        "id": body["appointment"]["id"],
        "date": booking_date,
        "time": booking_time,
        "service_id": body["appointment"]["service_id"],
        "staff_id": body["appointment"]["staff_id"],
    }

    print(
        f"\n[SETUP] Đã tạo appointment test #{booking['id']}"
    )

    # =========================================================
    # TEST CHẠY Ở ĐÂY
    # =========================================================

    yield booking

    # =========================================================
    # TEARDOWN - HARD DELETE ĐÚNG RECORD TEST VỪA TẠO
    # =========================================================

    appointment_id = booking["id"]

    with app.app_context():
        appointment = db.session.get(
            Appointment,
            appointment_id
        )

        if appointment:
            db.session.delete(appointment)
            db.session.commit()

            print(
                f"\n[TEARDOWN] Đã xóa appointment test "
                f"#{appointment_id} khỏi database"
            )

        else:
            print(
                f"\n[TEARDOWN] Appointment #{appointment_id} "
                f"không còn tồn tại trong database"
            )

@pytest.fixture
def customer_booking_within_2_hours():
    with app.app_context():
        customer = User.query.filter_by(username="customer1").first()
        staff = User.query.filter_by(username="staff1").first()
        service = Service.query.filter_by(
            service_name="Cắt tóc nam"
        ).first()

        appointment = Appointment(
            customer_id=customer.id,
            staff_id=staff.id,
            service_id=service.id,
            appointment_date=datetime.now() + timedelta(hours=1),
            status=AppointmentStatus.CONFIRMED,
            note="E2E_WITHIN_2_HOURS"
        )

        db.session.add(appointment)
        db.session.commit()

        appointment_id = appointment.id

    yield {
        "id": appointment_id
    }

    with app.app_context():
        appointment = db.session.get(
            Appointment,
            appointment_id
        )

        if appointment:
            db.session.delete(appointment)
            db.session.commit()


@pytest.fixture
def customer2_booking():
    with app.app_context():
        customer = User.query.filter_by(
            username="customer2"
        ).first()

        staff = User.query.filter_by(
            username="staff2"
        ).first()

        service = Service.query.filter_by(
            service_name="Cắt tóc nam"
        ).first()

        appointment = Appointment(
            customer_id=customer.id,
            staff_id=staff.id,
            service_id=service.id,
            appointment_date=datetime.now() + timedelta(days=3),
            status=AppointmentStatus.CONFIRMED,
            note="E2E_CUSTOMER2_PRIVATE_BOOKING"
        )

        db.session.add(appointment)
        db.session.commit()

        appointment_id = appointment.id

    yield {
        "id": appointment_id
    }

    with app.app_context():
        appointment = db.session.get(
            Appointment,
            appointment_id
        )

        if appointment:
            db.session.delete(appointment)
            db.session.commit()


#====================STAFF====================

@pytest.fixture
def staff1_booking(customer_page, base_url):
    # =========================
    # SETUP
    # =========================
    customer_page.goto(f"{base_url}/booking")

    booking_date = (
        date.today() + timedelta(days=2)
    ).strftime("%Y-%m-%d")

    # Chọn cụ thể staff1 - Trần Thị Hằng
    customer_page.locator("#staff_id").select_option(
        label="Trần Thị Hằng"
    )

    customer_page.locator("#date").fill(booking_date)

    first_slot = customer_page.locator(".slot-btn").first
    expect(first_slot).to_be_visible(timeout=10000)

    booking_time = first_slot.get_attribute("data-time")
    first_slot.click()

    customer_page.locator("#note").fill(
        "E2E_STAFF_ASSIGNED_BOOKING"
    )

    with customer_page.expect_response(
        lambda response:
            response.url.endswith("/appointments")
            and response.request.method == "POST"
    ) as response_info:

        customer_page.locator(
            "#btn-submit-booking"
        ).click()

    create_response = response_info.value

    assert create_response.status == 201

    body = create_response.json()

    assert body["appointment"]["staff_id"] is not None

    booking = {
        "id": body["appointment"]["id"],
        "date": booking_date,
        "time": booking_time,
        "service_id": body["appointment"]["service_id"],
        "staff_id": body["appointment"]["staff_id"],
    }

    print(
        f"\n[SETUP] Đã tạo appointment #{booking['id']} "
        f"cho staff1"
    )

    yield booking

    # =========================
    # TEARDOWN
    # =========================
    appointment_id = booking["id"]

    with app.app_context():
        appointment = db.session.get(
            Appointment,
            appointment_id
        )

        if appointment:
            db.session.delete(appointment)
            db.session.commit()

            print(
                f"\n[TEARDOWN] Đã xóa appointment "
                f"#{appointment_id}"
            )

@pytest.fixture
def service_with_products():
    with app.app_context():
        service = (
            Service.query
            .join(ServiceProduct)
            .filter(Service.active.is_(True))
            .first()
        )

        assert service is not None, (
            "Không có service nào được cấu hình ServiceProduct"
        )

        return service.id


@pytest.fixture
def staff1_booking_with_products(customer_page, base_url):
    # =========================================================
    # SETUP
    # Tạo appointment cho staff1 với service CÓ ServiceProduct
    # =========================================================

    customer_page.goto(f"{base_url}/booking")

    booking_date = (
        date.today() + timedelta(days=2)
    ).strftime("%Y-%m-%d")

    # Chọn service chắc chắn có sản phẩm định mức
    # Seed hiện tại: "Gội đầu dưỡng sinh"
    service_card = customer_page.locator(
        '.service-select-card'
    ).filter(
        has=customer_page.get_by_text(
            "Gội đầu dưỡng sinh",
            exact=True
        )
    )

    expect(service_card).to_have_count(1)
    expect(service_card).to_be_visible()

    service_card.click()

    # Chọn staff1 cụ thể
    customer_page.locator("#staff_id").select_option(
        label="Trần Thị Hằng"
    )

    # Chọn ngày
    with customer_page.expect_response(
            lambda response:
            "/appointments/available-slots"
            in response.url
            and f"date={booking_date}"
            in response.url
            and response.request.method == "GET"
    ) as slots_response_info:

        customer_page.locator(
            "#date"
        ).fill(
            booking_date
        )

    slots_response = slots_response_info.value

    assert slots_response.status == 200

    slots_body = slots_response.json()

    assert len(
        slots_body["available_slots"]
    ) > 0, (
        f"Không có slot cho ngày {booking_date}"
    )

    first_slot = customer_page.locator(
        ".slot-btn"
    ).first

    expect(first_slot).to_be_visible(
        timeout=10000
    )

    booking_time = first_slot.get_attribute("data-time")

    first_slot.click()

    customer_page.locator("#note").fill(
        "E2E_STAFF_INVOICE_WITH_PRODUCTS"
    )

    # Tạo appointment
    with customer_page.expect_response(
        lambda response:
            response.url.endswith("/appointments")
            and response.request.method == "POST"
    ) as response_info:

        customer_page.locator(
            "#btn-submit-booking"
        ).click()

    create_response = response_info.value

    assert create_response.status == 201

    body = create_response.json()

    assert body["appointment"]["staff_id"] is not None

    booking = {
        "id": body["appointment"]["id"],
        "date": booking_date,
        "time": booking_time,
        "service_id": body["appointment"]["service_id"],
        "staff_id": body["appointment"]["staff_id"],
    }

    print(
        f"\n[SETUP] Đã tạo appointment #{booking['id']} "
        f"với service có sản phẩm định mức"
    )

    # =========================================================
    # TEST CHẠY
    # =========================================================

    yield booking

    # =========================================================
    # TEARDOWN
    # InvoiceDetail -> Invoice -> Appointment
    # =========================================================

    appointment_id = booking["id"]

    with app.app_context():

        invoice = Invoice.query.filter_by(
            appointment_id=appointment_id
        ).first()

        if invoice:
            invoice_id = invoice.id

            # Xóa toàn bộ detail trước
            InvoiceDetail.query.filter_by(
                invoice_id=invoice_id
            ).delete(
                synchronize_session=False
            )

            db.session.delete(invoice)

            print(
                f"\n[TEARDOWN] Đã xóa invoice #{invoice_id}"
            )

        appointment = db.session.get(
            Appointment,
            appointment_id
        )

        if appointment:
            db.session.delete(appointment)

            print(
                f"[TEARDOWN] Đã xóa appointment #{appointment_id}"
            )

        db.session.commit()


#====================RECEPTIONIST====================

@pytest.fixture
def reception_draft_invoice(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

    # ==========================================
    # SETUP: Staff tạo DRAFT qua UI
    # ==========================================

    staff_page.goto(
        f"{base_url}/staff/appointments?date={booking_date}"
    )

    row = find_row_across_pages(
        staff_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None

    row.get_by_role(
        "link",
        name="Tạo hóa đơn"
    ).click()

    with staff_page.expect_response(
        lambda response:
            response.url.endswith("/invoices")
            and response.request.method == "POST"
    ) as response_info:

        staff_page.locator(
            "#btnSubmitDraft"
        ).click()

    response = response_info.value

    assert response.status == 201

    body = response.json()

    invoice = {
        "id": body["invoice"]["id"],
        "appointment_id": appointment_id,
        "date": booking_date,
    }

    print(
        f"\n[SETUP] Đã tạo DRAFT invoice "
        f"#{invoice['id']} cho Receptionist"
    )

    yield invoice

    # Không cần xóa ở đây nếu
    # staff1_booking_with_products bên ngoài
    # đã cleanup InvoiceDetail -> Invoice -> Appointment.


#====================ADMIN====================

@pytest.fixture
def admin_test_service(admin_page, base_url):
    # =====================================================
    # SETUP - TẠO SERVICE QUA UI
    # =====================================================

    service_name = f"E2E_SERVICE_{uuid.uuid4().hex[:8]}"

    admin_page.goto(
        f"{base_url}/admin/services"
    )

    admin_page.get_by_role(
        "button",
        name="Thêm Dịch Vụ Mới"
    ).click()

    create_form = admin_page.locator(
        "#createServiceForm"
    )

    expect(create_form).to_be_visible()

    create_form.locator(
        '[name="service_name"]'
    ).fill(service_name)

    create_form.locator(
        '[name="price"]'
    ).fill("250000")

    create_form.locator(
        '[name="duration_minutes"]'
    ).fill("60")

    create_form.locator(
        '[name="description"]'
    ).fill(
        "Dịch vụ được tạo bởi Playwright E2E"
    )

    with admin_page.expect_response(
        lambda response:
            response.url.endswith("/admin/services")
            and response.request.method == "POST"
    ) as response_info:

        create_form.get_by_role(
            "button",
            name="Tạo Dịch Vụ"
        ).click()

    response = response_info.value

    assert response.status == 201

    body = response.json()

    assert body["success"] is True

    service_id = body["id"]

    service = {
        "id": service_id,
        "name": service_name,
        "price": 250000,
        "duration_minutes": 60,
        "description": "Dịch vụ được tạo bởi Playwright E2E",
    }

    print(
        f"\n[SETUP] Đã tạo service test "
        f"#{service_id} - {service_name}"
    )

    # =====================================================
    # TEST
    # =====================================================

    yield service

    # =====================================================
    # TEARDOWN
    # ServiceProduct -> Service
    # =====================================================

    with app.app_context():

        # 1. Xóa toàn bộ định mức liên quan service test
        ServiceProduct.query.filter_by(
            service_id=service_id
        ).delete(
            synchronize_session=False
        )

        # 2. Xóa chính Service
        service_record = db.session.get(
            Service,
            service_id
        )

        if service_record:
            db.session.delete(service_record)

        db.session.commit()

        print(
            f"\n[TEARDOWN] Đã xóa service test "
            f"#{service_id} và toàn bộ ServiceProduct liên quan"
        )


@pytest.fixture
def admin_test_product(admin_page, base_url):
    product_id = None

    # =====================================================
    # SETUP - TẠO PRODUCT QUA UI THẬT
    # =====================================================

    product_name = f"E2E_PRODUCT_{uuid.uuid4().hex[:8]}"

    admin_page.goto(
        f"{base_url}/admin/products"
    )

    # Mở form tạo sản phẩm
    admin_page.get_by_role(
        "button",
        name="Thêm Sản Phẩm Mới"
    ).click()

    create_form = admin_page.locator(
        "#createProductForm"
    )

    expect(create_form).to_be_visible()

    # Điền dữ liệu
    create_form.locator(
        '[name="product_name"]'
    ).fill(product_name)

    create_form.locator(
        '[name="unit"]'
    ).select_option("ML")

    create_form.locator(
        '[name="stock_quantity"]'
    ).fill("100")

    create_form.locator(
        '[name="min_stock_level"]'
    ).fill("20")

    # Submit thật qua UI
    with admin_page.expect_response(
        lambda response:
            response.url.endswith("/admin/products")
            and response.request.method == "POST"
    ) as response_info:

        create_form.get_by_role(
            "button",
            name="Lưu Sản Phẩm"
        ).click()

    response = response_info.value

    assert response.status == 201

    body = response.json()

    assert body["success"] is True

    product_id = body["id"]

    product = {
        "id": product_id,
        "name": product_name,
        "unit": "ML",
        "stock_quantity": 100,
        "min_stock_level": 20,
    }

    print(
        f"\n[SETUP] Đã tạo product test "
        f"#{product_id} - {product_name}"
    )

    # =====================================================
    # TEST
    # =====================================================

    yield product

    # =====================================================
    # TEARDOWN
    # ServiceProduct -> Product
    # =====================================================

    with app.app_context():

        # Nếu test định mức sau này có liên kết Product
        # với Service thì phải xóa FK này trước.
        ServiceProduct.query.filter_by(
            product_id=product_id
        ).delete(
            synchronize_session=False
        )

        product_record = db.session.get(
            Product,
            product_id
        )

        if product_record:
            db.session.delete(product_record)
            db.session.commit()

            print(
                f"\n[TEARDOWN] Đã xóa product test "
                f"#{product_id} khỏi database"
            )

        else:
            # Ví dụ test Delete Product đã tự xóa qua UI.
            db.session.commit()

            print(
                f"\n[TEARDOWN] Product test "
                f"#{product_id} đã được test xóa trước đó"
            )


@pytest.fixture
def admin_test_promotion(
    admin_page,
    base_url
):
    promotion_id = None

    promo_code = (
        f"E2E_{uuid.uuid4().hex[:8].upper()}"
    )

    start_date = date.today()
    end_date = start_date + timedelta(days=30)

    # ==========================================
    # SETUP - TẠO PROMOTION QUA UI
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/promotions"
    )

    admin_page.get_by_role(
        "button",
        name="Thêm Mã Mới"
    ).click()

    modal = admin_page.locator(
        "#promoModal"
    )

    expect(modal).to_be_visible()

    expect(
        modal.locator("#modalTitle")
    ).to_have_text(
        "Thêm Mã Khuyến Mãi Mới"
    )

    # Điền form
    modal.locator(
        "#promo_code"
    ).fill(promo_code)

    modal.locator(
        "#promo_type"
    ).select_option("PERCENT")

    modal.locator(
        "#value"
    ).fill("15")

    modal.locator(
        "#start_date"
    ).fill(
        start_date.isoformat()
    )

    modal.locator(
        "#end_date"
    ).fill(
        end_date.isoformat()
    )

    # Submit
    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                "/admin/promotions"
            )
            and response.request.method == "POST"
    ) as response_info:

        modal.locator(
            "#btnSubmitForm"
        ).click()

    response = response_info.value

    assert response.ok

    body = response.json()

    assert body["success"] is True

    promotion_id = body["id"]

    print(
        f"\n[SETUP] Đã tạo promotion test "
        f"#{promotion_id} - {promo_code}"
    )

    promotion = {
        "id": promotion_id,
        "code": promo_code,
        "type": "PERCENT",
        "value": 15,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    # ==========================================
    # TEST
    # ==========================================

    yield promotion

    # ==========================================
    # TEARDOWN
    # ==========================================

    with app.app_context():

        promotion_record = db.session.get(
            Promotion,
            promotion_id
        )

        if promotion_record:
            db.session.delete(
                promotion_record
            )

            db.session.commit()

            print(
                f"\n[TEARDOWN] Đã xóa "
                f"promotion test "
                f"#{promotion_id}"
            )

        else:
            db.session.commit()

            print(
                f"\n[TEARDOWN] Promotion test "
                f"#{promotion_id} đã không còn"
            )

@pytest.fixture
def admin_test_staff(
    admin_page,
    base_url
):
    unique = uuid.uuid4().hex[:8]

    full_name = f"E2E Stylist {unique}"
    username = f"e2estaff{unique}"
    password = "Password123"
    email = f"{username}@test.com"
    phone = f"09{uuid.uuid4().int % 100000000:08d}"

    user_id = None

    # ==========================================
    # SETUP - TẠO STAFF QUA UI
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/users"
    )

    admin_page.get_by_role(
        "button",
        name="Tạo Nhân Viên Mới"
    ).click()

    form = admin_page.locator(
        "#createStaffForm"
    )

    expect(form).to_be_visible()

    form.locator(
        '[name="full_name"]'
    ).fill(full_name)

    form.locator(
        '[name="username"]'
    ).fill(username)

    form.locator(
        '[name="password"]'
    ).fill(password)

    form.locator(
        '[name="role"]'
    ).select_option("STAFF")

    form.locator(
        '[name="phone"]'
    ).fill(phone)

    form.locator(
        '[name="email"]'
    ).fill(email)

    with admin_page.expect_response(
        lambda response:
            response.url.endswith("/users")
            and response.request.method == "POST"
    ) as response_info:

        form.get_by_role(
            "button",
            name="Tạo Tài Khoản"
        ).click()

    response = response_info.value

    assert response.status == 201

    body = response.json()

    assert body["success"] is True

    user_id = body["user"]["id"]

    print(
        f"\n[SETUP] Đã tạo Staff test "
        f"#{user_id} - {username}"
    )

    # ==========================================
    # TRẢ DATA CHO TEST
    # ==========================================

    yield {
        "id": user_id,
        "full_name": full_name,
        "username": username,
        "phone": phone,
        "email": email,
        "role": "STAFF",
    }

    # ==========================================
    # TEARDOWN
    # ==========================================

    with app.app_context():

        user = db.session.get(
            User,
            user_id
        )

        if user:
            db.session.delete(user)
            db.session.commit()

            print(
                f"\n[TEARDOWN] Đã xóa "
                f"Staff test #{user_id}"
            )
        else:
            db.session.rollback()

            print(
                f"\n[TEARDOWN] Staff test "
                f"#{user_id} đã không còn"
            )


@pytest.fixture
def paid_invoice_for_report():
    invoice_id = None

    # Chọn ngày riêng cho test report
    report_date = datetime(2026, 8, 20, 10, 30, 0)

    with app.app_context():

        customer = User.query.filter_by(
            username="customer1"
        ).first()

        staff = User.query.filter_by(
            username="staff1"
        ).first()

        receptionist = User.query.filter_by(
            username="letan1"
        ).first()

        assert customer is not None
        assert staff is not None
        assert receptionist is not None

        invoice = Invoice(
            invoice_date=report_date,
            total_amount=555000,
            status=InvoiceStatus.PAID,
            payment_method=PaymentMethod.CASH,
            customer_id=customer.id,
            staff_id=staff.id,
            receptionist_id=receptionist.id,
            appointment_id=None,
            promotion_id=None
        )

        db.session.add(invoice)
        db.session.commit()

        invoice_id = invoice.id

        print(
            f"\n[SETUP] Đã tạo PAID invoice "
            f"#{invoice_id} = 555000 đ "
            f"cho Revenue Report"
        )

    yield {
        "id": invoice_id,
        "date": report_date.date().isoformat(),
        "amount": 555000,
    }

    with app.app_context():

        invoice = db.session.get(
            Invoice,
            invoice_id
        )

        if invoice:
            # Nếu sau này thêm detail thì xóa trước
            InvoiceDetail.query.filter_by(
                invoice_id=invoice_id
            ).delete(
                synchronize_session=False
            )

            db.session.delete(invoice)
            db.session.commit()

            print(
                f"\n[TEARDOWN] Đã xóa PAID invoice "
                f"#{invoice_id}"
            )


@pytest.fixture
def admin_draft_invoice():
    invoice_id = None

    with app.app_context():

        customer = User.query.filter_by(
            username="customer1"
        ).first()

        staff = User.query.filter_by(
            username="staff1"
        ).first()

        # ==========================================
        # Lấy 1 service chắc chắn có product định mức
        # ==========================================

        service_product = ServiceProduct.query.first()

        assert customer is not None
        assert staff is not None
        assert service_product is not None

        service = service_product.service
        product = service_product.product

        assert service is not None
        assert product is not None

        product_quantity = (
            service_product.default_quantity
            if service_product.default_quantity > 0
            else 10
        )

        # ==========================================
        # Tạo DRAFT invoice
        # ==========================================

        invoice = Invoice(
            invoice_date=datetime.now(),
            total_amount=service.price,
            status=InvoiceStatus.DRAFT,
            customer_id=customer.id,
            staff_id=staff.id,
            appointment_id=None,
            promotion_id=None
        )

        db.session.add(invoice)
        db.session.flush()

        # ==========================================
        # Detail SERVICE
        # ==========================================

        service_detail = InvoiceDetail(
            invoice_id=invoice.id,
            item_type=InvoiceItemType.SERVICE,
            service_id=service.id,
            product_id=None,
            quantity=1,
            unit_price=service.price,
            subtotal=service.price
        )

        # ==========================================
        # Detail PRODUCT_USED
        # ==========================================

        product_detail = InvoiceDetail(
            invoice_id=invoice.id,
            item_type=InvoiceItemType.PRODUCT_USED,
            service_id=None,
            product_id=product.id,
            quantity=product_quantity,
            unit_price=0,
            subtotal=0
        )

        db.session.add_all([
            service_detail,
            product_detail
        ])

        db.session.commit()

        invoice_id = invoice.id

        result = {
            "id": invoice.id,

            "service_id": service.id,
            "service_name": service.service_name,
            "original_quantity": 1,

            "product_id": product.id,
            "product_name": product.product_name,
            "product_quantity": product_quantity,
        }

        print(
            f"\n[SETUP] Đã tạo DRAFT invoice "
            f"#{invoice_id}"
        )

        print(
            f"[SETUP] Service: "
            f"{service.service_name}"
        )

        print(
            f"[SETUP] Product: "
            f"{product.product_name} "
            f"x {product_quantity}"
        )

    yield result

    # ==========================================
    # TEARDOWN
    # ==========================================

    with app.app_context():

        InvoiceDetail.query.filter_by(
            invoice_id=invoice_id
        ).delete(
            synchronize_session=False
        )

        invoice = db.session.get(
            Invoice,
            invoice_id
        )

        if invoice:
            db.session.delete(invoice)

        db.session.commit()

        print(
            f"\n[TEARDOWN] Đã xóa invoice "
            f"#{invoice_id}"
        )