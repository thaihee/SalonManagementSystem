from playwright.sync_api import expect

from test.e2e.utils.pagination import find_row_across_pages


def test_staff_can_open_appointments_page(
    staff_page,
    base_url
):
    staff_page.goto(
        f"{base_url}/staff/appointments"
    )

    expect(
        staff_page.get_by_role(
            "heading",
            name="Lịch Hẹn Được Giao"
        )
    ).to_be_visible()

    expect(
        staff_page.locator("#staff_customer_search")
    ).to_be_visible()

    expect(
        staff_page.locator("#date_filter")
    ).to_be_visible()

    expect(
        staff_page.locator("#appointments-tbody")
    ).to_be_visible()

def test_staff_can_see_assigned_booking(
    staff_page,
    staff1_booking,
    base_url
):
    appointment_id = staff1_booking["id"]
    booking_date = staff1_booking["date"]

    # Quan trọng: route Staff mặc định lọc theo ngày,
    # nên truyền đúng ngày fixture vừa tạo.
    staff_page.goto(
        f"{base_url}/staff/appointments"
        f"?date={booking_date}"
    )

    row = find_row_across_pages(
        staff_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is not None, (
        f"Staff1 không nhìn thấy appointment "
        f"#{appointment_id} được giao"
    )

    expect(row).to_be_visible()

    expect(row).to_contain_text(
        "Phạm Thị Lan"
    )

    expect(row).to_contain_text(
        "Đã xác nhận"
    )

    expect(row).to_contain_text(
        "E2E_STAFF_ASSIGNED_BOOKING"
    )

    expect(
        row.get_by_role(
            "link",
            name="Tạo hóa đơn"
        )
    ).to_be_visible()

def test_staff_cannot_see_other_staff_booking(
    staff2_page,
    staff1_booking,
    base_url
):
    appointment_id = staff1_booking["id"]
    booking_date = staff1_booking["date"]

    staff2_page.goto(
        f"{base_url}/staff/appointments?date={booking_date}"
    )

    # Duyệt toàn bộ pagination để chắc chắn appointment
    # không xuất hiện ở bất kỳ page nào
    row = find_row_across_pages(
        staff2_page,
        f"#row-appt-{appointment_id}"
    )

    assert row is None, (
        f"Staff2 lại nhìn thấy appointment #{appointment_id} "
        f"được giao cho Staff1"
    )
