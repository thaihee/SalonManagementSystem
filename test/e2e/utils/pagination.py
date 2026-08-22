def find_row_across_pages(page, row_selector, max_pages=20):
    for page_number in range(1, max_pages + 1):

        row = page.locator(row_selector)

        if row.count() > 0:
            return row

        next_button = page.locator(".page-btn").filter(
            has_text="Sau"
        )

        if next_button.count() == 0:
            break

        if "disabled" in (next_button.get_attribute("class") or ""):
            break

        next_button.click()
        page.wait_for_load_state("load")

    return None


def find_product_row_across_pages(
    page,
    product_id,
    base_url,
    max_pages=20
):
    for page_number in range(1, max_pages + 1):

        page.goto(
            f"{base_url}/admin/products?page={page_number}"
        )

        row = page.locator(
            f"#row-product-{product_id}"
        )

        if row.count() > 0:
            return row

        next_link = page.get_by_role(
            "link",
            name="Sau"
        )

        if next_link.count() == 0:
            return None

        style = next_link.get_attribute("style") or ""

        if (
            "pointer-events: none" in style
            or "opacity: 0.5" in style
        ):
            return None

    return None



def find_service_row_across_pages(
    page,
    service_id,
    base_url,
    max_pages=20
):
    for page_number in range(1, max_pages + 1):

        page.goto(
            f"{base_url}/admin/services?page={page_number}"
        )

        row = page.locator(
            f"#row-service-{service_id}"
        )

        if row.count() > 0:
            return row

        next_link = page.get_by_role(
            "link",
            name="Sau"
        )

        if next_link.count() == 0:
            return None

        style = next_link.get_attribute("style") or ""

        # Page cuối: nút Sau bị disable bằng CSS
        if (
            "pointer-events: none" in style
            or "opacity: 0.5" in style
        ):
            return None

    return None


def find_promotion_row_across_pages(
    page,
    promotion_id,
    base_url,
    max_pages=20
):
    for page_number in range(1, max_pages + 1):

        page.goto(
            f"{base_url}/admin/promotions?page={page_number}"
        )

        row = page.locator(
            f"#row-promotion-{promotion_id}"
        )

        if row.count() > 0:
            return row

        next_link = page.get_by_role(
            "link",
            name="Sau"
        )

        if next_link.count() == 0:
            return None

        style = next_link.get_attribute("style") or ""

        if (
            "pointer-events: none" in style
            or "opacity: 0.5" in style
        ):
            return None

    return None


def find_user_row_across_pages(
    page,
    user_id,
    base_url,
    role=None,
    max_pages=20
):
    for page_number in range(
        1,
        max_pages + 1
    ):
        url = (
            f"{base_url}/admin/users"
            f"?page={page_number}"
        )

        if role:
            url += f"&role={role}"

        page.goto(url)

        row = page.locator(
            f"#row-user-{user_id}"
        )

        if row.count() > 0:
            return row

        next_link = page.get_by_role(
            "link",
            name="Sau"
        )

        if next_link.count() == 0:
            return None

        style = (
            next_link.get_attribute("style")
            or ""
        )

        if (
            "pointer-events: none" in style
            or "opacity: 0.5" in style
        ):
            return None

    return None


from playwright.sync_api import expect


def find_invoice_row_across_pages(
    page,
    invoice_id,
    base_url,
    max_pages=20
):
    for page_number in range(
        1,
        max_pages + 1
    ):
        page.goto(
            f"{base_url}/reception/invoices"
            f"?status=DRAFT&page={page_number}"
        )

        row = page.locator(
            ".inv-row",
            has_text=f"#{invoice_id}"
        )

        if row.count() > 0:
            return row.first

        next_link = page.get_by_role(
            "link",
            name="Sau",
            exact=False
        )

        if (
            next_link.count() == 0
            or "disabled"
            in (
                next_link.get_attribute("class")
                or ""
            )
        ):
            break

    return None


def find_invoice_row_by_status_across_pages(
    page,
    invoice_id,
    base_url,
    status,
    max_pages=20
):
    for page_number in range(
        1,
        max_pages + 1
    ):
        page.goto(
            f"{base_url}/reception/invoices"
            f"?status={status}"
            f"&page={page_number}"
        )

        row = page.locator(
            ".inv-row",
            has_text=f"#{invoice_id}"
        )

        if row.count() > 0:
            return row.first

        next_link = page.get_by_role(
            "link",
            name="Sau",
            exact=False
        )

        if next_link.count() == 0:
            break

        next_class = (
            next_link.get_attribute("class")
            or ""
        )

        if "disabled" in next_class:
            break

    return None