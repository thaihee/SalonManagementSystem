import uuid

from playwright.sync_api import expect

from test.e2e.utils.pagination import find_row_across_pages, find_service_row_across_pages


def test_admin_can_open_services_page(
    admin_page,
    base_url
):
    admin_page.goto(
        f"{base_url}/admin/services"
    )

    # ==========================================
    # 1. Heading
    # ==========================================

    expect(
        admin_page.get_by_role(
            "heading",
            name="Quản Lý Dịch Vụ & Định Mức"
        )
    ).to_be_visible()

    # ==========================================
    # 2. Nút thêm dịch vụ
    # ==========================================

    expect(
        admin_page.get_by_role(
            "button",
            name="Thêm Dịch Vụ Mới"
        )
    ).to_be_visible()

    # ==========================================
    # 3. Danh sách dịch vụ
    # ==========================================

    expect(
        admin_page.get_by_text(
            "Danh Sách Dịch Vụ Salon",
            exact=False
        )
    ).to_be_visible()

    # ==========================================
    # 4. Các cột chính
    # ==========================================

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Tên Dịch Vụ"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Đơn Giá"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Thời Lượng"
        )
    ).to_be_visible()


def test_admin_can_create_service(
    admin_page,
    admin_test_service,
    base_url
):
    service_id = admin_test_service["id"]
    service_name = admin_test_service["name"]

    # Tìm service vừa tạo qua pagination
    row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url
    )

    assert row is not None, (
        f"Không tìm thấy service #{service_id}"
    )

    expect(row).to_be_visible()

    expect(row).to_contain_text(
        service_name
    )

    expect(row).to_contain_text(
        "250,000 đ"
    )

    expect(row).to_contain_text(
        "60 phút"
    )

    expect(row).to_contain_text(
        "Dịch vụ được tạo bởi Playwright E2E"
    )


def test_admin_can_edit_service(
    admin_page,
    admin_test_service,
    base_url
):
    service_id = admin_test_service["id"]

    # ==========================================
    # 1. Tìm service test qua pagination
    # ==========================================

    row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url
    )

    assert row is not None, (
        f"Không tìm thấy service #{service_id}"
    )

    expect(row).to_be_visible()

    # ==========================================
    # 2. Click Sửa
    # ==========================================

    row.get_by_role(
        "button",
        name="Sửa"
    ).click()

    # ==========================================
    # 3. Form edit phải hiện
    # ==========================================

    edit_row = admin_page.locator(
        f"#edit_service_row_{service_id}"
    )

    expect(edit_row).to_be_visible()

    # ==========================================
    # 4. Sửa dữ liệu qua UI
    # ==========================================

    new_name = f"{admin_test_service['name']}_UPDATED"

    admin_page.locator(
        f"#edit_name_{service_id}"
    ).fill(new_name)

    admin_page.locator(
        f"#edit_price_{service_id}"
    ).fill("320000")

    admin_page.locator(
        f"#edit_duration_{service_id}"
    ).fill("75")

    admin_page.locator(
        f"#edit_desc_{service_id}"
    ).fill(
        "Dịch vụ đã được cập nhật bởi Playwright E2E"
    )

    # ==========================================
    # 5. Click Lưu thật
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            f"/admin/services/{service_id}" in response.url
            and response.request.method in ("PUT", "PATCH")
    ) as response_info:
        edit_row.get_by_role(
            "button",
            name="Lưu Dịch Vụ"
        ).click()

    response = response_info.value

    print(
        f"\n[EDIT SERVICE] Status: {response.status}"
    )

    print(
        "[EDIT SERVICE] Body:",
        response.text()
    )

    assert response.ok

    # ==========================================
    # 6. Chờ UI reload
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 7. Tìm lại service qua pagination
    # ==========================================

    updated_row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url
    )

    assert updated_row is not None

    expect(updated_row).to_be_visible()

    # ==========================================
    # 8. UI phải hiển thị dữ liệu mới
    # ==========================================

    expect(updated_row).to_contain_text(
        new_name
    )

    expect(updated_row).to_contain_text(
        "320,000 đ"
    )

    expect(updated_row).to_contain_text(
        "75 phút"
    )

    expect(updated_row).to_contain_text(
        "Dịch vụ đã được cập nhật bởi Playwright E2E"
    )

    # Dữ liệu cũ không còn
    expect(updated_row).not_to_contain_text(
        "250,000 đ"
    )

    expect(updated_row).not_to_contain_text(
        "60 phút"
    )


