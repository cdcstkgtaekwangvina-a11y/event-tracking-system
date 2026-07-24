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
 * Alpine.js registers x-data on the DOM element.
 * We dispatch custom events that the x-data block listens to.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Employee Form Modal
    const formBackdrop = document.getElementById('emp-form-modal-backdrop');
    if (formBackdrop) {
        formBackdrop.addEventListener('emp-modal-open', function (e) {
            this._x_dataStack?.[0]?.open(e.detail);
        });
        window.employeeFormModal = {
            open(options = {}) {
                formBackdrop.dispatchEvent(
                    new CustomEvent('emp-modal-open', { detail: options })
                );
            },
        };
    }

    // Employee Delete Modal
    const deleteBackdrop = document.getElementById('emp-delete-modal-backdrop');
    if (deleteBackdrop) {
        deleteBackdrop.addEventListener('emp-delete-open', function (e) {
            this._x_dataStack?.[0]?.open(e.detail);
        });
        window.employeeDeleteModal = {
            open(options = {}) {
                deleteBackdrop.dispatchEvent(
                    new CustomEvent('emp-delete-open', { detail: options })
                );
            },
        };
    }

    // Employee Import Modal
    const importBackdrop = document.getElementById('emp-import-modal-backdrop');
    if (importBackdrop) {
        importBackdrop.addEventListener('emp-import-open', function () {
            this._x_dataStack?.[0]?.open();
        });
        window.employeeImportModal = {
            open() {
                importBackdrop.dispatchEvent(new CustomEvent('emp-import-open'));
            },
        };
    }
});
