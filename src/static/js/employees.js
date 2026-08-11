/**
 * employees.js
 * Client-side logic for the Employees admin module.
 */

window.employeeActions = {
    /**
     * Export employees to Excel / CSV / JSON via POST API.
     */
    async exportEmployees(fileType = 'excel') {
        const loadingId = window.notify?.toast?.loading?.('Đang xuất file...', 'Vui lòng chờ');
        try {
            const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
            const response = await fetch('/api/employees/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ file_type: fileType })
            });

            if (loadingId) window.notify?.toast?.dismiss?.(loadingId);

            if (response.status === 204) {
                window.notify?.toast?.info?.('Thông báo', 'Không có dữ liệu nhân viên để xuất');
                return;
            }

            if (!response.ok) {
                window.notify?.toast?.error?.('Lỗi', 'Không thể xuất danh sách nhân viên');
                return;
            }

            const blob = await response.blob();
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `employees.${fileType === 'excel' ? 'xlsx' : fileType}`;
            if (contentDisposition && contentDisposition.includes('filename=')) {
                filename = contentDisposition.split('filename=')[1].replace(/["']/g, '');
            }

            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

            window.notify?.toast?.success?.('Thành công', `Đã xuất file ${filename} thành công`);
        } catch (e) {
            if (loadingId) window.notify?.toast?.dismiss?.(loadingId);
            window.notify?.toast?.error?.('Lỗi', 'Có lỗi khi kết nối máy chủ');
        }
    },
};

/**
 * Bootstrap Alpine.js-based modal open helpers.
 */
window.employeeFormModal = {
    open(options = {}) {
        window.dispatchEvent(new CustomEvent('emp-form-open', { detail: options }));
        const el = document.getElementById('emp-form-modal-backdrop');
        if (el) {
            el.classList.remove('hidden');
            el.style.display = 'flex';
            if (window.Alpine && window.Alpine.$data) {
                try {
                    const data = window.Alpine.$data(el);
                    if (data && typeof data.open === 'function') data.open(options);
                } catch(e) {}
            }
        }
    },
};

window.employeeDeleteModal = {
    open(options = {}) {
        window.dispatchEvent(new CustomEvent('emp-delete-open', { detail: options }));
        const el = document.getElementById('emp-delete-modal-backdrop');
        if (el) {
            el.classList.remove('hidden');
            el.style.display = 'flex';
            if (window.Alpine && window.Alpine.$data) {
                try {
                    const data = window.Alpine.$data(el);
                    if (data && typeof data.open === 'function') data.open(options);
                } catch(e) {}
            }
        }
    },
};

window.employeeImportModal = {
    open() {
        window.dispatchEvent(new CustomEvent('emp-import-open'));
        const el = document.getElementById('emp-import-modal-backdrop');
        if (el) {
            el.classList.remove('hidden');
            el.style.display = 'flex';
            if (window.Alpine && window.Alpine.$data) {
                try {
                    const data = window.Alpine.$data(el);
                    if (data && typeof data.open === 'function') data.open();
                } catch(e) {}
            }
        }
    },
};
