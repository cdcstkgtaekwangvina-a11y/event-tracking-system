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

document.addEventListener('alpine:init', () => {
    Alpine.data('employeeDeleteModal', () => ({
        isOpen: false,
        mode: 'single',
        employeeId: null,
        employeeIds: [],
        employeeName: '',
        loading: false,
        init() {
            window.employeeDeleteModal = this;
        },
        open(options = {}) {
            this.mode = options.mode || (options.ids ? 'bulk' : 'single');
            if (this.mode === 'bulk') {
                this.employeeIds = options.ids || [];
            } else {
                this.employeeId = options.id;
                this.employeeName = options.name || 'nhân viên này';
            }
            this.isOpen = true;
        },
        close() {
            this.isOpen = false;
        },
        async confirm() {
            if (this.loading) return;
            if (this.mode === 'single' && !this.employeeId) return;
            if (this.mode === 'bulk' && (!this.employeeIds || this.employeeIds.length === 0)) return;

            this.loading = true;
            try {
                let res;
                if (this.mode === 'bulk') {
                    res = await window.fetchHelper.delete('employees/bulk', { ids: this.employeeIds });
                } else {
                    res = await window.fetchHelper.delete('employees/' + this.employeeId);
                }
                if (res.status_code === 200) {
                    window.notify?.toast?.success?.('Thành công', res.message || 'Xoá nhân viên thành công');
                    this.close();
                    window.dispatchEvent(new CustomEvent('emp-deleted', { detail: { mode: this.mode, ids: this.employeeIds } }));
                    const tableUrl = new URL(window.EMP_URLS.employeesTable, window.location.origin);
                    const curParams = new URLSearchParams(window.location.search);
                    ['page','limit','search','sort_field','is_desc'].forEach(k => {
                        if (curParams.has(k)) tableUrl.searchParams.set(k, curParams.get(k));
                    });
                    htmx.ajax('GET', tableUrl.toString(), {
                        target: '#emp-table-container',
                        swap: 'innerHTML'
                    });
                } else {
                    window.notify?.toast?.error?.('Lỗi', res.message || 'Xoá thất bại');
                }
            } catch(e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi xảy ra khi xoá');
            } finally {
                this.loading = false;
            }
        }
    }));

    Alpine.data('employeeFormModal', () => ({
        isOpen: false,
        mode: 'create',
        employee: null,
        loading: false,
        form: {
            id: '',
            name: '',
            email: '',
            position: '',
            gender: '',
            department: '',
            starting_date: ''
        },
        init() {
            window.employeeFormModal = this;
        },
        open(options = {}) {
            this.mode = options.mode || 'create';
            if (options.mode === 'edit' && options.employee) {
                this.employee = options.employee;
                this.form = {
                    id: '',
                    name: options.employee.name || '',
                    email: options.employee.email || '',
                    position: options.employee.position || '',
                    gender: options.employee.gender || '',
                    department: options.employee.department || '',
                    starting_date: options.employee.starting_date || ''
                };
            } else {
                this.employee = null;
                this.form = { id: '', name: '', email: '', position: '', gender: '', department: '', starting_date: '' };
            }
            this.isOpen = true;
            const el = document.getElementById('emp-form-modal-backdrop');
            if (el) {
                el.classList.remove('hidden');
                el.style.display = 'flex';
            }
        },
        close() {
            this.isOpen = false;
            const el = document.getElementById('emp-form-modal-backdrop');
            if (el) {
                el.style.display = 'none';
            }
        },
        async submit() {
            if (this.loading) return;
            if (!this.form.name?.trim()) {
                window.notify?.toast?.error?.('Lỗi', 'Tên nhân viên không được để trống');
                return;
            }
            this.loading = true;
            try {
                const payload = { ...this.form };
                if (this.mode === 'create' && payload.id) {
                    payload.id = parseInt(payload.id, 10);
                    if (isNaN(payload.id) || payload.id <= 0) {
                        window.notify?.toast?.error?.('Lỗi', 'Mã nhân viên phải là số dương');
                        this.loading = false;
                        return;
                    }
                } else {
                    delete payload.id;
                }
                const endpoint = this.mode === 'edit' ? ('employees/' + this.employee.id) : 'employees';
                const method = this.mode === 'edit' ? 'put' : 'post';
                const res = await window.fetchHelper[method](endpoint, payload);
                if (res.status_code === 200 || res.status_code === 201) {
                    window.notify?.toast?.success?.('Thành công', res.message || (this.mode === 'edit' ? 'Cập nhật thành công' : 'Thêm nhân viên thành công'));
                    this.close();
                    const tableUrl = new URL(window.EMP_URLS.employeesTable, window.location.origin);
                    const curParams = new URLSearchParams(window.location.search);
                    ['page','limit','search','sort_field','is_desc'].forEach(k => {
                        if (curParams.has(k)) tableUrl.searchParams.set(k, curParams.get(k));
                    });
                    if (this.mode === 'create') tableUrl.searchParams.set('page', '1');
                    htmx.ajax('GET', tableUrl.toString(), {
                        target: '#emp-table-container',
                        swap: 'innerHTML'
                    });
                } else {
                    window.notify?.toast?.error?.('Lỗi', res.message || 'Có lỗi xảy ra');
                }
            } catch(e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi xảy ra khi lưu dữ liệu');
            } finally {
                this.loading = false;
            }
        }
    }));

    /* ===== Employee Import Modal ===== */
    Alpine.data('employeeImportModal', () => ({
        isOpen: false,
        step: 'url',
        fileUrl: '',
        headerRow: 1,
        rowCount: 20,
        previewData: null,
        columnMap: {},
        fileValidation: {
            url: '',
            status: 'idle',
            type: '',
            message: ''
        },
        requiredFields: ['id', 'name', 'email', 'position', 'department', 'gender', 'starting_date'],
        fieldLabels: {
            id: 'Mã số (ID) *',
            name: 'Họ và tên *',
            email: 'Email',
            position: 'Chức vụ',
            department: 'Phòng ban',
            gender: 'Giới tính',
            starting_date: 'Ngày bắt đầu'
        },
        loading: false,
        init() {
            window.employeeImportModal = this;
            window.addEventListener('emp-media-picked', (e) => {
                this.fileUrl = e.detail.url;
                this.$nextTick(() => {
                    this.onFileUrlChanged();
                });
            });
        },
        open() {
            this.step = 'url';
            this.fileUrl = '';
            this.headerRow = 1;
            this.rowCount = 20;
            this.previewData = null;
            this.columnMap = {};
            this.resetFileValidation();
            this.isOpen = true;
        },
        close() {
            this.isOpen = false;
        },
        resetFileValidation() {
            this.fileValidation = {
                url: '',
                status: 'idle',
                type: '',
                message: ''
            };
        },
        onFileUrlChanged() {
            this.previewData = null;
            this.columnMap = {};
            const value = String(this.fileUrl || '').trim();
            if (!value) {
                this.resetFileValidation();
                return;
            }
            this.validateFileUrl(value, { silent: true });
        },
        async previewFile() {
            if (!this.fileUrl.trim()) {
                window.notify?.toast?.error?.('Lỗi', 'Vui lòng nhập hoặc chọn URL file');
                return;
            }
            const currentUrl = String(this.fileUrl || '').trim();
            const canContinue = (
                this.fileValidation.url === currentUrl &&
                ['valid', 'unknown'].includes(this.fileValidation.status)
            ) || await this.validateFileUrl(currentUrl);
            if (!canContinue) return;
            this.loading = true;
            try {
                const res = await window.fetchHelper.post('employees/read-import-file', {
                    url: this.fileUrl,
                    header_row: this.headerRow,
                    row_count: this.rowCount
                });
                if (res.status_code === 200) {
                    this.previewData = res.data;
                    this.columnMap = {};

                    /* Auto-map headers nếu khớp từ khóa thông dụng */
                    const headers = res.data?.headers || [];
                    const keywordsMap = {
                        id: ['mã số', 'ma so', 'mã nhân viên', 'ma nhan vien', 'mã nv', 'ma nv', 'id', 'code', 'emp_id', 'employee_id'],
                        name: ['họ và tên', 'ho va ten', 'họ tên', 'ho ten', 'tên', 'name', 'full name'],
                        email: ['email', 'thu dien tu', 'thư điện tử'],
                        position: ['chức vụ', 'chuc vu', 'position', 'vị trí', 'vi tri'],
                        department: ['phòng ban', 'phong ban', 'khoa', 'bộ phận', 'bo phan', 'department'],
                        gender: ['giới tính', 'gioi tinh', 'giưới tính', 'giuoi tinh', 'gender', 'sex', 'nam/nữ', 'nam/nu', 'nam nu', 'phái', 'phai', 'gt', 'male', 'female'],
                        starting_date: ['ngày bắt đầu', 'ngay bat dau', 'ngày vào công ty', 'ngay vao cong ty', 'starting_date', 'start_date']
                    };

                    headers.forEach(h => {
                        const normalized = String(h).trim().toLowerCase();
                        for (const [field, keywords] of Object.entries(keywordsMap)) {
                            if (!this.columnMap[field] && keywords.some(k => normalized.includes(k))) {
                                this.columnMap[field] = h;
                            }
                        }
                    });

                    this.step = 'map';
                } else {
                    window.notify?.toast?.error?.('Lỗi', res.message || 'Không thể đọc file');
                }
            } catch (e) {
                window.notify?.toast?.error?.('Lỗi', 'Lỗi kết nối');
            } finally {
                this.loading = false;
            }
        },
        async validateFileUrl(url, options = {}) {
            const value = String(url || '').trim();
            if (!value) return false;

            this.fileValidation = {
                url: value,
                status: 'checking',
                type: '',
                message: ''
            };

            try {
                const fileUrl = new URL(value, window.location.origin);
                fileUrl.searchParams.set('_ts', Date.now().toString());

                if (typeof window.fetchHelper?.rawGet !== 'function') {
                    throw new Error('fetchHelper.rawGet chưa sẵn sàng');
                }

                const res = await window.fetchHelper.rawGet(fileUrl.toString(), {}, {
                    requireAuth: false,
                    headers: {},
                    fetchOptions: { cache: 'reload' }
                });

                if (this.fileValidation.url !== value) {
                    return false;
                }

                if (!res || !res.ok) {
                    throw new Error('Không tải được file');
                }

                const fileBuffer = await res.arrayBuffer();
                const bytes = new Uint8Array(fileBuffer);
                const contentType = (res.headers.get('content-type') || '').toLowerCase();
                const cleanUrl = value.split('?')[0].toLowerCase();
                const head = bytes.slice(0, 8);
                const isExcel = (
                    (head[0] === 0x50 && head[1] === 0x4b && head[2] === 0x03 && head[3] === 0x04) ||
                    (head[0] === 0xd0 && head[1] === 0xcf && head[2] === 0x11 && head[3] === 0xe0 && head[4] === 0xa1 && head[5] === 0xb1 && head[6] === 0x1a && head[7] === 0xe1) ||
                    cleanUrl.endsWith('.xlsx') ||
                    cleanUrl.endsWith('.xls') ||
                    contentType.includes('spreadsheetml') ||
                    contentType.includes('ms-excel')
                );
                const isJson = (
                    cleanUrl.endsWith('.json') ||
                    contentType.includes('application/json') ||
                    (() => {
                        const text = new TextDecoder('utf-8').decode(bytes.slice(0, 128)).trim();
                        return text.startsWith('{') || text.startsWith('[');
                    })()
                );
                const isCsv = (
                    cleanUrl.endsWith('.csv') ||
                    contentType.includes('text/csv') ||
                    contentType.includes('application/csv') ||
                    contentType.includes('text/plain')
                );

                const detectedType = isExcel ? 'excel' : (isJson ? 'json' : (isCsv ? 'csv' : ''));
                if (detectedType) {
                    this.fileValidation = {
                        url: value,
                        status: 'valid',
                        type: detectedType,
                        message: ''
                    };
                    return true;
                }

                this.fileValidation = {
                    url: value,
                    status: 'invalid',
                    type: '',
                    message: 'Link file không đúng định dạng hỗ trợ'
                };
                if (!options.silent) {
                    window.notify?.toast?.error?.('Lỗi', 'Link file không đúng định dạng hỗ trợ');
                }
                return false;
            } catch (e) {
                this.fileValidation = {
                    url: value,
                    status: 'unknown',
                    type: '',
                    message: 'Trình duyệt chưa đọc được file, hệ thống sẽ kiểm tra khi xem trước'
                };
                return true;
            }

            return false;
        },
        async importData() {
            if (!this.columnMap.id || !this.columnMap.name) {
                window.notify?.toast?.error?.('Lỗi', 'Vui lòng map đầy đủ cột Mã số (ID) và Họ và tên');
                return;
            }

            /* Đảo ngược columnMap: { dbField: excelHeader } -> { excelHeader: dbField } */
            const formattedColumnMap = {};
            for (const [dbField, excelHeader] of Object.entries(this.columnMap)) {
                if (excelHeader && String(excelHeader).trim()) {
                    formattedColumnMap[excelHeader] = dbField;
                }
            }

            this.loading = true;
            try {
                const res = await window.fetchHelper.post('employees/import', {
                    file_url: this.fileUrl,
                    header_row: this.headerRow,
                    column_map: formattedColumnMap
                });
                if (res.status_code === 200) {
                    window.notify?.toast?.success?.('Thành công', res.message || 'Import thành công, đang xử lý...');
                    this.close();
                    setTimeout(() => {
                        const tableUrl = new URL(window.EMP_URLS.employeesTable, window.location.origin);
                        const curParams = new URLSearchParams(window.location.search);
                        ['page', 'limit', 'search', 'sort_field', 'is_desc'].forEach(k => {
                            if (curParams.has(k)) tableUrl.searchParams.set(k, curParams.get(k));
                        });
                        htmx.ajax('GET', tableUrl.toString(), { target: '#emp-table-container', swap: 'innerHTML' });
                    }, 2000);
                } else {
                    window.notify?.toast?.error?.('Lỗi', res.message || 'Import thất bại');
                }
            } catch (e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi xảy ra khi import');
            } finally {
                this.loading = false;
            }
        }
    }));

    /* ===== Employee Import Media Picker ===== */
    Alpine.data('empImportMediaPicker', () => ({
        open: false,
        loading: false,
        uploading: false,
        folderId: '',
        folderStack: [],
        search: '',

        /*
         * BẮT BUỘC có viewMode + mediaPicker đủ cấu trúc
         * để items_grid.j2 (load qua fetch) resolve Alpine scope đúng
         */
        viewMode: 'grid',
        mediaPicker: {
            selected: null,
            loading: false,
            uploading: false,
            folderId: '',
            folderStack: [],
            search: '',
            open: false,
            filterValue: 'all',
            filterOpen: false,
            sortValue: 'updated_at',
            sortOpen: false,
            sortDir: 'desc',
        },

        allowedExts: ['xlsx', 'xls', 'csv', 'json'],

        isAllowedExt(ext) {
            if (!ext) return false;
            return this.allowedExts.includes(ext.toLowerCase().replace(/^\./, ''));
        },

        getExtFromNameOrUrl(name = '', url = '') {
            const source = String(name || '').includes('.')
                ? String(name || '')
                : String(url || '').split('?')[0];
            return source.includes('.') ? source.split('.').pop().toLowerCase() : '';
        },

        init() {
            window.empImportMediaPicker = this;
        },

        openPicker() {
            this.folderId = '';
            this.folderStack = [];
            this.search = '';
            this.mediaPicker.selected = null;
            this.mediaPicker.folderId = '';
            this.mediaPicker.folderStack = [];
            this.mediaPicker.search = '';
            this.open = true;
            this.loadItems('');
        },

        closePicker() {
            this.open = false;
        },

        goRoot() {
            this.folderStack = [];
            this.mediaPicker.folderStack = [];
            this.loadItems('');
        },

        goBack() {
            const prev = this.folderStack.pop();
            this.mediaPicker.folderStack = [...this.folderStack];
            this.loadItems(prev || '');
        },

        async loadItems(folderId = '', pushHistory = false) {
            const container = document.getElementById('emp-import-media-items');
            if (!container) return;

            if (pushHistory && this.folderId) {
                this.folderStack.push(this.folderId);
                this.mediaPicker.folderStack = [...this.folderStack];
            }

            this.loading = true;
            this.mediaPicker.loading = true;
            this.folderId = folderId || '';
            this.mediaPicker.folderId = this.folderId;
            this.mediaPicker.selected = null;

            const params = new URLSearchParams();
            params.set('picker', 'true');
            params.set('limit', '60');
            if (this.folderId) params.set('folder_id', this.folderId);
            if (this.search) params.set('search', this.search);

            const url = window.EMP_URLS.mediaManager + '/items/html?' + params.toString();
            container.innerHTML = '<div class="media-loading"><div class="spinner-sm"></div><span>Đang tải...</span></div>';

            try {
                const res = await fetch(url, { credentials: 'same-origin' });
                const html = await res.text();
                container.innerHTML = html;

                /*
                 * Dùng $nextTick để đợi Alpine init xong các node mới
                 * rồi mới gắn click handler JS
                 */
                this.$nextTick(() => {
                    container.querySelectorAll('.media-row, .media-grid-card').forEach(el => {
                        el.style.cursor = 'pointer';
                        el.addEventListener('click', () => this.handleItemClick(el));
                        el.addEventListener('dblclick', () => {
                            this.handleItemClick(el);
                            this.confirmSelect();
                        });
                    });
                    this.syncClasses();
                });
            } catch (e) {
                container.innerHTML = '<p style="padding:24px;text-align:center;color:var(--text-secondary)">Không thể tải danh sách file.</p>';
            } finally {
                this.loading = false;
                this.mediaPicker.loading = false;
            }
        },

        handleItemClick(el) {
            const kind = el.dataset.mediaKind || el.dataset.type || 'file';
            const id = el.dataset.id;

            if (kind === 'folder') {
                this.loadItems(id, true);
                return;
            }

            const name = el.dataset.mediaName || '';
            const url = el.dataset.mediaUrl || '';
            const ext = this.getExtFromNameOrUrl(name, url);

            /* Gán vào mediaPicker.selected để Alpine `:class` trong items_grid reactive */
            this.mediaPicker.selected = {
                id: parseInt(id, 10),
                name,
                url,
                kind,
                ext,
                sizeLabel: this.formatBytes(el.dataset.mediaSize),
            };
            this.syncClasses();
        },

        syncClasses() {
            const container = document.getElementById('emp-import-media-items');
            if (!container) return;
            const selId = this.mediaPicker.selected?.id;
            container.querySelectorAll('.media-row, .media-grid-card').forEach(el => {
                el.classList.toggle('selected', !!selId && parseInt(el.dataset.id, 10) === selId);
            });
        },

        confirmSelect() {
            const sel = this.mediaPicker.selected;
            if (!sel || sel.kind === 'folder' || !sel.url) return;
            if (!this.isAllowedExt(sel.ext)) {
                window.notify?.toast?.error?.('Lỗi', 'Chỉ cho phép file .xlsx, .xls, .csv, .json');
                return;
            }
            this.closePicker();
            window.notify?.toast?.success?.('Thành công', 'Đã chọn: ' + sel.name);
            window.dispatchEvent(new CustomEvent('emp-media-picked', { detail: { url: sel.url, name: sel.name } }));
        },

        formatBytes(bytes) {
            const n = parseInt(bytes, 10);
            if (!n || n <= 0) return '—';
            if (n < 1024) return n + ' B';
            if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
            return (n / 1048576).toFixed(1) + ' MB';
        },

        async onFileSelected(event) {
            const file = event.target?.files?.[0];
            if (!file) return;
            const ext = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : '';
            if (!this.isAllowedExt(ext)) {
                window.notify?.toast?.error?.('Lỗi', 'Chỉ cho phép tải lên file .xlsx, .xls, .csv, .json');
                event.target.value = '';
                return;
            }
            await this.uploadFile(file);
            event.target.value = '';
        },

        async uploadFile(file) {
            if (!file || this.uploading) return;
            this.uploading = true;
            this.mediaPicker.uploading = true;
            const loadingId = window.notify?.toast?.loading?.('Đang xử lý', 'Đang tải file lên...');
            try {
                const formData = new FormData();
                formData.append('name', file.name);
                formData.append('is_folder', 'false');
                formData.append('file', file);
                if (this.folderId) formData.append('folder_id', this.folderId);
                const res = await window.fetchHelper.post('media', formData);
                if (loadingId) window.notify?.toast?.dismiss?.(loadingId);
                if (res?.status_code === 201) {
                    window.notify?.toast?.success?.('Thành công', 'Đã tải file lên');
                    await this.loadItems(this.folderId);
                } else {
                    window.notify?.toast?.error?.('Lỗi', res?.message || 'Tải file thất bại');
                }
            } catch (e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi khi tải file lên');
            } finally {
                this.uploading = false;
                this.mediaPicker.uploading = false;
            }
        }
    }));
});
