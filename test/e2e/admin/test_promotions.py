import re
import uuid
from datetime import date, timedelta

from playwright.sync_api import expect

from app import db, app
from app.models import Promotion
from test.e2e.utils.pagination import find_promotion_row_across_pages


def test_admin_can_open_promotions_page(
    admin_page,
    base_url
):
    # ==========================================
    # 1. Mở trang Promotions
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/promotions"
    )

    # ==========================================
    # 2. Đúng URL
    # ==========================================

    expect(admin_page).to_have_url(
        re.compile(r".*/admin/promotions.*")
    )

    # ==========================================
    # 3. Heading chính
    # ==========================================

    expect(
        admin_page.get_by_role(
            "heading",
            name="Quản Lý Khuyến Mãi"
        )
    ).to_be_visible()

    # ==========================================
    # 4. Nút thêm mã
    # ==========================================

    expect(
        admin_page.get_by_role(
            "button",
            name="Thêm Mã Mới"
        )
    ).to_be_visible()

    # ==========================================
    # 5. Bảng Promotions
    # ==========================================

    expect(
        admin_page.locator(
            "#promoTableBody"
        )
    ).to_be_visible()

    # ==========================================
    # 6. Các cột nghiệp vụ chính
    # ==========================================

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Mã Promotion"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Loại Giảm Giá"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Giá Trị"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Thời Gian Áp Dụng"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "columnheader",
            name="Trạng Thái"
        )
    ).to_be_visible()


def test_admin_can_edit_promotion(
    admin_page,
    admin_test_promotion,
    base_url
):
    promotion_id = admin_test_promotion["id"]
    old_code = admin_test_promotion["code"]

    new_code = (
        f"EDIT_{uuid.uuid4().hex[:8].upper()}"
    )

    # ==========================================
    # 1. Tìm Promotion qua pagination
    # ==========================================

    row = find_promotion_row_across_pages(
        admin_page,
        promotion_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    expect(row).to_contain_text(
        old_code
    )

    # ==========================================
    # 2. Click nút Chỉnh sửa
    # ==========================================

    edit_button = row.locator(
        'button[title="Chỉnh sửa"]'
    )

    expect(edit_button).to_be_visible()

    edit_button.click()

    # ==========================================
    # 3. Modal Edit phải hiện
    # ==========================================

    modal = admin_page.locator(
        "#promoModal"
    )

    expect(modal).to_be_visible()

    expect(
        modal.locator("#modalTitle")
    ).to_have_text(
        "Chỉnh Sửa Mã Khuyến Mãi"
    )

    # ==========================================
    # 4. Chỉnh dữ liệu bằng UI
    # ==========================================

    modal.locator(
        "#promo_code"
    ).fill(new_code)

    modal.locator(
        "#promo_type"
    ).select_option(
        "FIXED"
    )

    modal.locator(
        "#value"
    ).fill(
        "50000"
    )

    # Kiểm tra UI đã nhận dữ liệu mới
    expect(
        modal.locator("#promo_code")
    ).to_have_value(
        new_code
    )

    expect(
        modal.locator("#promo_type")
    ).to_have_value(
        "FIXED"
    )

    expect(
        modal.locator("#value")
    ).to_have_value(
        "50000"
    )

    # ==========================================
    # 5. Lưu thay đổi
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/promotions/{promotion_id}"
            )
            and response.request.method == "PUT"
    ) as response_info:

        modal.locator(
            "#btnSubmitForm"
        ).click()

    response = response_info.value

    print(
        "\n[EDIT PROMOTION] Status:",
        response.status
    )

    print(
        "[EDIT PROMOTION] Body:",
        response.text()
    )

    assert response.ok

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 6. Chờ UI cập nhật
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 7. Tìm lại Promotion
    # ==========================================

    updated_row = find_promotion_row_across_pages(
        admin_page,
        promotion_id,
        base_url
    )

    assert updated_row is not None

    expect(updated_row).to_be_visible()

    # ==========================================
    # 8. UI phải phản ánh dữ liệu mới
    # ==========================================

    expect(updated_row).to_contain_text(
        new_code
    )

    expect(updated_row).to_contain_text(
        "Số Tiền Cố Định"
    )

    expect(updated_row).to_contain_text(
        "Giảm 50,000 đ"
    )