def test_admin_can_add_product_norm_to_service(
    admin_page,
    admin_test_service,
    base_url
):
    service_id = admin_test_service["id"]

    # ==========================================
    # 1. Tìm service test qua pagination
    # ==========================================

    row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url
    )

    assert row is not None

    expect(row).to_be_visible()

    # ==========================================
    # 2. Mở khu vực Định mức
    # ==========================================

    row.get_by_role(
        "button",
        name="Định mức"
    ).click()

    norm_row = admin_page.locator(
        f"#norm_row_{service_id}"
    )

    expect(norm_row).to_be_visible()

    # Khi mở row, JS sẽ gọi:
    # GET /admin/services/<id>/products

    norm_container = admin_page.locator(
        f"#norm_list_container_{service_id}"
    )

    expect(norm_container).to_be_visible()

    # Service mới tạo chưa có định mức
    expect(norm_container).to_contain_text(
        "Dịch vụ này chưa được gán định mức sản phẩm nào"
    )

    # ==========================================
    # 3. Chọn Product từ UI
    # ==========================================

    product_select = admin_page.locator(
        f"#add_product_select_{service_id}"
    )

    expect(product_select).to_be_visible()

    # Dùng sản phẩm seed có sẵn
    product_select.select_option(
        label="Dầu gội (ĐVT: ML)"
    )

    # ==========================================
    # 4. Nhập định mức
    # ==========================================

    quantity_input = admin_page.locator(
        f"#add_product_qty_{service_id}"
    )

    quantity_input.fill("25")

    expect(quantity_input).to_have_value("25")

    # ==========================================
    # 5. Click Thêm Định Mức thật
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                "/admin/service-products"
            )
            and response.request.method == "POST"
    ) as response_info:

        norm_row.get_by_role(
            "button",
            name="Thêm Định Mức"
        ).click()

    response = response_info.value

    print(
        f"\n[ADD SERVICE PRODUCT] Status:",
        response.status
    )

    print(
        "[ADD SERVICE PRODUCT] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 6. UI phải reload danh sách định mức
    # ==========================================

    expect(norm_container).to_contain_text(
        "Dầu gội"
    )

    expect(norm_container).to_contain_text(
        "Định mức gợi ý:"
    )

    # ==========================================
    # 7. Input quantity mới phải xuất hiện
    # ==========================================

    quantity_inputs = norm_container.locator(
        'input[type="number"]'
    )

    expect(quantity_inputs).to_have_count(1)

    expect(
        quantity_inputs.first
    ).to_have_value("25")

    # ==========================================
    # 8. Có thao tác Lưu + Xóa
    # ==========================================

    expect(
        norm_container.get_by_role(
            "button",
            name="Lưu"
        )
    ).to_be_visible()

    expect(
        norm_container.get_by_role(
            "button",
            name="Xóa"
        )
    ).to_be_visible()


def test_admin_can_update_product_norm(
    admin_page,
    admin_test_service,
    base_url
):
    service_id = admin_test_service["id"]

    # ==========================================
    # 1. Tìm Service qua pagination
    # ==========================================

    row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    # ==========================================
    # 2. Mở khu vực Định mức
    # ==========================================

    row.get_by_role(
        "button",
        name="Định mức"
    ).click()

    norm_row = admin_page.locator(
        f"#norm_row_{service_id}"
    )

    expect(norm_row).to_be_visible()

    norm_container = admin_page.locator(
        f"#norm_list_container_{service_id}"
    )

    # Chờ request load định mức ban đầu xong
    expect(norm_container).to_contain_text(
        "Dịch vụ này chưa được gán định mức sản phẩm nào"
    )

    # ==========================================
    # 3. Tạo định mức ban đầu = 25 qua UI
    # ==========================================

    product_select = admin_page.locator(
        f"#add_product_select_{service_id}"
    )

    product_select.select_option(
        label="Dầu gội (ĐVT: ML)"
    )

    admin_page.locator(
        f"#add_product_qty_{service_id}"
    ).fill("25")

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                "/admin/service-products"
            )
            and response.request.method == "POST"
    ) as response_info:

        norm_row.get_by_role(
            "button",
            name="Thêm Định Mức"
        ).click()

    assert response_info.value.ok

    # ==========================================
    # 4. Chờ Product xuất hiện trên UI
    # ==========================================

    expect(norm_container).to_contain_text(
        "Dầu gội"
    )

    quantity_input = norm_container.locator(
        'input[type="number"]'
    ).first

    expect(quantity_input).to_have_value("25")

    # ==========================================
    # 5. Sửa định mức 25 -> 40
    # ==========================================

    quantity_input.fill("40")

    expect(quantity_input).to_have_value("40")

    # ==========================================
    # 6. Click Lưu thật
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            "/admin/service-products/" in response.url
            and response.request.method == "PUT"
    ) as response_info:

        norm_container.get_by_role(
            "button",
            name="Lưu"
        ).click()

    response = response_info.value

    print(
        "\n[UPDATE SERVICE PRODUCT] Status:",
        response.status
    )

    print(
        "[UPDATE SERVICE PRODUCT] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()
    assert body["success"] is True

    # ==========================================
    # 7. UI reload lại định mức
    # ==========================================

    expect(norm_container).to_contain_text(
        "Dầu gội"
    )

    updated_quantity = norm_container.locator(
        'input[type="number"]'
    ).first

    # Quan trọng:
    # chứng minh giá trị server trả lại sau reload là 40
    expect(updated_quantity).to_have_value("40")


def test_admin_can_delete_product_norm(
    admin_page,
    admin_test_service,
    base_url
):
    service_id = admin_test_service["id"]

    # ==========================================
    # 1. Tìm Service qua pagination
    # ==========================================

    row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    # ==========================================
    # 2. Mở khu vực Định mức
    # ==========================================

    row.get_by_role(
        "button",
        name="Định mức"
    ).click()

    norm_row = admin_page.locator(
        f"#norm_row_{service_id}"
    )

    expect(norm_row).to_be_visible()

    norm_container = admin_page.locator(
        f"#norm_list_container_{service_id}"
    )

    expect(norm_container).to_contain_text(
        "Dịch vụ này chưa được gán định mức sản phẩm nào"
    )

    # ==========================================
    # 3. Tạo định mức Dầu gội = 25
    # ==========================================

    product_select = admin_page.locator(
        f"#add_product_select_{service_id}"
    )

    product_select.select_option(
        label="Dầu gội (ĐVT: ML)"
    )

    admin_page.locator(
        f"#add_product_qty_{service_id}"
    ).fill("25")

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                "/admin/service-products"
            )
            and response.request.method == "POST"
    ) as response_info:

        norm_row.get_by_role(
            "button",
            name="Thêm Định Mức"
        ).click()

    assert response_info.value.ok

    # ==========================================
    # 4. Định mức phải xuất hiện
    # ==========================================

    expect(norm_container).to_contain_text(
        "Dầu gội"
    )

    quantity_input = norm_container.locator(
        'input[type="number"]'
    ).first

    expect(quantity_input).to_have_value("25")

    # ==========================================
    # 5. Click Xóa
    # ==========================================

    norm_container.get_by_role(
        "button",
        name="Xóa"
    ).click()

    # ==========================================
    # 6. Custom confirm modal phải xuất hiện
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

    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_contain_text(
        "Xóa sản phẩm này khỏi định mức dịch vụ?"
    )

    # ==========================================
    # 7. Click Xác nhận thật trên UI
    # ==========================================

    with admin_page.expect_response(
            lambda response:
            "/admin/service-products/" in response.url
            and response.request.method == "DELETE"
    ) as response_info:
        confirm_modal.get_by_role(
            "button",
            name="Xác nhận"
        ).click()

    response = response_info.value

    print(
        "\n[DELETE SERVICE PRODUCT] Status:",
        response.status
    )

    print(
        "[DELETE SERVICE PRODUCT] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 8. UI phải trở về trạng thái chưa có định mức
    # ==========================================

    expect(norm_container).to_contain_text(
        "Dịch vụ này chưa được gán định mức sản phẩm nào"
    )

    expect(
        norm_container.get_by_text(
            "Dầu gội",
            exact=True
        )
    ).to_have_count(0)

    expect(
        norm_container.locator(
            'input[type="number"]'
        )
    ).to_have_count(0)


def test_admin_can_delete_service(
    admin_page,
    admin_test_service,
    base_url
):
    service_id = admin_test_service["id"]
    service_name = admin_test_service["name"]

    # ==========================================
    # 1. Tìm Service qua pagination
    # ==========================================

    row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url
    )

    assert row is not None, (
        f"Không tìm thấy service #{service_id}"
    )

    expect(row).to_be_visible()

    expect(row).to_contain_text(
        service_name
    )

    # ==========================================
    # 2. Click nút thùng rác trên UI
    # ==========================================

    # Nút delete không có text,
    # nên lấy button cuối cùng trong row
    delete_button = row.locator(
        "button"
    ).last

    expect(delete_button).to_be_visible()

    delete_button.click()

    # ==========================================
    # 3. Custom confirm modal phải hiện
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

    # Message phải liên quan đúng Service
    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_contain_text(
        service_name
    )

    # ==========================================
    # 4. Click Xác nhận thật
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/services/{service_id}"
            )
            and response.request.method == "DELETE"
    ) as response_info:

        confirm_modal.get_by_role(
            "button",
            name="Xác nhận"
        ).click()

    response = response_info.value

    print(
        f"\n[DELETE SERVICE] Status: "
        f"{response.status}"
    )

    print(
        "[DELETE SERVICE] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 5. Chờ trang reload
    # ==========================================

    # Chờ JS reload sau delete
    admin_page.wait_for_timeout(1200)

    # Đi về page 1
    admin_page.goto(
        f"{base_url}/admin/services?page=1"
    )

    # Kiểm tra service không còn bằng helper có giới hạn
    deleted_row = find_service_row_across_pages(
        admin_page,
        service_id,
        base_url,
        max_pages=20
    )

    assert deleted_row is None