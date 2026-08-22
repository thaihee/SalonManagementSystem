import re
import uuid

from playwright.sync_api import expect

from app import db, app
from app.models import User
from test.e2e.utils.pagination import find_user_row_across_pages


def test_admin_can_open_staff_management_page(
    admin_page,
    base_url
):
    # ==========================================
    # 1. Mở trang
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/users"
    )

    # ==========================================
    # 2. URL đúng
    # ==========================================

    expect(admin_page).to_have_url(
        re.compile(r".*/admin/users.*")
    )

    # ==========================================
    # 3. Heading
    # ==========================================

    expect(
        admin_page.get_by_role(
            "heading",
            name="Quản Lý Nhân Viên & Tài Khoản"
        )
    ).to_be_visible()

    # ==========================================
    # 4. Nút Create
    # ==========================================

    expect(
        admin_page.get_by_role(
            "button",
            name="Tạo Nhân Viên Mới"
        )
    ).to_be_visible()

    # ==========================================
    # 5. Bộ lọc role
    # ==========================================

    expect(
        admin_page.get_by_role(
            "link",
            name="Tất cả"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "link",
            name="Stylist"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "link",
            name="Lễ Tân"
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_role(
            "link",
            name="Khách Hàng"
        )
    ).to_be_visible()

    # ==========================================
    # 6. Bảng tài khoản
    # ==========================================

    expect(
        admin_page.get_by_text(
            "Danh Sách Tài Khoản Hệ Thống",
            exact=False
        )
    ).to_be_visible()

    # ==========================================
    # 7. Các cột nghiệp vụ chính
    # ==========================================

    for column_name in [
        "Họ Và Tên",
        "Tên Đăng Nhập",
        "Vai Trò",
        "Số Điện Thoại",
        "Email",
        "Thao Tác",
    ]:
        expect(
            admin_page.get_by_role(
                "columnheader",
                name=column_name
            )
        ).to_be_visible()


def test_admin_can_filter_users_by_role(
    admin_page,
    base_url
):
    # ==========================================
    # 1. Mở trang Users
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/users"
    )

    # ==========================================
    # 2. Filter STYLIST
    # ==========================================

    admin_page.get_by_role(
        "link",
        name="Stylist",
        exact=True
    ).click()

    expect(admin_page).to_have_url(
        re.compile(
            r".*/admin/users\?.*role=STAFF.*"
        )
    )

    # Bảng phải có ít nhất 1 Stylist
    stylist_badges = admin_page.get_by_text(
        "STYLIST",
        exact=True
    )

    expect(
        stylist_badges.first
    ).to_be_visible()

    # Không được có role khác trong dữ liệu
    expect(
        admin_page.get_by_text(
            "LỄ TÂN",
            exact=True
        )
    ).to_have_count(0)

    expect(
        admin_page.get_by_text(
            "K.HÀNG",
            exact=True
        )
    ).to_have_count(0)

    # ==========================================
    # 3. Filter RECEPTIONIST
    # ==========================================

    admin_page.get_by_role(
        "link",
        name="Lễ Tân",
        exact=True
    ).click()

    expect(admin_page).to_have_url(
        re.compile(
            r".*/admin/users\?.*role=RECEPTIONIST.*"
        )
    )

    receptionist_badges = admin_page.get_by_text(
        "LỄ TÂN",
        exact=True
    )

    expect(
        receptionist_badges.first
    ).to_be_visible()

    # Không được lẫn Stylist / Customer
    expect(
        admin_page.get_by_text(
            "STYLIST",
            exact=True
        )
    ).to_have_count(0)

    expect(
        admin_page.get_by_text(
            "K.HÀNG",
            exact=True
        )
    ).to_have_count(0)

    # ==========================================
    # 4. Quay lại Tất cả
    # ==========================================

    admin_page.get_by_role(
        "link",
        name="Tất cả",
        exact=True
    ).click()

    expect(admin_page).to_have_url(
        re.compile(
            r".*/admin/users(?:\?page=\d+)?$"
        )
    )


