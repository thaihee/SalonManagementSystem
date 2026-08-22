import uuid

from playwright.sync_api import expect

from test.e2e.utils.pagination import find_product_row_across_pages


def test_admin_can_open_products_page(
    admin_page,
    base_url
):
    admin_page.goto(
        f"{base_url}/admin/products"
    )

    expect(
        admin_page.get_by_role(
            "heading",
            name="Quản Lý Sản Phẩm & Tồn Kho"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "button",
            name="Thêm Sản Phẩm Mới"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_text(
            "Kho Sản Phẩm Tiêu Hao",
            exact=False
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Tên Sản Phẩm"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Số Lượng Tồn"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Tồn Tối Thiểu"
        )
    ).to_be_visible()


def test_admin_can_create_product(
    admin_page,
    admin_test_product,
    base_url
):
    product_id = admin_test_product["id"]
    product_name = admin_test_product["name"]

    # ==========================================
    # Tìm Product vừa tạo qua pagination
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None, (
        f"Không tìm thấy product #{product_id}"
    )

    expect(row).to_be_visible()

    # ==========================================
    # Kiểm tra dữ liệu trên UI
    # ==========================================

    expect(row).to_contain_text(
        product_name
    )

    expect(row).to_contain_text(
        "ML"
    )

    expect(row).to_contain_text(
        "100"
    )

    expect(row).to_contain_text(
        "20"
    )

def test_admin_can_edit_product(
    admin_page,
    admin_test_product,
    base_url
):
    product_id = admin_test_product["id"]

    # ==========================================
    # 1. Tìm Product qua pagination
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    # ==========================================
    # 2. Click nút Sửa
    # ==========================================

    edit_button = row.locator(
        'button[title="Sửa thông tin"]'
    )

    expect(edit_button).to_be_visible()

    edit_button.click()

    # ==========================================
    # 3. Inline edit row phải hiện
    # ==========================================

    edit_row = admin_page.locator(
        f"#edit_product_row_{product_id}"
    )

    expect(edit_row).to_be_visible()

    # ==========================================
    # 4. Sửa dữ liệu qua UI
    # ==========================================

    new_name = f"{admin_test_product['name']}_UPDATED"

    admin_page.locator(
        f"#edit_name_{product_id}"
    ).fill(new_name)

    admin_page.locator(
        f"#edit_unit_{product_id}"
    ).select_option("GRAM")

    admin_page.locator(
        f"#edit_min_stock_{product_id}"
    ).fill("30")

    expect(
        admin_page.locator(
            f"#edit_name_{product_id}"
        )
    ).to_have_value(new_name)

    expect(
        admin_page.locator(
            f"#edit_unit_{product_id}"
        )
    ).to_have_value("GRAM")

    expect(
        admin_page.locator(
            f"#edit_min_stock_{product_id}"
        )
    ).to_have_value("30")

    # ==========================================
    # 5. Click Lưu Đổi Thay
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/products/{product_id}"
            )
            and response.request.method == "PUT"
    ) as response_info:

        edit_row.get_by_role(
            "button",
            name="Lưu Đổi Thay"
        ).click()

    response = response_info.value

    print(
        "\n[EDIT PRODUCT] Status:",
        response.status
    )

    print(
        "[EDIT PRODUCT] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 6. Chờ reload
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 7. Tìm lại Product
    # ==========================================

    updated_row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert updated_row is not None

    expect(updated_row).to_be_visible()

    # ==========================================
    # 8. UI phải phản ánh dữ liệu mới
    # ==========================================

    expect(updated_row).to_contain_text(
        new_name
    )

    expect(updated_row).to_contain_text(
        "GRAM"
    )

    expect(updated_row).to_contain_text(
        "30"
    )

    # Stock không được thay đổi khi chỉ edit thông tin
    expect(updated_row).to_contain_text(
        "100"
    )


def test_admin_can_import_product_stock(
    admin_page,
    admin_test_product,
    base_url
):
    product_id = admin_test_product["id"]

    # ==========================================
    # 1. Tìm Product
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    # Stock ban đầu
    expect(row).to_contain_text("100")

    # ==========================================
    # 2. Click Nhập
    # ==========================================

    import_button = row.get_by_role(
        "button",
        name="Nhập"
    )

    expect(import_button).to_be_visible()
    import_button.click()

    # ==========================================
    # 3. Modal Nhập kho phải hiện
    # ==========================================

    modal = admin_page.locator(
        "#stockActionModal"
    )

    expect(modal).to_be_visible()

    expect(
        admin_page.locator("#modalTitle")
    ).to_have_text(
        "Nhập Kho Sản Phẩm"
    )

    expect(
        admin_page.locator("#modalSubTitle")
    ).to_contain_text(
        admin_test_product["name"]
    )

    # ==========================================
    # 4. Nhập thêm 50
    # ==========================================

    quantity = admin_page.locator(
        "#modalQuantity"
    )

    quantity.fill("50")

    expect(quantity).to_have_value("50")

    # ==========================================
    # 5. Xác nhận nhập kho qua UI
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/products/{product_id}/import"
            )
            and response.request.method == "POST"
    ) as response_info:

        admin_page.get_by_role(
            "button",
            name="Xác Nhận Nhập"
        ).click()

    response = response_info.value

    print(
        "\n[IMPORT STOCK] Status:",
        response.status
    )

    print(
        "[IMPORT STOCK] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    # Nếu API trả stock_quantity thì assert luôn
    if "stock_quantity" in body:
        assert float(body["stock_quantity"]) == 150

    # ==========================================
    # 6. Chờ reload
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 7. Tìm lại product
    # ==========================================

    updated_row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert updated_row is not None

    # ==========================================
    # 8. Stock trên UI phải = 150
    # ==========================================

    expect(updated_row).to_contain_text(
        "150"
    )


def test_admin_can_export_product_stock(
    admin_page,
    admin_test_product,
    base_url
):
    product_id = admin_test_product["id"]

    # ==========================================
    # 1. Tìm Product
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    # Stock ban đầu = 100
    expect(row).to_contain_text("100")

    # ==========================================
    # 2. Click Xuất
    # ==========================================

    export_button = row.get_by_role(
        "button",
        name="Xuất"
    )

    expect(export_button).to_be_visible()
    export_button.click()

    # ==========================================
    # 3. Modal Xuất kho phải hiện
    # ==========================================

    modal = admin_page.locator(
        "#stockActionModal"
    )

    expect(modal).to_be_visible()

    expect(
        admin_page.locator("#modalTitle")
    ).to_have_text(
        "Xuất Kho Sản Phẩm"
    )

    expect(
        admin_page.locator("#modalSubTitle")
    ).to_contain_text(
        admin_test_product["name"]
    )

    # ==========================================
    # 4. Xuất 30
    # ==========================================

    quantity = admin_page.locator(
        "#modalQuantity"
    )

    quantity.fill("30")

    expect(quantity).to_have_value("30")

    # ==========================================
    # 5. Xác nhận xuất kho thật qua UI
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/products/{product_id}/export"
            )
            and response.request.method == "POST"
    ) as response_info:

        admin_page.get_by_role(
            "button",
            name="Xác Nhận Xuất"
        ).click()

    response = response_info.value

    print(
        "\n[EXPORT STOCK] Status:",
        response.status
    )

    print(
        "[EXPORT STOCK] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    if "stock_quantity" in body:
        assert float(body["stock_quantity"]) == 70

    # ==========================================
    # 6. Chờ reload
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 7. Tìm lại Product
    # ==========================================

    updated_row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert updated_row is not None

    # ==========================================
    # 8. UI phải hiển thị tồn = 70
    # ==========================================

    expect(updated_row).to_contain_text(
        "70"
    )


def test_admin_cannot_export_more_than_stock(
    admin_page,
    admin_test_product,
    base_url
):
    product_id = admin_test_product["id"]

    # ==========================================
    # 1. Tìm Product
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    # Tồn ban đầu = 100
    expect(row).to_contain_text("100")

    # ==========================================
    # 2. Mở modal Xuất kho
    # ==========================================

    row.get_by_role(
        "button",
        name="Xuất"
    ).click()

    modal = admin_page.locator(
        "#stockActionModal"
    )

    expect(modal).to_be_visible()

    expect(
        admin_page.locator("#modalTitle")
    ).to_have_text(
        "Xuất Kho Sản Phẩm"
    )

    # ==========================================
    # 3. Nhập số lượng vượt tồn
    # 100 trong kho nhưng yêu cầu xuất 150
    # ==========================================

    quantity = admin_page.locator(
        "#modalQuantity"
    )

    quantity.fill("150")

    expect(quantity).to_have_value("150")

    # ==========================================
    # 4. Click Xác Nhận Xuất
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/products/{product_id}/export"
            )
            and response.request.method == "POST"
    ) as response_info:

        admin_page.get_by_role(
            "button",
            name="Xác Nhận Xuất"
        ).click()

    response = response_info.value

    print(
        "\n[EXPORT OVER STOCK] Status:",
        response.status
    )

    print(
        "[EXPORT OVER STOCK] Body:",
        response.text()
    )

    # ==========================================
    # 5. Backend phải từ chối
    # ==========================================

    assert not response.ok

    body = response.json()

    assert body["success"] is False

    # ==========================================
    # 6. UI phải báo lỗi
    # ==========================================

    error_toast = admin_page.locator(
        ".toast-error"
    )

    expect(error_toast).to_be_visible(
        timeout=5000
    )

    # Tạm thời không khóa cứng nguyên câu lỗi,
    # chỉ kiểm tra đúng ý nghĩa nghiệp vụ.
    expect(error_toast).to_contain_text(
        "tồn"
    )

    # ==========================================
    # 7. Modal vẫn còn để Admin sửa số lượng
    # ==========================================

    expect(modal).to_be_visible()

    # ==========================================
    # 8. Đóng modal
    # ==========================================

    admin_page.get_by_role(
        "button",
        name="Hủy"
    ).click()

    expect(modal).not_to_be_visible()

    # ==========================================
    # 9. Tồn kho trên UI phải giữ nguyên = 100
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None

    expect(row).to_contain_text(
        "100"
    )


