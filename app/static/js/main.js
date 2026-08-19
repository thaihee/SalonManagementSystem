/* ========================================================
   UTILITIES JS - DÙNG CHUNG CHO TOÀN BỘ WEBSITE
   ======================================================== */

// 1. Lấy CSRF Token
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// 2. Hàm Fetch đính kèm CSRF Token tự động
async function csrfFetch(url, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
    };
    options.headers = { ...defaultHeaders, ...options.headers };
    return fetch(url, options);
}

// 3. Hàm hiển thị Toast Notification dùng chung
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;

    const iconClass = type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation';
    toast.innerHTML = `<i class="fa-solid ${iconClass} toast-icon"></i> <span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 4. Hàm đếm ký tự Textarea dùng chung
function updateCharCount(textarea, counterId = 'char_counter') {
    const counter = document.getElementById(counterId);
    if (counter) {
        const max = textarea.getAttribute('maxlength') || 255;
        counter.innerText = `${textarea.value.length}/${max}`;
    }
}

// 5. Hàm Confirm Modal đẹp mắt dùng chung
function showConfirm(message, onConfirm) {
    let modal = document.getElementById('custom-confirm-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'custom-confirm-modal';
        modal.className = 'modal-backdrop';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="modal-dialog-compact text-center" style="max-width: 360px; padding: 24px;">
                <div style="font-size: 2.2rem; color: #C87D75; margin-bottom: 10px;">
                    <i class="fa-solid fa-circle-question"></i>
                </div>
                <h5 style="margin-bottom: 8px; font-weight: 600; color: #2C2A29;">Xác nhận thao tác</h5>
                <p style="font-size: 0.9rem; color: #6c757d; margin-bottom: 20px;" id="confirm-modal-msg"></p>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button type="button" class="btn btn-sm btn-outline-secondary px-3" id="btn-cancel-confirm">Bỏ qua</button>
                    <button type="button" class="btn btn-sm btn-danger px-3" id="btn-ok-confirm">Xác nhận</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    document.getElementById('confirm-modal-msg').innerText = message;
    modal.style.display = 'flex';

    const btnOk = document.getElementById('btn-ok-confirm');
    const btnCancel = document.getElementById('btn-cancel-confirm');

    // Clone element để xóa sự kiện cũ
    const newOk = btnOk.cloneNode(true);
    const newCancel = btnCancel.cloneNode(true);
    btnOk.parentNode.replaceChild(newOk, btnOk);
    btnCancel.parentNode.replaceChild(newCancel, btnCancel);

    newCancel.addEventListener('click', () => { modal.style.display = 'none'; });
    newOk.addEventListener('click', () => {
        modal.style.display = 'none';
        if (onConfirm) onConfirm();
    });
}

// 6. Định dạng tiền tệ VND dùng chung
function formatCurrency(amount) {
    return new Intl.NumberFormat('vi-VN').format(amount || 0) + ' đ';
}


// 7. Bật/Tắt hiệu ứng loading cho nút bấm
function setButtonLoading(btn, isLoading, originalText = 'Lưu thay đổi') {
    if (!btn) return;
    btn.disabled = isLoading;
    if (isLoading) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý...';
    } else {
        btn.innerHTML = originalText;
    }
}


// 8. Hiển thị dòng thông báo rỗng cho Table
function renderEmptyRow(tableBodyId, colSpan, message = 'Chưa có dữ liệu') {
    const tbody = document.getElementById(tableBodyId);
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="${colSpan}" class="text-center py-4 text-muted">
                    <i class="fa-regular fa-folder-open d-block fs-3 mb-2"></i>
                    ${message}
                </td>
            </tr>
        `;
    }
}


//9. Trả về HTML Badge trạng thái Lịch hẹn
function getApptStatusBadge(status) {
    switch (status) {
        case "CONFIRMED":
            return `<span class="status-badge status-confirmed"><i class="fa-solid fa-calendar-check me-1"></i> Đã xác nhận</span>`;
        case "COMPLETED":
            return `<span class="status-badge status-completed"><i class="fa-solid fa-circle-check me-1"></i> Hoàn thành</span>`;
        case "CANCELLED":
            return `<span class="status-badge status-cancelled"><i class="fa-solid fa-ban me-1"></i> Đã hủy</span>`;
        default:
            return `<span class="status-badge">${status}</span>`;
    }
}

//10. Escape chuỗi tránh XSS
function escapeHtml(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}