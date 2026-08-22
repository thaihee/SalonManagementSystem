from playwright.sync_api import expect


def test_admin_fixture(admin_page, base_url):
    expect(admin_page).to_have_url(
        f"{base_url}/admin"
    )


def test_staff_fixture(staff_page, base_url):
    expect(staff_page).to_have_url(
        f"{base_url}/staff/appointments"
    )


def test_receptionist_fixture(receptionist_page, base_url):
    expect(receptionist_page).to_have_url(
        f"{base_url}/reception/appointments"
    )


def test_customer_fixture(customer_page, base_url):
    expect(customer_page).to_have_url(
        f"{base_url}/"
    )