def test_admin_sees_low_stock_warning(
    admin_page,
    admin_test_product,
    base_url
):
    product_id = admin_test_product["id"]
    product_name = admin_test_product["name"]

    # ==========================================
    # 1. Tìm Product
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    # Tồn ban đầu = 100
    expect(row).to_contain_text("100")

    # ==========================================
    # 2. Xuất 85 -> còn 15
    # min_stock = 20
    # ==========================================

    row.get_by_role(
        "button",
        name="Xuất"
    ).click()

    modal = admin_page.locator(
        "#stockActionModal"
    )

    expect(modal).to_be_visible()

    admin_page.locator(
        "#modalQuantity"
    ).fill("85")

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/products/{product_id}/export"
            )
            and response.request.method == "POST"
    ) as response_info:

        admin_page.get_by_role(
            "button",
            name="Xác Nhận Xuất"
        ).click()

    response = response_info.value

    assert response.ok

    body = response.json()

    assert body["success"] is True

    if "stock_quantity" in body:
        assert float(body["stock_quantity"]) == 15

    # ==========================================
    # 3. Chờ reload
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 4. Banner cảnh báo tồn thấp phải xuất hiện
    # ==========================================

    expect(
        admin_page.get_by_text(
            "Cảnh báo tồn kho thấp",
            exact=False
        )
    ).to_be_visible()

    # Banner phải nhắc đúng Product test
    expect(
        admin_page.locator("body")
    ).to_contain_text(
        product_name
    )

    expect(
        admin_page.locator("body")
    ).to_contain_text(
        "Tồn: 15 ML"
    )

    # ==========================================
    # 5. Row Product phải hiển thị tồn = 15
    # ==========================================

    updated_row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert updated_row is not None

    expect(updated_row).to_contain_text(
        "15"
    )

    # Min stock vẫn = 20
    expect(updated_row).to_contain_text(
        "20"
    )

    # ==========================================
    # 6. Icon cảnh báo tồn thấp
    # ==========================================

    warning_icon = updated_row.locator(
        'i[title="Cảnh báo tồn kho thấp!"]'
    )

    expect(warning_icon).to_be_visible()


