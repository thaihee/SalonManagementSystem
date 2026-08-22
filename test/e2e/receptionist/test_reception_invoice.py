from playwright.sync_api import expect

from test.e2e.utils.pagination import find_row_across_pages


def test_receptionist_can_open_invoice_list(
    receptionist_page,
    base_url
):
    receptionist_page.goto(
        f"{base_url}/reception/invoices"
    )

    # Heading
    expect(
        receptionist_page.get_by_role(
            "heading",
            name="Quản Lý Hóa Đơn"
        )
    ).to_be_visible()

    # Search
    expect(
        receptionist_page.locator(
            "#reception_invoice_search"
        )
    ).to_be_visible()

    # Filter stylist
    expect(
        receptionist_page.locator(
            "#stylist_filter"
        )
    ).to_be_visible()

    # Filter ngày
    expect(
        receptionist_page.locator(
            "#date_filter"
        )
    ).to_be_visible()

    # Bảng invoice
    expect(
        receptionist_page.locator(
            "#invoices-tbody"
        )
    ).to_be_visible()

    # Các tab trạng thái
    expect(
        receptionist_page.get_by_text(
            "CHỜ THANH TOÁN (DRAFT)",
            exact=True
        )
    ).to_be_visible()

    expect(
        receptionist_page.get_by_text(
            "ĐÃ THANH TOÁN (PAID)",
            exact=True
        )
    ).to_be_visible()


def test_receptionist_can_open_draft_invoice_checkout(
    receptionist_page,
    reception_draft_invoice,
    base_url
):
    invoice_id = reception_draft_invoice["id"]

    # ==========================================
    # 1. Mở danh sách DRAFT
    # ==========================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=DRAFT"
    )

    # ==========================================
    # 2. Tìm invoice qua pagination
    # ==========================================

    row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert row is not None, (
        f"Không tìm thấy DRAFT invoice #{invoice_id}"
    )

    expect(row).to_be_visible()

    # Kiểm tra đúng dữ liệu invoice
    expect(row).to_contain_text(
        f"#{invoice_id}"
    )

    expect(row).to_contain_text(
        "Phạm Thị Lan"
    )

    expect(row).to_contain_text(
        "Trần Thị Hằng"
    )

    expect(row).to_contain_text(
        "Chờ thanh toán"
    )

    # ==========================================
    # 3. Click Thanh toán thật
    # ==========================================

    row.get_by_role(
        "link",
        name="Thanh toán"
    ).click()

    # ==========================================
    # 4. Checkout phải mở đúng invoice
    # ==========================================

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    assert f"/reception/invoice/{invoice_id}/checkout" in receptionist_page.url


def test_receptionist_checkout_page_displays_invoice_information(
    receptionist_page,
    reception_draft_invoice,
    base_url
):
    invoice_id = reception_draft_invoice["id"]

    # ==========================================
    # 1. Mở danh sách DRAFT
    # ==========================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=DRAFT"
    )

    row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert row is not None

    # ==========================================
    # 2. Click Thanh toán qua UI
    # ==========================================

    row.get_by_role(
        "link",
        name="Thanh toán"
    ).click()

    assert (
        f"/reception/invoice/{invoice_id}/checkout"
        in receptionist_page.url
    )

    # ==========================================
    # 3. Thông tin invoice
    # ==========================================

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    # Customer
    expect(
        receptionist_page.locator("body")
    ).to_contain_text(
        "Phạm Thị Lan"
    )

    # Stylist
    expect(
        receptionist_page.locator("body")
    ).to_contain_text(
        "Trần Thị Hằng"
    )

    # ==========================================
    # 4. Service
    # ==========================================

    expect(
        receptionist_page.locator("body")
    ).to_contain_text(
        "Gội đầu dưỡng sinh"
    )

    # ==========================================
    # 5. Product USED
    # ==========================================

    expect(
        receptionist_page.locator("body")
    ).to_contain_text(
        "Dầu gội"
    )

    expect(
        receptionist_page.locator("body")
    ).to_contain_text(
        "Dầu xả"
    )

    # ==========================================
    # 6. Promotion
    # ==========================================

    promotion_select = receptionist_page.get_by_role(
        "combobox"
    )

    expect(promotion_select).to_be_visible()

    expect(
        promotion_select.locator("option")
    ).to_contain_text([
        "-- Không áp dụng --",
        "SALON10 (Giảm 10%)"
    ])

    # ==========================================
    # 7. Payment methods
    # ==========================================

    cash = receptionist_page.get_by_role(
        "radio",
        name="Tiền mặt (CASH)"
    )

    bank = receptionist_page.get_by_role(
        "radio",
        name="Chuyển khoản (BANK)"
    )

    card = receptionist_page.get_by_role(
        "radio",
        name="Quẹt thẻ (CARD)"
    )

    expect(cash).to_be_visible()
    expect(bank).to_be_visible()
    expect(card).to_be_visible()

    expect(cash).to_be_checked()
    expect(bank).not_to_be_checked()
    expect(card).not_to_be_checked()

    # ==========================================
    # 8. Tổng tiền
    # ==========================================

    expect(
        receptionist_page.get_by_text(
            "Tổng tạm tính:",
            exact=True
        )
    ).to_be_visible()

    expect(
        receptionist_page.get_by_text(
            "TỔNG THU:",
            exact=True
        )
    ).to_be_visible()

    # ==========================================
    # 9. Confirm
    # ==========================================

    confirm_button = receptionist_page.get_by_role(
        "button",
        name="XÁC NHẬN THANH TOÁN"
    )

    expect(confirm_button).to_be_visible()
    expect(confirm_button).to_be_enabled()


