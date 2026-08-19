/**
 * account.js
 * Client-side logic for the Account admin module.
 */

window.accountActions = {
    async toggleActive(id, isActive) {
        const actionLabel = isActive ? 'chặn' : 'bỏ chặn';
        const approved = await window.notify.modal.confirm(
            'Xác nhận',
            `Bạn có chắc muốn ${actionLabel} tài khoản này?`
        );
        if (!approved) return;

        const res = await window.fetchHelper.put('Account/' + id, { is_active: !isActive });
        if (res.status_code === 200) {
            window.notify?.toast?.success?.('Thành công', res.message || 'Cập nhật trạng thái thành công');
            const tableUrl = new URL(window.ACCOUNT_URLS.accountsTable, window.location.origin);
            const curParams = new URLSearchParams(window.location.search);
            ['page', 'limit', 'search', 'sort_field', 'is_desc'].forEach(k => {
                if (curParams.has(k)) tableUrl.searchParams.set(k, curParams.get(k));
            });
            htmx.ajax('GET', tableUrl.toString(), { target: '#acc-table-container', swap: 'innerHTML' });
        } else {
            window.notify?.toast?.error?.('Lỗi', res.message || 'Cập nhật trạng thái thất bại');
        }
    }
};

document.addEventListener('alpine:init', () => {
    Alpine.data('accountFormModal', (canEditEmail) => ({
        isOpen: false,
        mode: 'create',
        account: null,
        loading: false,
        canEditEmail: !!canEditEmail,
        form: {
            name: '',
            username: '',
            email: '',
            password: '',
        },
        init() {
            window.accountFormModal = this;
        },
        open(options = {}) {
            this.mode = options.mode || 'create';
            if (this.mode === 'edit' && options.account) {
                this.account = options.account;
                this.form = {
                    name: options.account.name || '',
                    username: options.account.username || '',
                    email: options.account.email || '',
                    password: '',
                };
            } else {
                this.account = null;
                this.form = { name: '', username: '', email: '', password: '' };
            }
            this.isOpen = true;
        },
        close() {
            this.isOpen = false;
        },
        extractErrorMessage(res, fallback) {
            if (Array.isArray(res)) {
                return res.map(e => e.msg || e.message).filter(Boolean).join('; ') || fallback;
            }
            return res?.message || fallback;
        },
        async submit() {
            if (this.loading) return;
            if (!this.form.name?.trim() || !this.form.username?.trim()) {
                window.notify?.toast?.error?.('Lỗi', 'Họ tên và tên đăng nhập không được để trống');
                return;
            }
            if (this.mode === 'create' && (!this.form.email?.trim() || !this.form.password)) {
                window.notify?.toast?.error?.('Lỗi', 'Email và mật khẩu không được để trống');
                return;
            }

            this.loading = true;
            try {
                let res;
                if (this.mode === 'edit') {
                    const payload = { name: this.form.name, username: this.form.username };
                    if (this.form.password) payload.password = this.form.password;
                    if (this.canEditEmail) payload.email = this.form.email;
                    res = await window.fetchHelper.put('Account/' + this.account.id, payload);
                } else {
                    res = await window.fetchHelper.post('Account', { ...this.form });
                }

                if (res.status_code === 200 || res.status_code === 201) {
                    window.notify?.toast?.success?.('Thành công', res.message || (this.mode === 'edit' ? 'Cập nhật thành công' : 'Tạo tài khoản thành công'));
                    this.close();
                    const tableUrl = new URL(window.ACCOUNT_URLS.accountsTable, window.location.origin);
                    const curParams = new URLSearchParams(window.location.search);
                    ['page', 'limit', 'search', 'sort_field', 'is_desc'].forEach(k => {
                        if (curParams.has(k)) tableUrl.searchParams.set(k, curParams.get(k));
                    });
                    if (this.mode === 'create') tableUrl.searchParams.set('page', '1');
                    htmx.ajax('GET', tableUrl.toString(), {
                        target: '#acc-table-container',
                        swap: 'innerHTML'
                    });
                } else {
                    window.notify?.toast?.error?.('Lỗi', this.extractErrorMessage(res, 'Có lỗi xảy ra'));
                }
            } catch (e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi xảy ra khi lưu dữ liệu');
            } finally {
                this.loading = false;
            }
        }
    }));
});
