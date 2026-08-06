/**
 * employees.js
 * Client-side logic for the Employees admin module.
 */

window.employeeActions = {
    /**
     * Export employees to CSV via the API.
     */
    exportEmployees() {
        window.notify?.info('Đang tải xuống danh sách nhân viên...');
        window.open('/api/employees/export', '_blank');
    },
};

/**
 * Bootstrap Alpine.js-based modal open helpers.
 * Use window-level CustomEvents so Alpine x-on listeners can catch them
 * regardless of initialization order.
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
window.employeeFormModal = {
    open(options) {
        window.dispatchEvent(new CustomEvent('emp-form-open', { detail: options || {} }));
        const el = document.getElementById('emp-form-modal-backdrop');
        if (el) {
            el.classList.remove('hidden');
            el.style.display = 'flex';
            if (window.Alpine && window.Alpine.$data) {
                try {
                    const data = window.Alpine.$data(el);
                    if (data && typeof data.open === 'function') data.open(options || {});
                } catch(e) {}
            }
        }
    }
};
window.employeeFormModal = {
    open(options) {
        window.dispatchEvent(new CustomEvent('emp-form-open', { detail: options || {} }));
        const el = document.getElementById('emp-form-modal-backdrop');
        if (el) {
            el.classList.remove('hidden');
            el.style.display = 'flex';
            if (window.Alpine && window.Alpine.$data) {
                try {
                    const data = window.Alpine.$data(el);
                    if (data && typeof data.open === 'function') data.open(options || {});
                } catch(e) {}
            }
        }
    }
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

window.employeeFormModal = {
    open(options) {
        window.dispatchEvent(new CustomEvent('emp-form-open', { detail: options || {} }));
        const el = document.getElementById('emp-form-modal-backdrop');
        if (el) {
            el.classList.remove('hidden');
            el.style.display = 'flex';
            if (window.Alpine && window.Alpine.$data) {
                try {
                    const data = window.Alpine.$data(el);
                    if (data && typeof data.open === 'function') data.open(options || {});
                } catch(e) {}
            }
        }
    }
};

window.employeeFormModal = {
    open(options) {
        window.dispatchEvent(new CustomEvent('emp-form-open', { detail: options || {} }));
        const el = document.getElementById('emp-form-modal-backdrop');
        if (el) {
            el.classList.remove('hidden');
            el.style.display = 'flex';
            if (window.Alpine && window.Alpine.$data) {
                try {
                    const data = window.Alpine.$data(el);
                    if (data && typeof data.open === 'function') data.open(options || {});
                } catch(e) {}
            }
        }
    }
};