def test_admin_can_delete_product(
    admin_page,
    admin_test_product,
    base_url
):
    product_id = admin_test_product["id"]
    product_name = admin_test_product["name"]

    # ==========================================
    # 1. Tìm Product qua pagination
    # ==========================================

    row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    expect(row).to_contain_text(
        product_name
    )

    # ==========================================
    # 2. Click nút Xóa
    # ==========================================

    delete_button = row.locator(
        'button[title="Xóa sản phẩm"]'
    )

    expect(delete_button).to_be_visible()

    delete_button.click()

    # ==========================================
    # 3. Custom confirm modal phải xuất hiện
    # ==========================================

    confirm_modal = admin_page.locator(
        "#custom-confirm-modal"
    )

    expect(confirm_modal).to_be_visible()

    expect(
        confirm_modal.get_by_text(
            "Xác nhận thao tác",
            exact=True
        )
    ).to_be_visible()

    # Kiểm tra message xác nhận
    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_contain_text(
        product_name
    )

    # ==========================================
    # 4. Click Xác nhận thật trên UI
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/products/{product_id}"
            )
            and response.request.method == "DELETE"
    ) as response_info:

        confirm_modal.get_by_role(
            "button",
            name="Xác nhận"
        ).click()

    response = response_info.value

    print(
        "\n[DELETE PRODUCT] Status:",
        response.status
    )

    print(
        "[DELETE PRODUCT] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 5. Chờ UI reload
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 6. Product vẫn tồn tại nhưng phải bị khóa
    # ==========================================

    deleted_row = find_product_row_across_pages(
        admin_page,
        product_id,
        base_url,
        max_pages=20
    )

    assert deleted_row is not None, (
        f"Không tìm thấy product #{product_id} "
        f"sau thao tác khóa"
    )

    expect(deleted_row).to_be_visible()

    # Vẫn đúng Product vừa thao tác
    expect(deleted_row).to_contain_text(
        product_name
    )

    # Nhưng phải chuyển sang trạng thái inactive
    expect(deleted_row).to_contain_text(
        "Đã khóa"
    )

    print(
        f"[TEST] Product #{product_id} "
        f"đã được khóa thành công trên UI"
    )