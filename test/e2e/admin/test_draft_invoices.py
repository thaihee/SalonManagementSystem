from playwright.sync_api import expect

from app import db, app
from app.models import Invoice, InvoiceStatus, InvoiceDetail, InvoiceItemType
from test.e2e.utils.pagination import find_invoice_row_across_pages, find_invoice_row_by_status_across_pages


def test_admin_can_edit_draft_invoice(
    admin_page,
    admin_draft_invoice,
    base_url
):
    invoice_id = admin_draft_invoice["id"]
    product_id = admin_draft_invoice["product_id"]

    old_quantity = float(
        admin_draft_invoice["product_quantity"]
    )

    new_quantity = old_quantity + 5

    # ==========================================
    # 1. Tìm đúng DRAFT invoice
    # ==========================================

    row = find_invoice_row_across_pages(
        admin_page,
        invoice_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()
    expect(row).to_contain_text("Chờ thanh toán")

    # ==========================================
    # 2. Mở Edit và load Draft Detail
    # ==========================================

    edit_button = row.get_by_role(
        "button",
        name="Sửa",
        exact=False
    )

    expect(edit_button).to_be_visible()

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/invoices/"
                f"{invoice_id}/draft-detail"
            )
            and response.request.method == "GET"
    ) as response_info:

        edit_button.click()

    detail_response = response_info.value

    assert detail_response.ok
    assert detail_response.json()["success"] is True

    # ==========================================
    # 3. Sửa số lượng PRODUCT_USED
    # ==========================================

    edit_row = admin_page.locator(
        f"#edit_row_{invoice_id}"
    )

    expect(edit_row).to_be_visible()

    # Service và Product đúng của fixture phải hiện
    expect(edit_row).to_contain_text(
        admin_draft_invoice["service_name"]
    )

    expect(edit_row).to_contain_text(
        admin_draft_invoice["product_name"]
    )

    product_input = edit_row.locator(
        f'.draft-qty-input-{invoice_id}'
        f'[data-item-type="PRODUCT_USED"]'
        f'[data-item-id="{product_id}"]'
    )

    expect(product_input).to_be_visible()

    assert float(
        product_input.input_value()
    ) == old_quantity

    product_input.fill(
        str(new_quantity)
    )

    # ==========================================
    # 4. Lưu thay đổi
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/invoices/{invoice_id}"
            )
            and response.request.method == "PUT"
    ) as response_info:

        edit_row.get_by_role(
            "button",
            name="Lưu Thay Đổi"
        ).click()

    response = response_info.value

    print(
        "\n[EDIT DRAFT INVOICE] Status:",
        response.status
    )

    print(
        "[EDIT DRAFT INVOICE] Body:",
        response.text()
    )

    assert response.status == 200

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 5. Verify dữ liệu thật trong Database
    # ==========================================

    with app.app_context():

        detail = InvoiceDetail.query.filter_by(
            invoice_id=invoice_id,
            item_type=InvoiceItemType.PRODUCT_USED,
            product_id=product_id
        ).first()

        assert detail is not None

        assert float(
            detail.quantity
        ) == new_quantity


def test_admin_can_cancel_draft_invoice(
    admin_page,
    admin_draft_invoice,
    base_url
):
    invoice_id = admin_draft_invoice["id"]

    # ==========================================
    # 1. Tìm DRAFT invoice
    # ==========================================

    row = find_invoice_row_across_pages(
        admin_page,
        invoice_id,
        base_url
    )

    assert row is not None, (
        f"Không tìm thấy DRAFT invoice "
        f"#{invoice_id}"
    )

    expect(row).to_be_visible()

    expect(row).to_contain_text(
        f"#{invoice_id}"
    )

    expect(row).to_contain_text(
        "Chờ thanh toán"
    )

    # ==========================================
    # 2. Nút Hủy phải tồn tại
    # ==========================================

    cancel_button = row.get_by_role(
        "button",
        name="Hủy",
        exact=False
    )

    expect(cancel_button).to_be_visible()

    # ==========================================
    # 3. Click Hủy + accept native confirm
    # ==========================================

    admin_page.once(
        "dialog",
        lambda dialog: dialog.accept()
    )

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/invoices/"
                f"{invoice_id}/cancel"
            )
            and response.request.method == "PATCH"
    ) as response_info:

        cancel_button.click()

    response = response_info.value

    print(
        "\n[CANCEL DRAFT INVOICE] Status:",
        response.status
    )

    print(
        "[CANCEL DRAFT INVOICE] Body:",
        response.text()
    )

    # ==========================================
    # 4. Backend phải hủy thành công
    # ==========================================

    assert response.status == 200

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 5. Chờ frontend reload
    # ==========================================

    admin_page.wait_for_timeout(
        800
    )

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 6. Invoice không còn trong DRAFT
    # ==========================================

    draft_row = find_invoice_row_across_pages(
        admin_page,
        invoice_id,
        base_url
    )

    assert draft_row is None, (
        f"Invoice #{invoice_id} vẫn còn "
        f"xuất hiện trong danh sách DRAFT "
        f"sau khi hủy"
    )

    # ==========================================
    # 7. Verify trạng thái thật trong Database
    # ==========================================

    with app.app_context():
        cancelled_invoice = db.session.get(
            Invoice,
            invoice_id
        )

        assert cancelled_invoice is not None, (
            f"Invoice #{invoice_id} "
            f"không còn tồn tại trong DB"
        )

        assert (
                cancelled_invoice.status
                == InvoiceStatus.CANCELLED
        ), (
            f"Invoice #{invoice_id} có status "
            f"{cancelled_invoice.status}, "
            f"mong đợi CANCELLED"
        )