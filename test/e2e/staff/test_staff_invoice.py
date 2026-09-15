from playwright.sync_api import expect

from test.e2e.utils.pagination import find_row_across_pages


def test_staff_can_open_create_invoice_from_booking(
    staff_page,
    staff1_booking,
    base_url
):
    appointment_id = staff1_booking["id"]
    booking_date = staff1_booking["date"]
    service_id = staff1_booking["service_id"]

    # ==========================================
    # 1. Staff mở danh sách lịch được giao
    # ==========================================

    staff_page.goto(
        f"{base_url}/staff/appointments?date={booking_date}"
    )

    # Vì danh sách có pagination
    row = find_row_across_pages(
        staff_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None, (
        f"Không tìm thấy appointment #{appointment_id}"
    )

    expect(row).to_be_visible()

    # ==========================================
    # 2. Click "Tạo hóa đơn" thật trên UI
    # ==========================================

    create_invoice_link = row.get_by_role(
        "link",
        name="Tạo hóa đơn"
    )

    expect(create_invoice_link).to_be_visible()

    create_invoice_link.click()

    # ==========================================
    # 3. Kiểm tra đã vào form invoice
    # ==========================================

    expect(
        staff_page.get_by_role(
            "heading",
            name="Lập Hóa Đơn Nháp (DRAFT)"
        )
    ).to_be_visible()

    # ==========================================
    # 4. Appointment phải được truyền đúng
    # ==========================================

    expect(
        staff_page.locator("#appointment_id")
    ).to_have_value(str(appointment_id))

    # ==========================================
    # 5. Customer phải được truyền đúng
    # ==========================================

    customer_id = staff_page.locator("#customer_id")

    expect(customer_id).not_to_have_value("")

    expect(
        staff_page.locator(".customer-selected-card")
    ).to_contain_text("Phạm Thị Lan")

    expect(
        staff_page.locator(".customer-selected-card")
    ).to_contain_text(
        f"Mã Lịch Hẹn: #{appointment_id}"
    )

    # ==========================================
    # 6. Service của appointment phải được load
    # ==========================================

    service_rows = staff_page.locator(
        "#selectedServicesBody tr"
    )

    expect(service_rows).to_have_count(1)

    service_row = service_rows.first

    expect(service_row).not_to_contain_text(
        "Chưa chọn dịch vụ nào"
    )

    # ==========================================
    # 7. Summary phải nhận service
    # ==========================================

    expect(
        staff_page.locator("#service_count_text")
    ).to_have_text("1 mục")

    # ==========================================
    # 8. Tổng tiền không được bằng 0
    # ==========================================

    expect(
        staff_page.locator("#grand_total_text")
    ).not_to_have_text("0 đ")

    # ==========================================
    # 9. Form đang ở trạng thái DRAFT
    # ==========================================

    expect(
        staff_page.locator(".summary-card-sticky")
    ).to_contain_text("DRAFT")

    # ==========================================
    # 10. Có nút lưu hóa đơn nháp
    # ==========================================

    expect(
        staff_page.locator("#btnSubmitDraft")
    ).to_be_visible()

    expect(
        staff_page.locator("#btnSubmitDraft")
    ).to_be_enabled()


def test_service_products_are_loaded_automatically(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

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

    # Service phải tự được add vào hóa đơn
    service_rows = staff_page.locator(
        "#selectedServicesBody tr"
    )

    expect(service_rows).to_have_count(1)

    expect(
        service_rows.first
    ).to_contain_text(
        "Gội đầu dưỡng sinh"
    )

    # ==========================================
    # PRODUCT
    # ==========================================

    product_rows = staff_page.locator(
        "#selectedProductsBody tr"
    )

    # Seed có 2 product:
    # Dầu gội + Dầu xả
    expect(product_rows).to_have_count(2)

    products_body = staff_page.locator(
        "#selectedProductsBody"
    )

    expect(products_body).to_contain_text(
        "Dầu gội"
    )

    expect(products_body).to_contain_text(
        "Dầu xả"
    )

    # Input tiêu hao thực tế
    quantity_inputs = staff_page.locator(
        '#selectedProductsBody input[type="number"]'
    )

    expect(quantity_inputs).to_have_count(2)

    # Giá trị mặc định phải đúng định mức
    expect(
        quantity_inputs.nth(0)
    ).to_have_value("30")

    expect(
        quantity_inputs.nth(1)
    ).to_have_value("15")

    # Summary
    expect(
        staff_page.locator("#product_count_text")
    ).to_have_text("2 mục")


def test_staff_can_adjust_actual_product_usage(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

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

    # Chờ product render
    quantity_inputs = staff_page.locator(
        '#selectedProductsBody input[type="number"]'
    )

    expect(quantity_inputs).to_have_count(2)

    # Giá trị định mức mặc định
    expect(quantity_inputs.nth(0)).to_have_value("30")
    expect(quantity_inputs.nth(1)).to_have_value("15")

    # Stylist nhập lượng thực tế
    quantity_inputs.nth(0).fill("25")
    quantity_inputs.nth(0).blur()

    quantity_inputs.nth(1).fill("12")
    quantity_inputs.nth(1).blur()

    # UI phải giữ đúng lượng thực tế vừa nhập
    expect(quantity_inputs.nth(0)).to_have_value("25")
    expect(quantity_inputs.nth(1)).to_have_value("12")


def test_staff_can_create_draft_invoice(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]
    staff_page.goto(
        f"{base_url}/staff/appointments?date={booking_date}"
    )
    row = find_row_across_pages(
        staff_page,
        f"#row-appt-{appointment_id}"
    )
    assert row is not None, (
        f"Không tìm thấy appointment #{appointment_id}"
    )
    expect(row).to_be_visible()
    create_invoice_link = row.get_by_role(
        "link",
        name="Tạo hóa đơn"
    )
    expect(create_invoice_link).to_be_visible()
    create_invoice_link.click()
    expect(
        staff_page.locator("#appointment_id")
    ).to_have_value(str(appointment_id))
    service_rows = staff_page.locator(
        "#selectedServicesBody tr"
    )
    expect(service_rows).to_have_count(1)
    expect(
        service_rows.first
    ).not_to_contain_text(
        "Chưa chọn dịch vụ nào"
    )
    quantity_inputs = staff_page.locator(
        '#selectedProductsBody input[type="number"]'
    )
    product_count = quantity_inputs.count()
    assert product_count > 0, (
        "Service được chọn không có sản phẩm định mức"
    )
    for i in range(product_count):
        quantity_input = quantity_inputs.nth(i)
        current_value = float(
            quantity_input.input_value()
        )
        assert current_value > 0, (
            f"Product thứ {i + 1} có định mức không hợp lệ"
        )
        new_value = round(
            max(current_value * 0.8, 0.01),
            2
        )
        if new_value.is_integer():
            new_value_text = str(int(new_value))
        else:
            new_value_text = str(new_value)
        quantity_input.fill(
            new_value_text
        )
        quantity_input.blur()
        expect(
            quantity_input
        ).to_have_value(
            new_value_text
        )
    with staff_page.expect_response(
        lambda response:
            response.url.endswith("/invoices")
            and response.request.method == "POST"
    ) as response_info:

        staff_page.locator(
            "#btnSubmitDraft"
        ).click()
    response = response_info.value
    assert response.status == 201, (
        f"Tạo invoice thất bại - "
        f"status={response.status}, "
        f"body={response.text()}"
    )
    body = response.json()
    assert "invoice" in body
    assert (
        body["invoice"]["status"]
        == "DRAFT"
    )
    invoice_id = body["invoice"]["id"]
    assert invoice_id is not None
    print(
        f"\n[TEST] Đã tạo invoice DRAFT "
        f"#{invoice_id} "
        f"cho appointment #{appointment_id}"
    )

def test_created_draft_invoice_appears_in_staff_invoice_list(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

    # =====================================================
    # 1. Staff mở appointment
    # =====================================================

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

    # =====================================================
    # 2. Chỉnh lượng sản phẩm thực tế
    # =====================================================

    quantity_inputs = staff_page.locator(
        '#selectedProductsBody input[type="number"]'
    )

    expect(quantity_inputs).to_have_count(2)

    quantity_inputs.nth(0).fill("25")
    quantity_inputs.nth(0).blur()

    quantity_inputs.nth(1).fill("12")
    quantity_inputs.nth(1).blur()

    # =====================================================
    # 3. Tạo DRAFT
    # =====================================================

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

    invoice_id = body["invoice"]["id"]

    assert body["invoice"]["status"] == "DRAFT"

    print(
        f"\n[TEST] Đã tạo invoice DRAFT #{invoice_id}"
    )

    # =====================================================
    # 4. Mở danh sách invoice của Staff
    # =====================================================

    staff_page.goto(
        f"{base_url}/staff/invoices?status=DRAFT"
    )

    # =====================================================
    # 5. Tìm invoice qua pagination
    # =====================================================

    invoice_row = find_row_across_pages(
        staff_page,
        f'.staff-inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert invoice_row is not None, (
        f"Không tìm thấy invoice DRAFT #{invoice_id} "
        f"trong danh sách hóa đơn của Staff"
    )

    expect(invoice_row).to_be_visible()

    # =====================================================
    # 6. Kiểm tra dữ liệu hiển thị
    # =====================================================

    expect(invoice_row).to_contain_text(
        f"#{invoice_id}"
    )

    expect(invoice_row).to_contain_text(
        "Phạm Thị Lan"
    )

    expect(invoice_row).to_contain_text(
        "Gội đầu dưỡng sinh"
    )

    expect(invoice_row).to_contain_text(
        "Chờ Lễ tân thu"
    )

    # =====================================================
    # 7. Có thể mở chi tiết
    # =====================================================

    expect(
        invoice_row.get_by_role(
            "link",
            name="Chi tiết"
        )
    ).to_be_visible()


def test_staff_can_view_draft_invoice_detail(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

    # =====================================================
    # Tạo invoice DRAFT
    # =====================================================

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

    invoice_id = body["invoice"]["id"]

    # =====================================================
    # Mở danh sách
    # =====================================================

    staff_page.goto(
        f"{base_url}/staff/invoices?status=DRAFT"
    )

    invoice_row = find_row_across_pages(
        staff_page,
        f'.staff-inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert invoice_row is not None

    # =====================================================
    # Click Chi tiết thật
    # =====================================================

    invoice_row.get_by_role(
        "link",
        name="Chi tiết"
    ).click()

    # =====================================================
    # Kiểm tra invoice detail
    # =====================================================

    expect(
        staff_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    expect(
        staff_page.locator(".invoice-paper-card")
    ).to_contain_text(
        "HÓA ĐƠN NHÁP"
    )

    expect(
        staff_page.locator(".invoice-paper-card")
    ).to_contain_text(
        "Phạm Thị Lan"
    )

    expect(
        staff_page.locator(".invoice-paper-card")
    ).to_contain_text(
        "Trần Thị Hằng"
    )

    expect(
        staff_page.locator(".invoice-paper-card")
    ).to_contain_text(
        "Gội đầu dưỡng sinh"
    )

    # DRAFT chưa có lễ tân và phương thức thanh toán
    expect(
        staff_page.locator(".invoice-paper-card")
    ).to_contain_text(
        "Chưa chọn"
    )

    # Staff phải có nút quay lại đúng danh sách của mình
    expect(
        staff_page.get_by_role(
            "link",
            name="Danh sách hóa đơn"
        )
    ).to_be_visible()


def test_staff_cannot_create_duplicate_invoice_for_same_appointment(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

    # =====================================================
    # 1. Mở appointment
    # =====================================================

    staff_page.goto(
        f"{base_url}/staff/appointments?date={booking_date}"
    )

    row = find_row_across_pages(
        staff_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None

    create_invoice_link = row.get_by_role(
        "link",
        name="Tạo hóa đơn"
    )

    expect(create_invoice_link).to_be_visible()

    # =====================================================
    # 2. Tạo invoice DRAFT lần đầu
    # =====================================================

    create_invoice_link.click()

    expect(
        staff_page.locator("#appointment_id")
    ).to_have_value(str(appointment_id))

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

    invoice_id = body["invoice"]["id"]

    assert body["invoice"]["status"] == "DRAFT"

    print(
        f"\n[TEST] Invoice đầu tiên #{invoice_id} "
        f"đã được tạo cho appointment #{appointment_id}"
    )

    # =====================================================
    # 3. Quay lại appointment
    # =====================================================

    staff_page.goto(
        f"{base_url}/staff/appointments?date={booking_date}"
    )

    row = find_row_across_pages(
        staff_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None

    # =====================================================
    # 4. Không được phép tạo invoice lần 2 qua UI
    # =====================================================

    duplicate_create_link = row.get_by_role(
        "link",
        name="Tạo hóa đơn"
    )

    expect(
        duplicate_create_link
    ).to_have_count(0)


def test_staff_cannot_create_invoice_without_service(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

    # Mở appointment
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

    # Service mặc định phải có
    service_rows = staff_page.locator(
        "#selectedServicesBody tr"
    )

    expect(service_rows).to_have_count(1)

    # Click nút thùng rác để xóa service
    service_rows.first.locator(
        ".btn-action-cancel"
    ).click()

    # Sau khi xóa phải hiện trạng thái rỗng
    expect(
        staff_page.locator("#selectedServicesBody")
    ).to_contain_text(
        "Chưa chọn dịch vụ nào"
    )

    expect(
        staff_page.locator("#service_count_text")
    ).to_have_text("0 mục")

    # Product cũng phải được rebuild về rỗng
    expect(
        staff_page.locator("#product_count_text")
    ).to_have_text("0 mục")

    # Click Lưu
    staff_page.locator("#btnSubmitDraft").click()

    # UI phải báo lỗi
    error_toast = staff_page.locator(".toast-error")

    expect(error_toast).to_be_visible(timeout=5000)

    expect(error_toast).to_contain_text(
        "Hóa đơn phải có ít nhất 1 dịch vụ"
    )

    # Vẫn ở form tạo invoice
    assert "/staff/create-invoice" in staff_page.url


def test_staff_cannot_submit_invalid_product_quantity(
    staff_page,
    staff1_booking_with_products,
    base_url
):
    appointment_id = staff1_booking_with_products["id"]
    booking_date = staff1_booking_with_products["date"]

    # Mở form invoice từ appointment
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

    quantity_inputs = staff_page.locator(
        '#selectedProductsBody input[type="number"]'
    )

    expect(quantity_inputs).to_have_count(2)

    first_quantity = quantity_inputs.first

    # Giá trị ban đầu hợp lệ
    expect(first_quantity).to_have_value("30")

    # Nhập quantity không hợp lệ
    first_quantity.fill("0")

    # Browser phải đánh dấu vi phạm min=0.01
    is_invalid = first_quantity.evaluate(
        "el => el.validity.rangeUnderflow"
    )

    assert is_invalid is True

    # Form cũng phải ở trạng thái invalid
    form_valid = staff_page.locator(
        "#createInvoiceForm"
    ).evaluate(
        "form => form.checkValidity()"
    )

    assert form_valid is False

    # Click submit
    staff_page.locator("#btnSubmitDraft").click()

    # Browser giữ user tại form vì validation thất bại
    assert "/staff/create-invoice" in staff_page.url

    # Không có invoice success toast
    expect(
        staff_page.locator(".toast-success")
    ).to_have_count(0)