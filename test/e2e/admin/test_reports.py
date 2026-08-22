import re

from playwright.sync_api import expect


def test_admin_can_open_revenue_report(
    admin_page,
    base_url
):
    # ==========================================
    # 1. Mở Revenue Report
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/reports/revenue"
    )

    # ==========================================
    # 2. URL đúng
    # ==========================================

    expect(admin_page).to_have_url(
        re.compile(
            r".*/admin/reports/revenue.*"
        )
    )

    # ==========================================
    # 3. Heading
    # ==========================================

    expect(
        admin_page.get_by_role(
            "heading",
            name="Báo Cáo Doanh Thu"
        )
    ).to_be_visible()

    # ==========================================
    # 4. Hai KPI chính
    # ==========================================

    expect(
        admin_page.get_by_text(
            "TỔNG DOANH THU TRONG KỲ",
            exact=True
        )
    ).to_be_visible()

    expect(
        admin_page.get_by_text(
            "TỔNG SỐ HÓA ĐƠN",
            exact=True
        )
    ).to_be_visible()

    # ==========================================
    # 5. Chart
    # ==========================================

    expect(
        admin_page.get_by_text(
            "Biểu Đồ Tăng Trưởng Doanh Thu",
            exact=False
        )
    ).to_be_visible()

    expect(
        admin_page.locator(
            "#revenueChart"
        )
    ).to_be_visible()

    # ==========================================
    # 6. Bảng số liệu
    # ==========================================

    expect(
        admin_page.get_by_text(
            "Bảng Số Liệu Chi Tiết",
            exact=False
        )
    ).to_be_visible()

    for column_name in [
        "Thời Gian",
        "Số Hóa Đơn",
        "Trung Bình / Đơn",
        "Tổng Doanh Thu",
    ]:
        expect(
            admin_page.get_by_role(
                "columnheader",
                name=column_name
            )
        ).to_be_visible()

    # ==========================================
    # 7. Bộ lọc
    # ==========================================

    filter_form = admin_page.locator(
        "#revenueFilterForm"
    )

    expect(filter_form).to_be_visible()

    period_select = filter_form.locator(
        '[name="period_type"]'
    )

    expect(period_select).to_be_visible()

    expect(
        period_select.locator(
            'option[value="day"]'
        )
    ).to_have_text(
        "Theo Ngày"
    )

    expect(
        period_select.locator(
            'option[value="month"]'
        )
    ).to_have_text(
        "Theo Tháng"
    )

    expect(
        period_select.locator(
            'option[value="year"]'
        )
    ).to_have_text(
        "Theo Năm"
    )

    expect(
        filter_form.locator(
            '[name="from_date"]'
        )
    ).to_be_visible()

    expect(
        filter_form.locator(
            '[name="to_date"]'
        )
    ).to_be_visible()

    expect(
        filter_form.get_by_role(
            "button",
            name="Lọc"
        )
    ).to_be_visible()

    # ==========================================
    # 8. Export Excel
    # ==========================================

    export_link = admin_page.get_by_role(
        "link",
        name="Xuất File Excel"
    )

    expect(export_link).to_be_visible()

    expect(export_link).to_have_attribute(
        "href",
        re.compile(
            r"/admin/reports/revenue/export"
        )
    )


from datetime import date, timedelta


def test_admin_can_filter_revenue_report(
    admin_page,
    base_url
):
    today = date.today()
    from_date = today - timedelta(days=30)
    to_date = today

    # ==========================================
    # 1. Mở Revenue Report
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/reports/revenue"
    )

    filter_form = admin_page.locator(
        "#revenueFilterForm"
    )

    expect(filter_form).to_be_visible()

    period_select = filter_form.locator(
        '[name="period_type"]'
    )

    from_input = filter_form.locator(
        '[name="from_date"]'
    )

    to_input = filter_form.locator(
        '[name="to_date"]'
    )

    # ==========================================
    # 2. Filter theo MONTH
    # ==========================================
    # select có onchange submit tự động

    period_select.select_option(
        "month"
    )

    admin_page.wait_for_load_state(
        "networkidle"
    )

    expect(admin_page).to_have_url(
        re.compile(
            r".*/admin/reports/revenue"
            r"\?.*period_type=month.*"
        )
    )

    # Sau reload lấy locator mới
    filter_form = admin_page.locator(
        "#revenueFilterForm"
    )

    period_select = filter_form.locator(
        '[name="period_type"]'
    )

    expect(period_select).to_have_value(
        "month"
    )

    # ==========================================
    # 3. Nhập khoảng ngày
    # ==========================================

    from_input = filter_form.locator(
        '[name="from_date"]'
    )

    to_input = filter_form.locator(
        '[name="to_date"]'
    )

    from_input.fill(
        from_date.isoformat()
    )

    to_input.fill(
        to_date.isoformat()
    )

    expect(from_input).to_have_value(
        from_date.isoformat()
    )

    expect(to_input).to_have_value(
        to_date.isoformat()
    )

    # ==========================================
    # 4. Click Lọc
    # ==========================================

    filter_form.get_by_role(
        "button",
        name="Lọc"
    ).click()

    admin_page.wait_for_load_state(
        "networkidle"
    )

    # ==========================================
    # 5. Query phải giữ đúng filter
    # ==========================================

    expect(admin_page).to_have_url(
        re.compile(
            rf".*period_type=month"
            rf".*from_date={from_date.isoformat()}"
            rf".*to_date={to_date.isoformat()}.*"
        )
    )

    # ==========================================
    # 6. Form sau reload phải giữ giá trị
    # ==========================================

    filter_form = admin_page.locator(
        "#revenueFilterForm"
    )

    expect(
        filter_form.locator(
            '[name="period_type"]'
        )
    ).to_have_value(
        "month"
    )

    expect(
        filter_form.locator(
            '[name="from_date"]'
        )
    ).to_have_value(
        from_date.isoformat()
    )

    expect(
        filter_form.locator(
            '[name="to_date"]'
        )
    ).to_have_value(
        to_date.isoformat()
    )

    # ==========================================
    # 7. Đổi sang YEAR
    # ==========================================

    filter_form.locator(
        '[name="period_type"]'
    ).select_option(
        "year"
    )

    admin_page.wait_for_load_state(
        "networkidle"
    )

    expect(admin_page).to_have_url(
        re.compile(
            r".*period_type=year.*"
        )
    )

    expect(
        admin_page.locator(
            '#revenueFilterForm '
            '[name="period_type"]'
        )
    ).to_have_value(
        "year"
    )