def test_receptionist_can_apply_promotion_on_checkout(
    receptionist_page,
    reception_draft_invoice,
    base_url
):
    invoice_id = reception_draft_invoice["id"]

    # ==========================================
    # 1. Mở danh sách DRAFT
    # ==========================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=DRAFT"
    )

    row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert row is not None

    # ==========================================
    # 2. Click Thanh toán
    # ==========================================

    row.get_by_role(
        "link",
        name="Thanh toán"
    ).click()

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    # ==========================================
    # 3. Tổng tiền ban đầu
    # ==========================================

    expect(
        receptionist_page.get_by_text(
            "120,000 đ",
            exact=True
        ).first
    ).to_be_visible()

    # ==========================================
    # 4. Chọn promotion SALON10 qua UI
    # ==========================================

    promotion_select = receptionist_page.get_by_role(
        "combobox"
    )

    expect(promotion_select).to_be_visible()

    promotion_select.select_option(
        label="SALON10 (Giảm 10%)"
    )

    # ==========================================
    # 5. Tổng thu phải thay đổi trên UI
    # ==========================================

    expect(
        receptionist_page.get_by_text(
            "108,000 đ",
            exact=True
        )
    ).to_be_visible()

    # ==========================================
    # 6. Vẫn chưa thanh toán
    # ==========================================

    expect(
        receptionist_page.get_by_role(
            "button",
            name="XÁC NHẬN THANH TOÁN"
        )
    ).to_be_visible()

    # Vẫn đang ở checkout
    assert (
        f"/reception/invoice/{invoice_id}/checkout"
        in receptionist_page.url
    )


