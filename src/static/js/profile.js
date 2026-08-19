/**
 * profile.js
 * Client-side logic for the user profile page (`/user/me`).
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('avatarLibraryPicker', () => ({
        isOpen: false,
        loading: false,
        saving: false,
        folderId: '',
        folderStack: [],
        selected: null,
        search: '',
        viewMode: 'grid',
        init() {
            window.avatarLibraryPicker = this;
        },
        async load(folderId = '', pushHistory = false) {
            const container = document.getElementById('avatar-picker-items');
            if (!container) return;
            if (pushHistory && this.folderId) this.folderStack.push(this.folderId);

            this.loading = true;
            this.folderId = folderId || '';
            this.selected = null;

            const params = new URLSearchParams();
            params.set('picker', 'true');
            params.set('type_filter', 'image');
            params.set('limit', '60');
            if (this.folderId) params.set('folder_id', this.folderId);
            if (this.search) params.set('search', this.search);

            const url = window.PROFILE_URLS.mediaManager + '/items/html?' + params.toString();
            container.innerHTML = '<div class="media-loading"><div class="spinner-sm"></div><span>Đang tải dữ liệu...</span></div>';
            try {
                await htmx.ajax('GET', url, { target: '#avatar-picker-items', swap: 'innerHTML' });
            } finally {
                this.loading = false;
                this.syncSelectionClasses();
            }
        },
        syncSelectionClasses() {
            const container = document.getElementById('avatar-picker-items');
            if (!container) return;
            const selectedId = this.selected?.id;
            container.querySelectorAll('.media-row, .media-grid-card').forEach((el) => {
                el.classList.toggle('selected', !!selectedId && parseInt(el.dataset.id) === selectedId);
            });
        },
        open() {
            window.activeMediaPicker = this;
            this.isOpen = true;
            this.folderId = '';
            this.folderStack = [];
            this.selected = null;
            this.search = '';
            this.load('');
        },
        close() {
            this.isOpen = false;
        },
        goRoot() {
            this.folderStack = [];
            this.load('');
        },
        goBack() {
            const previousFolderId = this.folderStack.pop();
            this.load(previousFolderId || '');
        },
        handleItemClick(event) {
            const itemEl = event.currentTarget.closest('.media-row, .media-grid-card');
            if (!itemEl) return;

            const kind = itemEl.dataset.mediaKind || itemEl.dataset.type || 'file';
            if (kind === 'folder') {
                this.load(itemEl.dataset.id, true);
                return;
            }

            this.selected = {
                id: parseInt(itemEl.dataset.id),
                name: itemEl.dataset.mediaName || '',
                url: itemEl.dataset.mediaUrl || '',
            };
            this.syncSelectionClasses();
        },
        async confirm() {
            if (!this.selected || this.saving) return;
            this.saving = true;
            try {
                const res = await window.fetchHelper.put('User/profile/avatar/media', { media_id: this.selected.id });
                if (res.status_code === 200) {
                    window.notify?.toast?.success?.('Thành công', res.message || 'Cập nhật ảnh đại diện thành công');
                    window.dispatchEvent(new CustomEvent('avatar-media-selected', {
                        detail: { url: res.data.file_url || res.data.avatar_url }
                    }));
                    this.close();
                } else {
                    window.notify?.toast?.error?.('Lỗi', res.message || 'Cập nhật ảnh đại diện thất bại');
                }
            } catch (e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi xảy ra khi chọn ảnh');
            } finally {
                this.saving = false;
            }
        },
    }));

    Alpine.data('profilePage', (initial) => ({
        role: initial.role,
        isSuperAdmin: initial.is_super_admin,
        avatarUrl: initial.avatar_url,
        savingProfile: false,
        changingPassword: false,
        form: {
            name: initial.name,
            username: initial.username,
            email: initial.email,
        },
        passwordForm: {
            current_password: '',
            new_password: '',
            confirm_new_password: '',
        },
        extractErrorMessage(res, fallback) {
            if (Array.isArray(res)) {
                return res.map(e => e.msg || e.message).filter(Boolean).join('; ') || fallback;
            }
            return res?.message || fallback;
        },
        roleLabel(role) {
            const labels = { 'SUPPER_ADMIN': 'Super Admin', 'ADMIN': 'Admin', 'COMMON': 'Nhân viên' };
            return labels[role] || role || '—';
        },
        async saveProfile() {
            if (this.savingProfile) return;
            if (!this.form.name?.trim() || !this.form.username?.trim()) {
                window.notify?.toast?.error?.('Lỗi', 'Họ tên và tên đăng nhập không được để trống');
                return;
            }
            this.savingProfile = true;
            try {
                const payload = { name: this.form.name, username: this.form.username };
                if (this.isSuperAdmin) payload.email = this.form.email;
                const res = await window.fetchHelper.put('User/profile', payload);
                if (res.status_code === 200) {
                    window.notify?.toast?.success?.('Thành công', res.message || 'Cập nhật thông tin thành công');
                } else {
                    window.notify?.toast?.error?.('Lỗi', this.extractErrorMessage(res, 'Cập nhật thông tin thất bại'));
                }
            } catch (e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi xảy ra khi lưu thông tin');
            } finally {
                this.savingProfile = false;
            }
        },
        async changePassword() {
            if (this.changingPassword) return;
            const { current_password, new_password, confirm_new_password } = this.passwordForm;
            if (!current_password || !new_password || !confirm_new_password) {
                window.notify?.toast?.error?.('Lỗi', 'Vui lòng nhập đầy đủ thông tin mật khẩu');
                return;
            }
            if (new_password !== confirm_new_password) {
                window.notify?.toast?.error?.('Lỗi', 'Xác nhận mật khẩu mới không khớp');
                return;
            }
            this.changingPassword = true;
            try {
                const res = await window.fetchHelper.put('User/profile/password', this.passwordForm);
                if (res.status_code === 200) {
                    window.notify?.toast?.success?.('Thành công', 'Đổi mật khẩu thành công, vui lòng đăng nhập lại');
                    setTimeout(() => { window.location.href = '/auth/login'; }, 1500);
                } else {
                    window.notify?.toast?.error?.('Lỗi', this.extractErrorMessage(res, 'Đổi mật khẩu thất bại'));
                }
            } catch (e) {
                window.notify?.toast?.error?.('Lỗi', 'Có lỗi xảy ra khi đổi mật khẩu');
            } finally {
                this.changingPassword = false;
            }
        },
    }));
});