def test_revenue_report_shows_paid_invoice_correctly(
    admin_page,
    paid_invoice_for_report,
    base_url
):
    report_date = paid_invoice_for_report["date"]

    # ==========================================
    # 1. Lọc đúng ngày của invoice test
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/reports/revenue"
        f"?period_type=day"
        f"&from_date={report_date}"
        f"&to_date={report_date}"
    )

    # ==========================================
    # 2. Trang phải mở bình thường
    # ==========================================

    expect(
        admin_page.get_by_role(
            "heading",
            name="Báo Cáo Doanh Thu"
        )
    ).to_be_visible()

    # ==========================================
    # 3. KPI doanh thu
    # ==========================================

    revenue_kpi = admin_page.locator(
        ".report-kpi-value-green"
    )

    expect(revenue_kpi).to_have_text(
        "555,000 đ"
    )

    # ==========================================
    # 4. KPI số hóa đơn
    # ==========================================

    invoice_kpi = admin_page.locator(
        ".report-kpi-value-blue"
    )

    expect(invoice_kpi).to_have_text(
        "1 đơn"
    )

    # ==========================================
    # 5. Bảng phải có đúng dữ liệu ngày đó
    # ==========================================

    table = admin_page.locator(
        ".report-table"
    )

    expect(table).to_be_visible()

    # Tổng doanh thu của row
    expect(table).to_contain_text(
        "555,000 đ"
    )

    # Có đúng 1 invoice
    expect(table).to_contain_text(
        "1 đơn"
    )

    # Trung bình / đơn cũng = 555,000
    expect(table).to_contain_text(
        "555,000 đ"
    )


def test_admin_can_export_revenue_report_excel(
    admin_page,
    paid_invoice_for_report,
    base_url
):
    report_date = paid_invoice_for_report["date"]

    # ==========================================
    # 1. Mở report với filter cụ thể
    # ==========================================

    admin_page.goto(
        f"{base_url}/admin/reports/revenue"
        f"?period_type=day"
        f"&from_date={report_date}"
        f"&to_date={report_date}"
    )

    # ==========================================
    # 2. Nút Export phải tồn tại
    # ==========================================

    export_link = admin_page.get_by_role(
        "link",
        name="Xuất File Excel"
    )

    expect(export_link).to_be_visible()

    # Link export phải giữ filter hiện tại
    href = export_link.get_attribute("href")

    assert href is not None
    assert "/admin/reports/revenue/export" in href
    assert "period_type=day" in href
    assert f"from_date={report_date}" in href
    assert f"to_date={report_date}" in href

    # ==========================================
    # 3. Click và bắt download thật
    # ==========================================

    with admin_page.expect_download() as download_info:
        export_link.click()

    download = download_info.value

    # ==========================================
    # 4. Download không được lỗi
    # ==========================================

    failure = download.failure()

    assert failure is None, (
        f"Export Excel thất bại: {failure}"
    )

    # ==========================================
    # 5. Filename phải là file Excel
    # ==========================================

    filename = download.suggested_filename

    print(
        "\n[EXPORT REPORT] Filename:",
        filename
    )

    assert filename.lower().endswith(
        ".xlsx"
    )

    # ==========================================
    # 6. File thực sự phải tồn tại và có dữ liệu
    # ==========================================

    file_path = download.path()

    assert file_path is not None

    assert file_path.stat().st_size > 0

    print(
        "[EXPORT REPORT] Size:",
        file_path.stat().st_size,
        "bytes"
    )