def test_admin_can_create_staff(
    admin_page,
    base_url
):
    user_id = None

    unique = uuid.uuid4().hex[:8]

    full_name = f"E2E Stylist {unique}"
    username = f"e2estaff{unique}"
    email = f"{username}@test.com"
    phone = f"09{uuid.uuid4().int % 100000000:08d}"

    try:
        # ==========================================
        # 1. Mở trang quản lý tài khoản
        # ==========================================

        admin_page.goto(
            f"{base_url}/admin/users"
        )

        # ==========================================
        # 2. Mở form Create
        # ==========================================

        admin_page.get_by_role(
            "button",
            name="Tạo Nhân Viên Mới"
        ).click()

        form = admin_page.locator(
            "#createStaffForm"
        )

        expect(form).to_be_visible()

        # ==========================================
        # 3. Điền dữ liệu qua UI
        # ==========================================

        form.locator(
            '[name="full_name"]'
        ).fill(full_name)

        form.locator(
            '[name="username"]'
        ).fill(username)

        form.locator(
            '[name="password"]'
        ).fill("Password123")

        form.locator(
            '[name="role"]'
        ).select_option("STAFF")

        form.locator(
            '[name="phone"]'
        ).fill(phone)

        form.locator(
            '[name="email"]'
        ).fill(email)

        # ==========================================
        # 4. Submit thật qua UI
        # ==========================================

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

        print(
            "\n[CREATE STAFF] Status:",
            response.status
        )

        print(
            "[CREATE STAFF] Body:",
            response.text()
        )

        assert response.status == 201

        body = response.json()

        assert body["success"] is True

        user_id = body["user"]["id"]

        assert body["user"]["username"] == username
        assert body["user"]["role"] == "STAFF"

        print(
            f"\n[TEST] Đã tạo Staff "
            f"#{user_id} - {username}"
        )

        # ==========================================
        # 5. Chờ UI cập nhật
        # ==========================================

        admin_page.wait_for_load_state(
            "networkidle"
        )

        # ==========================================
        # 6. Tìm Staff qua pagination
        # ==========================================

        row = find_user_row_across_pages(
            admin_page,
            user_id,
            base_url
        )

        assert row is not None, (
            f"Không tìm thấy Staff #{user_id}"
        )

        expect(row).to_be_visible()

        # ==========================================
        # 7. Kiểm tra dữ liệu trên giao diện
        # ==========================================

        expect(row).to_contain_text(
            full_name
        )

        expect(row).to_contain_text(
            username
        )

        expect(row).to_contain_text(
            "STYLIST"
        )

        expect(row).to_contain_text(
            phone
        )

        expect(row).to_contain_text(
            email
        )

    finally:
        # ==========================================
        # TEARDOWN
        # ==========================================

        if user_id is not None:

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


def test_admin_can_edit_staff(
    admin_page,
    admin_test_staff,
    base_url
):
    user_id = admin_test_staff["id"]
    username = admin_test_staff["username"]

    unique = uuid.uuid4().hex[:6]

    new_full_name = (
        f"E2E Stylist Edited {unique}"
    )

    new_phone = (
        f"08{uuid.uuid4().int % 100000000:08d}"
    )

    new_email = (
        f"edited{unique}@test.com"
    )

    # ==========================================
    # 1. Tìm Staff qua pagination
    # ==========================================

    row = find_user_row_across_pages(
        admin_page,
        user_id,
        base_url
    )

    assert row is not None

    expect(row).to_be_visible()

    expect(row).to_contain_text(
        username
    )

    # ==========================================
    # 2. Click nút Sửa
    # ==========================================

    edit_button = row.get_by_role(
        "button",
        name="Sửa",
        exact=False
    )

    expect(edit_button).to_be_visible()

    edit_button.click()

    # ==========================================
    # 3. Inline edit row phải hiện
    # ==========================================

    edit_row = admin_page.locator(
        f"#edit_staff_row_{user_id}"
    )

    expect(edit_row).to_be_visible()

    full_name_input = admin_page.locator(
        f"#edit_fullname_{user_id}"
    )

    phone_input = admin_page.locator(
        f"#edit_phone_{user_id}"
    )

    email_input = admin_page.locator(
        f"#edit_email_{user_id}"
    )

    # ==========================================
    # 4. Dữ liệu cũ phải được load đúng
    # ==========================================

    expect(full_name_input).to_have_value(
        admin_test_staff["full_name"]
    )

    expect(phone_input).to_have_value(
        admin_test_staff["phone"]
    )

    expect(email_input).to_have_value(
        admin_test_staff["email"]
    )

    # ==========================================
    # 5. Sửa dữ liệu qua UI
    # ==========================================

    full_name_input.fill(
        new_full_name
    )

    phone_input.fill(
        new_phone
    )

    email_input.fill(
        new_email
    )

    expect(full_name_input).to_have_value(
        new_full_name
    )

    expect(phone_input).to_have_value(
        new_phone
    )

    expect(email_input).to_have_value(
        new_email
    )

    # ==========================================
    # 6. Click Lưu Thay Đổi
    # ==========================================

    with admin_page.expect_response(
            lambda response:
            response.url.endswith(
                f"/users/{user_id}"
            )
            and response.request.method == "PUT"
    ) as response_info:
        edit_row.get_by_role(
            "button",
            name="Lưu Thay Đổi"
        ).click()

    response = response_info.value

    print(
        "\n[EDIT STAFF] Status:",
        response.status
    )

    print(
        "[EDIT STAFF] Body:",
        response.text()
    )

    assert response.status == 200

    body = response.json()

    assert body["success"] is True

    # ==========================================
    # 7. API cũng phải trả dữ liệu mới
    # ==========================================

    assert (
        body["user"]["full_name"]
        == new_full_name
    )

    assert (
        body["user"]["phone"]
        == new_phone
    )

    assert (
        body["user"]["email"]
        == new_email
    )

    # ==========================================
    # 8. Chờ UI cập nhật
    # ==========================================

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 9. Tìm lại Staff
    # ==========================================

    updated_row = find_user_row_across_pages(
        admin_page,
        user_id,
        base_url
    )

    assert updated_row is not None

    expect(updated_row).to_be_visible()

    # ==========================================
    # 10. Row phải hiển thị dữ liệu mới
    # ==========================================

    expect(updated_row).to_contain_text(
        new_full_name
    )

    expect(updated_row).to_contain_text(
        new_phone
    )

    expect(updated_row).to_contain_text(
        new_email
    )

    # Username không được thay đổi
    expect(updated_row).to_contain_text(
        username
    )


