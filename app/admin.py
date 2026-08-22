from datetime import date, datetime
import math
from io import StringIO, BytesIO

from flask import request, jsonify, render_template, Response, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

from app import app, dao
from app.decorators import role_required
from app.models import UserRole, InvoiceStatus
from app.exceptions import ValidationError, DuplicateError, NotFoundError


# =========================================================================
# 0. TRANG QUẢN TRỊ ADMIN (DASHBOARD TỔNG QUAN)
# =========================================================================
@app.route('/admin', methods=['GET'])
@role_required(UserRole.ADMIN)
def admin_dashboard_view():
    kw = request.args.get('kw', '').strip()
    date_str = request.args.get('date', None)  # Đọc tham số ngày
    status_str = request.args.get('status', 'ALL')
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)

    # Nếu người dùng truyền date rỗng (bấm Clear) -> selected_date = None
    selected_date = None
    if date_str and date_str.strip():
        try:
            selected_date = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        except ValueError:
            selected_date = None
            date_str = ''

    # Thống kê Doanh thu (nếu không chọn ngày thì lấy hôm nay)
    kpi_date = selected_date or date.today()
    today_invoices, _ = dao.get_invoices(
        status='PAID',
        from_date=datetime.combine(kpi_date, datetime.min.time()),
        to_date=datetime.combine(kpi_date, datetime.max.time()),
        page=None
    )
    today_revenue = sum(inv.total_amount for inv in today_invoices)

    # Lấy danh sách lịch hẹn (Nếu selected_date=None -> lấy TOÀN BỘ)
    all_appointments = dao.get_appointments(date=selected_date, page=None)

    # Lọc theo Trạng thái
    if status_str != 'ALL':
        appointments = [a for a in all_appointments if a.status.name == status_str]
    else:
        appointments = all_appointments

    # Lọc theo Từ khóa
    if kw:
        kw_lower = kw.lower()
        appointments = [
            a for a in appointments
            if (a.customer and kw_lower in a.customer.full_name.lower()) or
               (a.customer and kw_lower in a.customer.phone) or
               (a.service and kw_lower in a.service.service_name.lower()) or
               (a.staff and kw_lower in a.staff.full_name.lower())
        ]

    # Phân trang
    total_items = len(appointments)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size
    appointments_paged = appointments[start:end]

    low_stock_products = dao.check_low_stock_products()
    pending_drafts, _ = dao.get_invoices(status='DRAFT', page=None)

    return render_template(
        'admin/admin_dashboard.html',
        today_revenue=today_revenue,
        today_appointments=appointments_paged,
        total_appointments_count=total_items,
        all_appointments=all_appointments,
        low_stock_products=low_stock_products,
        pending_drafts=pending_drafts,
        selected_date=date_str if date_str is not None else date.today().strftime('%Y-%m-%d'),
        selected_status=status_str,
        kw=kw,
        page=page,
        total_pages=total_pages
    ), 200


# =========================Nghiệp vụ 2: CRUD Dịch vụ (Quản lý)==========================

@app.route('/admin/services', methods=['GET'])
@role_required(UserRole.ADMIN)
def list_services():
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)  # Mặc định 10 mục / trang

    # Lấy danh sách dịch vụ có phân trang
    services, total_items = dao.get_services_paged(page=page, page_size=page_size)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    all_products = dao.get_all_products()

    return render_template(
        'admin/admin_services.html',
        services=services,
        products=all_products,
        page=page,
        total_pages=total_pages
    ), 200


@app.route('/admin/services', methods=['POST'])
@role_required(UserRole.ADMIN)
def create_service():
    data = request.form
    try:
        s = dao.add_service(
            name=data.get('service_name'),
            price=data.get('price'),
            duration=data.get('duration_minutes'),
            description=data.get('description'),
            avatar=data.get('avatar')  # Đọc trường avatar từ Form
        )
        return jsonify(success=True, id=s.id), 201
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi thêm dịch vụ!"), 500