def test_receptionist_can_confirm_invoice_payment(
    receptionist_page,
    reception_draft_invoice,
    base_url
):
    invoice_id = reception_draft_invoice["id"]

    # =====================================================
    # 1. Receptionist mở danh sách DRAFT
    # =====================================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=DRAFT"
    )

    row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert row is not None

    expect(row).to_contain_text(
        f"#{invoice_id}"
    )

    expect(row).to_contain_text(
        "Chờ thanh toán"
    )

    # =====================================================
    # 2. Click Thanh toán
    # =====================================================

    row.get_by_role(
        "link",
        name="Thanh toán"
    ).click()

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    # =====================================================
    # 3. Chọn SALON10
    # =====================================================

    promotion_select = receptionist_page.get_by_role(
        "combobox"
    )

    promotion_select.select_option(
        label="SALON10 (Giảm 10%)"
    )

    # Sau khi mình vừa sửa formatCurrency()
    expect(
        receptionist_page.get_by_text(
            "108,000 đ",
            exact=True
        )
    ).to_be_visible()

    # =====================================================
    # 4. Chọn BANK
    # =====================================================

    bank = receptionist_page.get_by_role(
        "radio",
        name="Chuyển khoản (BANK)"
    )

    bank.check()

    expect(bank).to_be_checked()

    # CASH phải bỏ chọn
    cash = receptionist_page.get_by_role(
        "radio",
        name="Tiền mặt (CASH)"
    )

    expect(cash).not_to_be_checked()

    # =====================================================
    # 5. Xác nhận thanh toán thật qua UI
    # =====================================================

    confirm_button = receptionist_page.get_by_role(
        "button",
        name="XÁC NHẬN THANH TOÁN"
    )

    expect(confirm_button).to_be_enabled()

    with receptionist_page.expect_response(
        lambda response:
            "confirm-payment" in response.url
            and response.request.method in ("PATCH", "POST")
    ) as response_info:

        confirm_button.click()

    response = response_info.value

    # =====================================================
    # 6. Backend phải xác nhận thành công
    # =====================================================

    assert response.status == 200

    body = response.json()

    print(
        f"\n[TEST] Receptionist đã thanh toán "
        f"invoice #{invoice_id}"
    )

    print(
        "[TEST] Response:",
        body
    )

    # =====================================================
    # 7. JS phải redirect sang Invoice Detail
    # =====================================================

    receptionist_page.wait_for_url(
        f"**/invoices/{invoice_id}"
    )

    assert (
        f"/invoices/{invoice_id}"
        in receptionist_page.url
    )

    # =====================================================
    # 8. Invoice Detail phải thể hiện PAID
    # =====================================================

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    invoice_card = receptionist_page.locator(
        ".invoice-paper-card"
    )

    expect(invoice_card).to_contain_text(
        "ĐÃ THANH TOÁN"
    )

    # =====================================================
    # 9. Receptionist thực hiện
    # =====================================================

    expect(invoice_card).to_contain_text(
        "Đỗ Thị Mai"
    )

    # =====================================================
    # 10. Payment method
    # =====================================================

    expect(invoice_card).to_contain_text(
        "BANK"
    )

    # =====================================================
    # 11. Promotion / tổng thanh toán
    # =====================================================

    expect(invoice_card).to_contain_text(
        "108,000"
    )


def test_paid_invoice_moves_from_draft_to_paid_list(
    receptionist_page,
    reception_draft_invoice,
    base_url
):
    invoice_id = reception_draft_invoice["id"]

    # =====================================================
    # 1. Mở danh sách DRAFT
    # =====================================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=DRAFT"
    )

    row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert row is not None

    expect(row).to_contain_text(
        "Chờ thanh toán"
    )

    # =====================================================
    # 2. Mở checkout
    # =====================================================

    row.get_by_role(
        "link",
        name="Thanh toán"
    ).click()

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    # =====================================================
    # 3. Chọn BANK
    # =====================================================

    bank = receptionist_page.get_by_role(
        "radio",
        name="Chuyển khoản (BANK)"
    )

    bank.check()

    expect(bank).to_be_checked()

    # =====================================================
    # 4. Thanh toán
    # =====================================================

    confirm_button = receptionist_page.get_by_role(
        "button",
        name="XÁC NHẬN THANH TOÁN"
    )

    with receptionist_page.expect_response(
        lambda response:
            "confirm-payment" in response.url
            and response.request.method in ("PATCH", "POST")
    ) as response_info:

        confirm_button.click()

    response = response_info.value

    assert response.status == 200

    # Chờ redirect hoàn tất
    receptionist_page.wait_for_url(
        f"**/invoices/{invoice_id}"
    )

    # =====================================================
    # 5. Quay lại tab DRAFT
    # =====================================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=DRAFT"
    )

    draft_row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    # Invoice PAID không còn thuộc danh sách DRAFT
    assert draft_row is None

    # =====================================================
    # 6. Mở tab PAID
    # =====================================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=PAID"
    )

    paid_row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert paid_row is not None

    expect(paid_row).to_be_visible()

    expect(paid_row).to_contain_text(
        f"#{invoice_id}"
    )

    expect(paid_row).to_contain_text(
        "Phạm Thị Lan"
    )

    expect(paid_row).to_contain_text(
        "Trần Thị Hằng"
    )

    expect(paid_row).to_contain_text(
        "Đã thanh toán"
    )

    # =====================================================
    # 7. PAID không còn nút Thanh toán
    # =====================================================

    expect(
        paid_row.get_by_role(
            "link",
            name="Thanh toán"
        )
    ).to_have_count(0)

    # Nhưng vẫn xem được chi tiết
    expect(
        paid_row.get_by_role(
            "link",
            name="Chi tiết"
        )
    ).to_be_visible()