def test_admin_cannot_create_promotion_with_invalid_date_range(
    admin_page,
    base_url
):
    promo_code = (
        f"E2E_INVALID_{uuid.uuid4().hex[:8].upper()}"
    )

    start_date = date.today()
    end_date = start_date - timedelta(days=1)

    # ==========================================
    # 1. Mở trang Promotions
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/promotions"
    )

    # ==========================================
    # 2. Mở modal Create
    # ==========================================

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

    # ==========================================
    # 3. Nhập dữ liệu
    # ==========================================

    modal.locator(
        "#promo_code"
    ).fill(
        promo_code
    )

    modal.locator(
        "#promo_type"
    ).select_option(
        "PERCENT"
    )

    modal.locator(
        "#value"
    ).fill(
        "15"
    )

    # Start = hôm nay
    modal.locator(
        "#start_date"
    ).fill(
        start_date.isoformat()
    )

    # End = hôm qua -> không hợp lệ
    modal.locator(
        "#end_date"
    ).fill(
        end_date.isoformat()
    )

    expect(
        modal.locator("#start_date")
    ).to_have_value(
        start_date.isoformat()
    )

    expect(
        modal.locator("#end_date")
    ).to_have_value(
        end_date.isoformat()
    )

    # ==========================================
    # 4. Submit thật qua UI
    # ==========================================

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

    print(
        "\n[INVALID PROMOTION DATE] Status:",
        response.status
    )

    print(
        "[INVALID PROMOTION DATE] Body:",
        response.text()
    )

    # ==========================================
    # 5. Backend phải từ chối
    # ==========================================

    assert not response.ok

    body = response.json()

    assert body["success"] is False

    # ==========================================
    # 6. Modal vẫn phải mở
    # ==========================================
    # Không được coi đây là create thành công.

    expect(modal).to_be_visible()

    # Dữ liệu người dùng nhập vẫn còn
    expect(
        modal.locator("#promo_code")
    ).to_have_value(
        promo_code
    )

    # ==========================================
    # 7. UI phải có thông báo lỗi
    # ==========================================

    error_toast = admin_page.locator(
        ".toast-error"
    )

    expect(
        error_toast
    ).to_be_visible(
        timeout=5000
    )


def test_admin_can_delete_promotion(
    admin_page,
    admin_test_promotion,
    base_url
):
    promotion_id = admin_test_promotion["id"]
    promo_code = admin_test_promotion["code"]

    # ==========================================
    # 1. Tìm Promotion qua pagination
    # ==========================================

    row = find_promotion_row_across_pages(
        admin_page,
        promotion_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    expect(row).to_contain_text(
        promo_code
    )

    # ==========================================
    # 2. Click nút Xóa
    # ==========================================

    delete_button = row.locator(
        'button[title="Xóa"]'
    )

    expect(delete_button).to_be_visible()

    delete_button.click()

    # ==========================================
    # 3. Custom confirm phải xuất hiện
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

    # Message xác nhận đúng với UI thực tế
    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_have_text(
        "Bạn có chắc chắn muốn xóa mã khuyến mãi này?"
    )

    # ==========================================
    # 4. Xác nhận xóa thật qua UI
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/admin/promotions/{promotion_id}"
            )
            and response.request.method == "DELETE"
    ) as response_info:

        confirm_modal.get_by_role(
            "button",
            name="Xác nhận"
        ).click()

    response = response_info.value

    print(
        "\n[DELETE PROMOTION] Status:",
        response.status
    )

    print(
        "[DELETE PROMOTION] Body:",
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
    # 6. Tìm lại Promotion
    # ==========================================

    deleted_row = find_promotion_row_across_pages(
        admin_page,
        promotion_id,
        base_url
    )

    # Promotion của module này có thể:
    #
    # A. hard delete -> row biến mất
    #
    # B. soft delete/deactivate -> row vẫn còn
    #    nhưng chuyển trạng thái.
    #
    # Trước mắt in behavior thật để xác định.

    if deleted_row is None:

        print(
            f"[TEST] Promotion #{promotion_id} "
            f"đã biến mất khỏi danh sách "
            f"(hard delete)"
        )

    else:

        expect(deleted_row).to_be_visible()

        print(
            f"[TEST] Promotion #{promotion_id} "
            f"vẫn còn sau DELETE."
        )

        print(
            "[TEST] Row sau DELETE:",
            deleted_row.inner_text()
        )