def test_admin_can_lock_and_unlock_staff(
    admin_page,
    admin_test_staff,
    base_url
):
    user_id = admin_test_staff["id"]
    full_name = admin_test_staff["full_name"]

    # ==========================================
    # 1. Tìm Staff đang hoạt động
    # ==========================================

    row = find_user_row_across_pages(
        admin_page,
        user_id,
        base_url
    )

    assert row is not None
    expect(row).to_be_visible()

    expect(row).to_contain_text(
        full_name
    )

    # Staff mới tạo chưa bị khóa
    expect(
        row.get_by_text(
            "Đã khóa",
            exact=True
        )
    ).to_have_count(0)

    # ==========================================
    # 2. Click Khóa
    # ==========================================

    lock_button = row.locator(
        'button[title="Vô hiệu hóa tài khoản"]'
    )

    expect(lock_button).to_be_visible()

    lock_button.click()

    # ==========================================
    # 3. Custom confirm xuất hiện
    # ==========================================

    confirm_modal = admin_page.locator(
        "#custom-confirm-modal"
    )

    expect(confirm_modal).to_be_visible()

    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_contain_text(
        full_name
    )

    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_contain_text(
        "vô hiệu hóa"
    )

    # ==========================================
    # 4. Xác nhận khóa
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/users/{user_id}/toggle-active"
            )
            and response.request.method == "PATCH"
    ) as response_info:

        confirm_modal.get_by_role(
            "button",
            name="Xác nhận"
        ).click()

    response = response_info.value

    print(
        "\n[LOCK STAFF] Status:",
        response.status
    )

    print(
        "[LOCK STAFF] Body:",
        response.text()
    )

    assert response.status == 200

    body = response.json()

    assert body["success"] is True
    assert body["active"] is False

    # JS đợi 1 giây rồi mới reload
    admin_page.wait_for_timeout(1200)

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 5. Tìm lại Staff sau khi khóa
    # ==========================================

    locked_row = find_user_row_across_pages(
        admin_page,
        user_id,
        base_url
    )

    assert locked_row is not None
    expect(locked_row).to_be_visible()

    # UI phải báo đã khóa
    expect(
        locked_row.get_by_text(
            "Đã khóa",
            exact=True
        )
    ).to_be_visible()

    # Nút phải đổi thành Mở khóa
    unlock_button = locked_row.locator(
        'button[title="Kích hoạt lại tài khoản"]'
    )

    expect(unlock_button).to_be_visible()

    # ==========================================
    # 6. Click Mở khóa
    # ==========================================

    unlock_button.click()

    expect(confirm_modal).to_be_visible()

    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_contain_text(
        full_name
    )

    expect(
        confirm_modal.locator(
            "#confirm-modal-msg"
        )
    ).to_contain_text(
        "mở khóa"
    )

    # ==========================================
    # 7. Xác nhận mở khóa
    # ==========================================

    with admin_page.expect_response(
        lambda response:
            response.url.endswith(
                f"/users/{user_id}/toggle-active"
            )
            and response.request.method == "PATCH"
    ) as response_info:

        confirm_modal.get_by_role(
            "button",
            name="Xác nhận"
        ).click()

    response = response_info.value

    print(
        "\n[UNLOCK STAFF] Status:",
        response.status
    )

    print(
        "[UNLOCK STAFF] Body:",
        response.text()
    )

    assert response.status == 200

    body = response.json()

    assert body["success"] is True
    assert body["active"] is True

    admin_page.wait_for_timeout(1200)

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 8. Kiểm tra Staff hoạt động trở lại
    # ==========================================

    unlocked_row = find_user_row_across_pages(
        admin_page,
        user_id,
        base_url
    )

    assert unlocked_row is not None
    expect(unlocked_row).to_be_visible()

    # Badge Đã khóa phải biến mất
    expect(
        unlocked_row.get_by_text(
            "Đã khóa",
            exact=True
        )
    ).to_have_count(0)

    # Nút Khóa phải trở lại
    expect(
        unlocked_row.locator(
            'button[title="Vô hiệu hóa tài khoản"]'
        )
    ).to_be_visible()