def test_receptionist_can_pay_cash_without_promotion(
    receptionist_page,
    reception_draft_invoice,
    base_url
):
    invoice_id = reception_draft_invoice["id"]

    # =====================================================
    # 1. Mở danh sách DRAFT
    # =====================================================

    receptionist_page.goto(
        f"{base_url}/reception/invoices?status=DRAFT"
    )

    row = find_row_across_pages(
        receptionist_page,
        f'.inv-row[data-inv-id="#{invoice_id}"]'
    )

    assert row is not None

    expect(row).to_be_visible()

    expect(row).to_contain_text(
        "Chờ thanh toán"
    )

    # =====================================================
    # 2. Click Thanh toán
    # =====================================================

    row.get_by_role(
        "link",
        name="Thanh toán"
    ).click()

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    # =====================================================
    # 3. KHÔNG áp dụng promotion
    # =====================================================

    promotion_select = receptionist_page.get_by_role(
        "combobox"
    )

    expect(promotion_select).to_be_visible()

    # Option mặc định phải là "-- Không áp dụng --"
    expect(
        promotion_select
    ).to_have_value("")

    # =====================================================
    # 4. CASH phải là payment mặc định
    # =====================================================

    cash = receptionist_page.get_by_role(
        "radio",
        name="Tiền mặt (CASH)"
    )

    bank = receptionist_page.get_by_role(
        "radio",
        name="Chuyển khoản (BANK)"
    )

    card = receptionist_page.get_by_role(
        "radio",
        name="Quẹt thẻ (CARD)"
    )

    expect(cash).to_be_checked()
    expect(bank).not_to_be_checked()
    expect(card).not_to_be_checked()

    # =====================================================
    # 5. Không promotion → tổng thu không thay đổi
    # =====================================================

    expect(
        receptionist_page.locator("body")
    ).to_contain_text(
        "TỔNG THU: 120,000 đ"
    )

    # =====================================================
    # 6. Xác nhận thanh toán CASH
    # =====================================================

    confirm_button = receptionist_page.get_by_role(
        "button",
        name="XÁC NHẬN THANH TOÁN"
    )

    expect(confirm_button).to_be_visible()
    expect(confirm_button).to_be_enabled()

    with receptionist_page.expect_response(
        lambda response:
            "confirm-payment" in response.url
            and response.request.method in ("PATCH", "POST")
    ) as response_info:

        confirm_button.click()

    response = response_info.value

    assert response.status == 200

    # =====================================================
    # 7. Redirect sang Invoice Detail
    # =====================================================

    receptionist_page.wait_for_url(
        f"**/invoices/{invoice_id}"
    )

    expect(
        receptionist_page.get_by_role(
            "heading",
            name=f"Hóa Đơn #{invoice_id}"
        )
    ).to_be_visible()

    # =====================================================
    # 8. Invoice phải PAID
    # =====================================================

    invoice_card = receptionist_page.locator(
        ".invoice-paper-card"
    )

    expect(invoice_card).to_contain_text(
        "ĐÃ THANH TOÁN"
    )

    # =====================================================
    # 9. Đúng Receptionist
    # =====================================================

    expect(invoice_card).to_contain_text(
        "Đỗ Thị Mai"
    )

    # =====================================================
    # 10. Đúng payment method
    # =====================================================

    expect(invoice_card).to_contain_text(
        "CASH"
    )

    # =====================================================
    # 11. Tổng tiền vẫn nguyên giá
    # =====================================================

    expect(invoice_card).to_contain_text(
        "120,000"
    )

    print(
        f"\n[TEST] Invoice #{invoice_id} "
        f"đã thanh toán CASH không promotion"
    )