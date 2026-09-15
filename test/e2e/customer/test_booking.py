from datetime import date, timedelta
import re
from playwright.sync_api import expect
from test.e2e.utils.pagination import find_row_across_pages


def test_customer_can_open_booking_page(customer_page, base_url):
    customer_page.goto(f"{base_url}/booking")

    # Tiêu đề
    expect(
        customer_page.get_by_role(
            "heading",
            name="Đặt Lịch Trải Nghiệm Dịch Vụ"
        )
    ).to_be_visible()

    # Danh sách dịch vụ
    expect(
        customer_page.locator(".service-select-card").first
    ).to_be_visible()

    # Chọn stylist
    expect(
        customer_page.locator("#staff_id")
    ).to_be_visible()

    # Chọn ngày
    expect(
        customer_page.locator("#date")
    ).to_be_visible()

    # Khu vực giờ trống
    expect(
        customer_page.locator("#slots-container")
    ).to_be_visible()

    # Ghi chú
    expect(
        customer_page.locator("#note")
    ).to_be_visible()

    # Nút submit
    expect(
        customer_page.locator("#btn-submit-booking")
    ).to_be_visible()

def test_customer_can_load_available_slots(customer_page, base_url):
    customer_page.goto(f"{base_url}/booking")

    tomorrow = (
        date.today() + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    customer_page.locator("#date").fill(tomorrow)

    first_slot = customer_page.locator(".slot-btn").first

    expect(first_slot).to_be_visible(timeout=10000)
    expect(first_slot).to_have_attribute(
        "data-time",
        re.compile(r"\d{2}:\d{2}")
    )

def test_customer_can_create_booking(customer_page, base_url):
    customer_page.goto(f"{base_url}/booking")
    tomorrow = (
        date.today() + timedelta(days=1)
    ).strftime("%Y-%m-%d")
    customer_page.locator("#date").fill(tomorrow)
    first_slot = customer_page.locator(".slot-btn").first
    expect(first_slot).to_be_visible(timeout=10000)
    first_slot.click()
    expect(
        customer_page.locator("#selected_time")
    ).not_to_have_value("")
    customer_page.locator("#note").fill(
        "Playwright E2E booking test"
    )
    with customer_page.expect_response(
        lambda response:
            "/appointments" in response.url
            and response.request.method == "POST"
    ) as response_info:
        customer_page.locator(
            "#btn-submit-booking"
        ).click()
    response = response_info.value
    assert response.status == 201
    body = response.json()
    assert body["message"] == "Đặt lịch hẹn thành công!"
    assert body["appointment"]["id"] is not None
    expect(
        customer_page.locator(".toast-success")
    ).to_contain_text(
        "Đặt lịch hẹn thành công",
        timeout=5000
    )
    expect(customer_page).to_have_url(
        f"{base_url}/",
        timeout=5000
    )

def test_customer_can_view_created_booking(customer_page, customer_booking, base_url):
    appointment_id = customer_booking["id"]

    booking_date = customer_booking["date"]

    customer_page.goto(
        f"{base_url}/appointments/me?date={booking_date}"
    )

    row = find_row_across_pages(
        customer_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None, (
        f"Không tìm thấy appointment #{appointment_id}"
    )

    expect(row).to_be_visible()

    expect(row).to_contain_text(
        "E2E_AUTOMATION_BOOKING"
    )

    expect(row).to_contain_text(
        "Đã xác nhận"
    )

def test_customer_can_edit_booking(customer_page, customer_booking, base_url):
    appointment_id = customer_booking["id"]

    booking_date = customer_booking["date"]

    customer_page.goto(
        f"{base_url}/appointments/me?date={booking_date}"
    )

    row = find_row_across_pages(
        customer_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None, (
        f"Không tìm thấy appointment #{appointment_id}"
    )

    expect(row).to_be_visible()

    # Mở modal edit
    row.locator(".btn-edit-trigger").click()

    modal = customer_page.locator(
        "#editAppointmentModal"
    )

    expect(modal).to_be_visible()

    # Đảm bảo modal đang edit đúng appointment
    expect(
        customer_page.locator("#edit_appt_id")
    ).to_have_value(str(appointment_id))

    # Sửa note
    customer_page.locator("#edit_note").fill(
        "E2E_BOOKING_UPDATED"
    )

    with customer_page.expect_response(
            lambda response:
            f"/appointments/{appointment_id}" in response.url
            and response.request.method == "PUT"
    ) as response_info:
        customer_page.locator(
            "#btnSubmitEdit"
        ).click()

    response = response_info.value

    assert response.status == 200

    body = response.json()

    assert body["message"] == "Cập nhật lịch hẹn thành công!"
    assert body["appointment"]["id"] == appointment_id
    assert body["appointment"]["note"] == "E2E_BOOKING_UPDATED"

    # Trang reload sau update
    customer_page.wait_for_load_state("load")

    # Sau reload có thể lại quay về page 1,
    # nên phải tìm lại qua pagination
    row = find_row_across_pages(
        customer_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None, (
        f"Không tìm thấy appointment #{appointment_id} sau khi update"
    )

    expect(row).to_contain_text(
        "E2E_BOOKING_UPDATED"
    )

def test_customer_can_cancel_booking(customer_page, customer_booking, base_url):
    appointment_id = customer_booking["id"]
    booking_date = customer_booking["date"]

    customer_page.goto(
        f"{base_url}/appointments/me?date={booking_date}"
    )

    row = find_row_across_pages(
        customer_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None, (
        f"Không tìm thấy appointment #{appointment_id} "
        f"trong các trang phân trang"
    )

    expect(row).to_be_visible()

    row.locator(".btn-action-cancel").click()

    expect(
        customer_page.locator("#custom-confirm-modal")
    ).to_be_visible()

    with customer_page.expect_response(
            lambda response:
            f"/appointments/{appointment_id}/cancel" in response.url
            and response.request.method == "PATCH"
    ) as response_info:
        customer_page.locator(
            "#btn-ok-confirm"
        ).click()

    response = response_info.value

    assert response.status == 200

    body = response.json()

    assert body["appointment_id"] == appointment_id
    assert body["status"] == "CANCELLED"


def test_customer_cannot_cancel_booking_within_2_hours(
    customer_page,
    customer_booking_within_2_hours,
    base_url
):
    appointment_id = customer_booking_within_2_hours["id"]

    customer_page.goto(
        f"{base_url}/appointments/me"
    )

    row = find_row_across_pages(
        customer_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None

    # Với rule hiện tại, UI phải khóa thao tác
    expect(row).to_contain_text("Đã khóa")

    expect(
        row.locator(".btn-action-cancel")
    ).to_have_count(0)

    expect(
        row.locator(".btn-edit-trigger")
    ).to_have_count(0)

def test_customer_cannot_bypass_ui_and_cancel_within_2_hours(
    customer_page,
    customer_booking_within_2_hours,
    base_url
):
    appointment_id = customer_booking_within_2_hours["id"]

    customer_page.goto(f"{base_url}/appointments/me")

    csrf_token = customer_page.locator(
        'meta[name="csrf-token"]'
    ).get_attribute("content")

    response = customer_page.request.patch(
        f"{base_url}/appointments/{appointment_id}/cancel",
        headers={
            "X-CSRFToken": csrf_token
        }
    )

    assert response.status == 400

    body = response.json()

    assert "tối thiểu 2 giờ" in body["error"]



# customer1 không sửa được lịch customer2
def test_customer_cannot_edit_other_customer_booking(
    customer_page,
    customer2_booking,
    base_url
):
    appointment_id = customer2_booking["id"]

    customer_page.goto(
        f"{base_url}/appointments/me"
    )

    csrf_token = customer_page.locator(
        'meta[name="csrf-token"]'
    ).get_attribute("content")

    response = customer_page.request.put(
        f"{base_url}/appointments/{appointment_id}",
        headers={
            "X-CSRFToken": csrf_token
        },
        data={
            "note": "HACKED BY CUSTOMER1"
        }
    )

    assert response.status == 403

    body = response.json()

    assert "không có quyền sửa" in body["error"]

# customer1 không hủy được lịch customer2
def test_customer_cannot_cancel_other_customer_booking(
    customer_page,
    customer2_booking,
    base_url
):
    appointment_id = customer2_booking["id"]

    customer_page.goto(
        f"{base_url}/appointments/me"
    )

    csrf_token = customer_page.locator(
        'meta[name="csrf-token"]'
    ).get_attribute("content")

    response = customer_page.request.patch(
        f"{base_url}/appointments/{appointment_id}/cancel",
        headers={
            "X-CSRFToken": csrf_token
        }
    )

    assert response.status == 403

    body = response.json()

    assert "không có quyền hủy" in body["error"]

# Không được đặt lịch quá 30 ngày
from datetime import date, timedelta

from playwright.sync_api import expect


def test_booking_date_cannot_exceed_30_days(
    customer_page,
    base_url
):
    customer_page.goto(f"{base_url}/booking")

    date_input = customer_page.locator("#date")

    today = date.today()

    expected_min = today.strftime("%Y-%m-%d")

    expected_max = (
        today + timedelta(days=30)
    ).strftime("%Y-%m-%d")

    # UI phải giới hạn đúng khoảng ngày
    expect(date_input).to_have_attribute(
        "min",
        expected_min
    )

    expect(date_input).to_have_attribute(
        "max",
        expected_max
    )

    # Thử gán ngày +31 để kiểm tra browser validation
    invalid_date = (
        today + timedelta(days=31)
    ).strftime("%Y-%m-%d")

    date_input.fill(invalid_date)

    is_range_overflow = date_input.evaluate(
        "el => el.validity.rangeOverflow"
    )

    assert is_range_overflow is True

# Không được đặt trùng khung giờ
def test_customer_cannot_select_already_booked_time_slot(
    customer_page,
    customer_booking,
    base_url
):
    booking_date = customer_booking["date"]
    booking_time = customer_booking["time"]
    service_id = customer_booking["service_id"]
    staff_id = customer_booking["staff_id"]

    customer_page.goto(f"{base_url}/booking")

    # Chọn đúng dịch vụ đã dùng ở booking trước
    customer_page.locator(
        f'.service-select-card[data-id="{service_id}"]'
    ).click()

    # Chọn đúng stylist đã được gán ở booking trước
    customer_page.locator("#staff_id").select_option(
        str(staff_id)
    )

    # Chọn đúng ngày đã có lịch
    with customer_page.expect_response(
        lambda response:
            "/appointments/available-slots" in response.url
            and booking_date in response.url
    ):
        customer_page.locator("#date").fill(
            booking_date
        )

    # Giờ đã được đặt trước đó không được xuất hiện nữa
    occupied_slot = customer_page.locator(
        f'.slot-btn[data-time="{booking_time}"]'
    )

    expect(occupied_slot).to_have_count(0)

# UI không cho chọn ngày quá khứ
def test_booking_date_cannot_be_in_the_past(
    customer_page,
    base_url
):
    customer_page.goto(f"{base_url}/booking")

    date_input = customer_page.locator("#date")

    yesterday = (
        date.today() - timedelta(days=1)
    ).strftime("%Y-%m-%d")

    date_input.fill(yesterday)

    is_range_underflow = date_input.evaluate(
        "el => el.validity.rangeUnderflow"
    )

    assert is_range_underflow is True

    # Đồng thời kiểm tra min vẫn là hôm nay
    expect(date_input).to_have_attribute(
        "min",
        date.today().strftime("%Y-%m-%d")
    )

# Slot đã được đặt không còn xuất hiện trên giao diện
def test_booked_time_slot_is_not_available_again(
    customer_page,
    customer_booking,
    base_url
):
    booking_date = customer_booking["date"]
    booking_time = customer_booking["time"]
    service_id = customer_booking["service_id"]
    staff_id = customer_booking["staff_id"]

    # Fixture đã tạo appointment trước đó.
    # Bây giờ customer quay lại Booking.
    customer_page.goto(f"{base_url}/booking")

    # Chọn đúng dịch vụ của appointment đã tồn tại
    service_card = customer_page.locator(
        f'.service-select-card[data-id="{service_id}"]'
    )

    service_card.click()

    # Chọn đúng stylist đã được gán
    customer_page.locator("#staff_id").select_option(
        str(staff_id)
    )

    # Khi đổi ngày, UI sẽ gọi available-slots
    with customer_page.expect_response(
        lambda response:
            "/appointments/available-slots" in response.url
            and booking_date in response.url
    ):
        customer_page.locator("#date").fill(
            booking_date
        )

    # Slot đã được booking trước đó
    # không được render lại trên UI
    booked_slot = customer_page.locator(
        f'.slot-btn[data-time="{booking_time}"]'
    )

    expect(booked_slot).to_have_count(0)


# customer không thể đặt 2 lịch hẹn cùng giờ cùng ngày dù khác stylist
def test_customer_cannot_book_same_time_with_different_staff(
    customer_page,
    staff1_booking,
    base_url
):
    booking_date = staff1_booking["date"]
    booking_time = staff1_booking["time"]
    service_id = staff1_booking["service_id"]

    # Appointment đầu tiên đã tồn tại:
    # customer1 + staff1 + booking_date + booking_time

    customer_page.goto(f"{base_url}/booking")

    # 1. Chọn đúng dịch vụ của appointment đầu tiên
    customer_page.locator(
        f'.service-select-card[data-id="{service_id}"]'
    ).click()

    # 2. Chọn STAFF2 thay vì STAFF1
    customer_page.locator("#staff_id").select_option(
        label="Lê Văn Tuấn"
    )

    # 3. Chọn cùng ngày
    with customer_page.expect_response(
        lambda response:
            "/appointments/available-slots" in response.url
            and booking_date in response.url
    ):
        customer_page.locator("#date").fill(
            booking_date
        )

    # 4. Staff2 đang rảnh nên cùng giờ đó
    # vẫn phải xuất hiện trên giao diện
    same_time_slot = customer_page.locator(
        f'.slot-btn[data-time="{booking_time}"]'
    )

    expect(
        same_time_slot
    ).to_be_visible(timeout=10000)

    # 5. Customer chọn đúng giờ đang bị trùng với lịch Staff1
    same_time_slot.click()

    expect(
        customer_page.locator("#selected_time")
    ).to_have_value(booking_time)

    customer_page.locator("#note").fill(
        "E2E_OVERLAP_DIFFERENT_STAFF"
    )

    # 6. Submit hoàn toàn qua UI
    with customer_page.expect_response(
        lambda response:
            response.url.endswith("/appointments")
            and response.request.method == "POST"
    ) as response_info:

        customer_page.locator(
            "#btn-submit-booking"
        ).click()

    response = response_info.value

    # 7. Backend phải từ chối
    assert response.status == 400

    body = response.json()

    assert "trùng khung giờ" in body["error"]

    # 8. Người dùng phải nhìn thấy lỗi ngay trên UI
    error_toast = customer_page.locator(
        ".toast-error"
    )

    expect(error_toast).to_be_visible(timeout=5000)

    expect(error_toast).to_contain_text(
        "trùng khung giờ"
    )

    # 9. Vì thất bại nên vẫn ở trang Booking,
    # không được redirect về trang chủ
    expect(customer_page).to_have_url(
        f"{base_url}/booking"
    )