@app.route('/admin/services/<int:service_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_service_route(service_id):
    data = request.get_json(silent=True) or {}

    name = data.get('service_name')
    price = data.get('price')
    duration = data.get('duration_minutes')
    description = data.get('description')
    avatar = data.get('avatar')

    try:
        dao.update_service(
            service_id=service_id,
            name=name,
            price=price,
            duration=duration,
            description=description,
            avatar=avatar
        )
        return jsonify(success=True, message="Cập nhật thành công!"), 200

    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception("LỖI UPDATE SERVICE: %s", ex)
        return jsonify(success=False, error=f"Lỗi Server: {str(ex)}"), 500


@app.route('/admin/services/<int:service_id>', methods=['DELETE'])
@role_required(UserRole.ADMIN)
def delete_service_route(service_id):
    try:
        dao.delete_service(service_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi xóa dịch vụ!"), 500


# =========================Nghiệp vụ 3b: Nhập / Xuất kho (Quản lý)==========================

@app.route('/admin/products/<int:product_id>/import', methods=['POST'])
@role_required(UserRole.ADMIN)
def import_stock_route(product_id):
    data = request.form
    try:
        p = dao.import_stock(product_id, data.get('quantity'))
        return jsonify(success=True, product_id=p.id, stock_quantity=p.stock_quantity), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi nhập kho!"), 500


@app.route('/admin/products/<int:product_id>/export', methods=['POST'])
@role_required(UserRole.ADMIN)
def export_stock_route(product_id):
    data = request.form
    try:
        p = dao.export_stock(product_id, data.get('quantity'))
        return jsonify(success=True, product_id=p.id, stock_quantity=p.stock_quantity), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi xuất kho!"), 500


# =========================Nghiệp vụ 3c: Cảnh báo tồn kho thấp==========================

@app.route('/admin/products/low-stock', methods=['GET'])
@role_required(UserRole.ADMIN)
def low_stock_products_route():
    products = dao.check_low_stock_products()
    return jsonify([{
        "id": p.id,
        "product_name": p.product_name,
        "stock_quantity": p.stock_quantity,
        "min_stock_level": p.min_stock_level
    } for p in products]), 200


# =========================Nghiệp vụ 1b: Admin quản lý User/Nhân viên==========================

def _serialize_user(u):
    return {
        "id": u.id,
        "full_name": u.full_name,
        "username": u.username,
        "phone": u.phone,
        "email": u.email,
        "role": u.role.name,
        "active": u.active
    }

@app.route('/admin/users', methods=['GET'])
@role_required(UserRole.ADMIN)
def list_users_route():
    role_filter = request.args.get('role')
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)  # 10 tài khoản / trang

    # Lấy danh sách người dùng theo vai trò
    all_users = dao.get_users(role=role_filter) if role_filter else dao.get_users()

    # Tính toán phân trang
    total_items = len(all_users) if all_users else 0
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size
    users_paged = all_users[start:end] if all_users else []

    return render_template(
        'admin/admin_staff.html',  # hoặc tên file template quản lý nhân sự của bạn
        users=users_paged,
        total_items=total_items,
        selected_role=role_filter,
        page=page,
        total_pages=total_pages
    ), 200


@app.route('/users/<int:user_id>', methods=['GET'])
@role_required(UserRole.ADMIN)
def get_user_detail_route(user_id):
    u = dao.get_user_by_id(user_id)
    if not u:
        return jsonify(success=False, error="Không tìm thấy người dùng!"), 404
    return jsonify(_serialize_user(u)), 200


@app.route('/users', methods=['POST'])
@role_required(UserRole.ADMIN)
def create_staff_route():
    data = request.form

    role_param = data.get('role', 'STAFF').upper()
    if role_param not in ('STAFF', 'RECEPTIONIST'):
        return jsonify(success=False, error="Chỉ được tạo tài khoản với role STAFF hoặc RECEPTIONIST!"), 400

    try:
        u = dao.add_user(
            full_name=data.get('full_name'),
            username=data.get('username'),
            password=data.get('password'),
            phone=data.get('phone'),
            email=data.get('email'),
            role=UserRole[role_param]
        )
        return jsonify(success=True, user=_serialize_user(u)), 201
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi tạo tài khoản nhân viên!"), 500


@app.route('/users/<int:user_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_staff_route(user_id):
    data = request.form
    try:
        u = dao.update_user_profile(
            user_id=user_id,
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        return jsonify(success=True, user=_serialize_user(u)), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi cập nhật nhân viên!"), 500


@app.route('/users/<int:user_id>', methods=['DELETE'])
@role_required(UserRole.ADMIN)
def deactivate_user_route(user_id):
    try:
        dao.delete_user_soft(user_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi vô hiệu hóa tài khoản!"), 500


# =========================Nghiệp vụ 4: Báo cáo Doanh thu (Quản lý)==========================

@app.route('/admin/reports/revenue', methods=['GET'])
@role_required(UserRole.ADMIN)
def revenue_report_route():
    period_type = request.args.get('period_type', 'day').lower()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10) # 10 dòng / trang

    try:
        from_date_str = from_date if from_date else None
        to_date_str = to_date if to_date else None

        report_data = dao.get_revenue_report(
            period_type=period_type,
            from_date_str=from_date_str,
            to_date_str=to_date_str
        )

        grand_total_revenue = sum(item.get("total_revenue", 0) for item in report_data) if report_data else 0
        grand_total_invoices = sum(item.get("total_invoices", 0) for item in report_data) if report_data else 0

        # PHÂN TRANG BẢNG BÁO CÁO
        total_items = len(report_data) if report_data else 0
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

        start = (page - 1) * page_size
        end = start + page_size
        report_data_paged = report_data[start:end] if report_data else []

        return render_template(
            'admin/admin_reports.html',
            report_data=report_data_paged, # Truyền danh sách đã cắt theo trang
            full_report_data=report_data,  # Dùng cho Biểu đồ Chart.js (vẽ đầy đủ)
            period_type=period_type,
            from_date=from_date,
            to_date=to_date,
            grand_total_revenue=grand_total_revenue,
            grand_total_invoices=grand_total_invoices,
            page=page,
            total_pages=total_pages
        ), 200

    except Exception as ex:
        app.logger.exception(ex)
        return render_template('admin/admin_reports.html', err_msg=str(ex)), 500


@app.route('/admin/reports/revenue/export', methods=['GET'])
@role_required(UserRole.ADMIN)
def export_revenue_report_route():
    from_date = request.args.get('from_date', '').strip() or None
    to_date = request.args.get('to_date', '').strip() or None

    # Lấy danh sách hóa đơn PAID trong khoảng thời gian chọn
    from_dt = datetime.strptime(from_date, '%Y-%m-%d') if from_date else None
    to_dt = datetime.strptime(to_date, '%Y-%m-%d') if to_date else None

    if to_dt:
        to_dt = datetime.combine(to_dt, datetime.max.time())

    invoices, _ = dao.get_invoices(
        status='PAID',
        from_date=from_dt,
        to_date=to_dt,
        page=None
    )

    # 1. Khởi tạo Workbook & Sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Báo Cáo Doanh Thu"

    # Định nghĩa Màu sắc & Font chữ mẫu Luxury
    font_title = Font(name="Arial", size=14, bold=True, color="000000")
    font_header = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    font_body = Font(name="Arial", size=10)
    font_total = Font(name="Arial", size=11, bold=True, color="000000")

    fill_title = PatternFill(start_color="F7D3D0", end_color="F7D3D0", fill_type="solid")  # Màu hồng nhạt
    fill_header = PatternFill(start_color="D6705B", end_color="D6705B", fill_type="solid")  # Màu cam gạch

    thin_border = Border(
        left=Side(style='thin', color='E0E0E0'),
        right=Side(style='thin', color='E0E0E0'),
        top=Side(style='thin', color='E0E0E0'),
        bottom=Side(style='thin', color='E0E0E0')
    )

    # 2. Tiêu đề Báo Báo
    date_title = f"BÁO CÁO DOANH THU NHÂN VIÊN"
    if from_date and to_date:
        date_title += f" TỪ {from_date} ĐẾN {to_date}"
    elif from_date:
        date_title += f" TỪ NGÀY {from_date}"

    ws.merge_cells('A1:G1')
    ws['A1'] = date_title
    ws['A1'].font = font_title
    ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
    ws['A1'].fill = fill_title
    ws.row_dimensions[1].height = 40

    # 3. Header Bảng
    headers = [
        "Mã Nhân Viên",
        "Họ Tên Nhân Viên",
        "Ngày Lập Hóa Đơn",
        "Số Hóa Đơn",
        "Tên Khách Hàng",
        "Dịch Vụ Đã Làm",
        "Tổng Tiền Hóa Đơn (VND)"
    ]
    ws.append(headers)
    ws.row_dimensions[2].height = 28

    for col_num, _ in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center" if col_num != 6 else "left", vertical="center")

    # 4. Ghi Dữ Liệu Chi Tiết Hóa Đơn
    total_sum = 0
    row_idx = 3

    for inv in invoices:
        staff_code = f"{inv.staff_id}" if inv.staff else "N/A"
        staff_name = inv.staff.full_name if inv.staff else "Chưa chỉ định"
        inv_date = inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else ""
        inv_code = f"{inv.id}"
        cust_name = inv.customer.full_name if inv.customer else "Khách vãng lai"

        # Gom danh sách các dịch vụ trong hóa đơn
        services_done = ", ".join([d.service.service_name for d in inv.details if d.service]) or "---"
        amount = inv.total_amount or 0
        total_sum += amount

        row_data = [staff_code, staff_name, inv_date, inv_code, cust_name, services_done, amount]
        ws.append(row_data)

        # Định dạng dòng
        ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=3).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=4).alignment = Alignment(horizontal="center")

        # Định dạng tiền tệ
        amount_cell = ws.cell(row=row_idx, column=7)
        amount_cell.number_format = '#,##0 "đ"'
        amount_cell.alignment = Alignment(horizontal="right")

        for col in range(1, 8):
            c = ws.cell(row=row_idx, column=col)
            c.font = font_body
            c.border = thin_border

        row_idx += 1

    # 5. Dòng Tổng Cộng
    ws.cell(row=row_idx, column=1, value="Tổng cộng").font = font_total
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)

    total_cell = ws.cell(row=row_idx, column=7, value=total_sum)
    total_cell.font = font_total
    total_cell.number_format = '#,##0 "đ"'
    total_cell.alignment = Alignment(horizontal="right")

    for col in range(1, 8):
        ws.cell(row=row_idx, column=col).border = thin_border

    # Tự động điều chỉnh độ rộng cột
    column_widths = {'A': 15, 'B': 22, 'C': 18, 'D': 15, 'E': 22, 'F': 32, 'G': 25}
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    # 6. Xuất ra Byte Stream
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Bao_Cao_Doanh_Thu_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )


# =========================Nghiệp vụ 3: CRUD Sản phẩm (Quản lý)==========================

@app.route('/admin/products', methods=['GET'])
@role_required(UserRole.ADMIN)
def list_products():
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)  # Mặc định 10 sản phẩm / trang

    # Lấy toàn bộ danh sách sản phẩm
    all_products = dao.get_all_products()
    total_items = len(all_products)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    # Cắt danh sách theo trang hiện tại
    start = (page - 1) * page_size
    end = start + page_size
    products_paged = all_products[start:end]

    low_stock_products = dao.check_low_stock_products()

    return render_template(
        'admin/admin_products.html',
        products=products_paged,  # Danh sách đã phân trang
        low_stock=low_stock_products,
        page=page,                # Trang hiện tại
        total_pages=total_pages   # Tổng số trang
    ), 200


@app.route('/admin/products', methods=['POST'])
@role_required(UserRole.ADMIN)
def create_product():
    data = request.form
    try:
        p = dao.add_product(
            name=data.get('product_name'),
            stock_quantity=data.get('stock_quantity'),
            min_stock_level=data.get('min_stock_level'),
            unit=data.get('unit')
        )
        return jsonify(success=True, id=p.id), 201
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi thêm sản phẩm!"), 500


@app.route('/admin/products/<int:product_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_product_route(product_id):
    data = request.form
    try:
        dao.update_product(
            product_id=product_id,
            name=data.get('product_name'),
            unit=data.get('unit'),
            min_stock_level=data.get('min_stock_level')
        )
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi cập nhật sản phẩm!"), 500


@app.route('/admin/products/<int:product_id>', methods=['DELETE'])
@role_required(UserRole.ADMIN)
def delete_product_route(product_id):
    try:
        dao.delete_product(product_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi xóa sản phẩm!"), 500


# =========================Nghiệp vụ: Định mức Sản phẩm theo Dịch vụ (Quản lý)==========================

@app.route('/admin/services/<int:service_id>/products', methods=['GET'])
@role_required(UserRole.ADMIN)
def list_service_products_route(service_id):
    items = dao.get_service_products(service_id)
    return jsonify([{
        "id": sp.id,
        "product_id": sp.product_id,
        "product_name": sp.product.product_name,
        "default_quantity": sp.default_quantity
    } for sp in items]), 200


@app.route('/admin/service-products', methods=['POST'])
@role_required(UserRole.ADMIN)
def create_service_product_route():
    data = request.form
    try:
        sp = dao.add_service_product(
            service_id=data.get('service_id'),
            product_id=data.get('product_id'),
            default_quantity=data.get('default_quantity')
        )
        return jsonify(success=True, id=sp.id), 201
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi thêm định mức sản phẩm!"), 500


@app.route('/admin/service-products/<int:sp_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_service_product_route(sp_id):
    data = request.form
    try:
        dao.update_service_product(sp_id, default_quantity=data.get('default_quantity'))
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi cập nhật định mức!"), 500


@app.route('/admin/service-products/<int:sp_id>', methods=['DELETE'])
@role_required(UserRole.ADMIN)
def delete_service_product_route(sp_id):
    try:
        dao.delete_service_product(sp_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi xóa định mức!"), 500


# =========================Nghiệp vụ: Khuyến mãi (Quản lý)==========================

@app.route('/admin/promotions', methods=['GET'])
@role_required(UserRole.ADMIN)
def list_promotions_route():
    page = request.args.get('page', 1, type=int)
    page_size = app.config.get('PAGE_SIZE', 10)  # 10 khuyến mãi / trang

    # 1. Lấy toàn bộ mã khuyến mãi
    all_promos = dao.get_all_promotions() if hasattr(dao, 'get_all_promotions') else []

    # 2. Tính toán phân trang
    total_items = len(all_promos) if all_promos else 0
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size
    promos_paged = all_promos[start:end] if all_promos else []

    return render_template(
        'admin/admin_promotions.html',
        promotions=promos_paged,
        total_items=total_items,
        page=page,
        total_pages=total_pages
    ), 200


@app.route('/admin/promotions', methods=['POST'])
@role_required(UserRole.ADMIN)
def create_promotion_route():
    data = request.get_json(silent=True) or request.form
    try:
        pr = dao.add_promotion(
            promo_code=data.get('promo_code'),
            promo_type=data.get('promo_type'),
            value=data.get('value'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )
        return jsonify(success=True, id=pr.id), 201
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi thêm khuyến mãi!"), 500


@app.route('/admin/promotions/<int:promo_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_promotion_route(promo_id):
    data = request.get_json(silent=True) or request.form
    try:
        dao.update_promotion(
            promo_id,
            promo_code=data.get('promo_code'),
            promo_type=data.get('promo_type'),
            value=data.get('value'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except DuplicateError as ex:
        return jsonify(success=False, error=str(ex)), 409
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi cập nhật khuyến mãi!"), 500


@app.route('/admin/promotions/<int:promo_id>', methods=['DELETE'])
@role_required(UserRole.ADMIN)
def delete_promotion_route(promo_id):
    try:
        dao.delete_promotion(promo_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error=str(ex)), 500


@app.route('/users/<int:user_id>/toggle-active', methods=['PATCH'])
@role_required(UserRole.ADMIN)
def toggle_user_active_route(user_id):
    try:
        u = dao.toggle_user_active(user_id)
        return jsonify(success=True, active=u.active), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi thay đổi trạng thái tài khoản!"), 500


# =========================Nghiệp vụ: Xóa /Sửa đơn nháp (Quản lý)==========================

@app.route('/admin/invoices/<int:invoice_id>', methods=['PUT'])
@role_required(UserRole.ADMIN)
def update_invoice_draft_route(invoice_id):
    data = request.get_json(silent=True) or request.form
    details = data.get('details', [])

    if not details:
        return jsonify(success=False, error="Vui lòng cung cấp danh sách chi tiết (details)!"), 400

    try:
        invoice = dao.update_invoice_draft(invoice_id, details)
        return jsonify(success=True, invoice={
            "id": invoice.id,
            "status": invoice.status.name,
            "total_amount": invoice.total_amount
        }), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi sửa hóa đơn!"), 500


@app.route('/admin/invoices/<int:invoice_id>/cancel', methods=['PATCH'])
@role_required(UserRole.ADMIN)
def cancel_invoice_draft_route(invoice_id):
    try:
        dao.cancel_invoice_draft(invoice_id)
        return jsonify(success=True), 200
    except NotFoundError as ex:
        return jsonify(success=False, error=str(ex)), 404
    except ValidationError as ex:
        return jsonify(success=False, error=str(ex)), 400
    except Exception as ex:
        app.logger.exception(ex)
        return jsonify(success=False, error="Lỗi hệ thống khi hủy hóa đơn!"), 500



# API trả về danh sách chi tiết của Hóa đơn nháp để Admin sửa tại chỗ (Inline Edit)
@app.route('/admin/invoices/<int:invoice_id>/draft-detail', methods=['GET'])
@role_required(UserRole.ADMIN)
def get_invoice_draft_detail_route(invoice_id):
    invoice = dao.get_invoice_by_id(invoice_id)
    if not invoice:
        return jsonify(success=False, error="Không tìm thấy hóa đơn!"), 404

    if invoice.status != InvoiceStatus.DRAFT:
        return jsonify(success=False, error="Hóa đơn này không phải hóa đơn nháp!"), 400

    details_data = []
    for d in invoice.details:
        if d.service:
            item_name = d.service.service_name
            item_id = d.service_id
            item_type = "SERVICE"
        elif d.product:
            item_name = d.product.product_name
            item_id = d.product_id
            item_type = "PRODUCT_USED"
        else:
            continue

        details_data.append({
            "detail_id": d.id,
            "item_name": item_name,
            "item_id": item_id,
            "item_type": item_type,
            "quantity": d.quantity,
            "unit_price": d.unit_price,
            "subtotal": d.subtotal
        })

    return jsonify(success=True, invoice={
        "id": invoice.id,
        "details": details_data
    }), 200