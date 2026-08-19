/**
 * admin_events.js
 * Client-side Alpine component and helpers for Events Admin module.
 */

function adminEventsApp() {
    return {
        search: '',
        modalOpen: false,
        isEdit: false,
        isLoading: false,
        currentEventId: null,
        activeField: null,
        activeEditor: null,
        savedRange: null,
        imageFile: null,
        imagePreview: '',
        isDraggingImage: false,
        maxUploadSizeBytes: 50 * 1024 * 1024,
        uploadLimitLoaded: false,
        errors: {},
        form: {
            name: '',
            description: '',
            location: '',
            start_at: '',
            end_at: '',
            url_image: '',
            url_map: ''
        },

        resetForm() {
            if (this.imagePreview?.startsWith('blob:')) URL.revokeObjectURL(this.imagePreview);
            this.form = {
                name: '',
                description: '',
                location: '',
                start_at: '',
                end_at: '',
                url_image: '',
                url_map: ''
            };
            this.currentEventId = null;
            this.activeField = null;
            this.activeEditor = null;
            this.savedRange = null;
            this.imageFile = null;
            this.imagePreview = '';
            this.isDraggingImage = false;
            this.errors = {};
        },

        setEditorContent() {
            if (this.$refs.titleEditor) this.$refs.titleEditor.innerHTML = this.form.name || '';
            if (this.$refs.locationEditor) this.$refs.locationEditor.innerHTML = this.form.location || '';
            window.myEditor?.commands.setContent(this.form.description || '');
        },

        activateEditor(field, element) {
            this.activeField = field;
            this.activeEditor = element;
            this.captureSelection();
        },

        captureSelection() {
            const selection = window.getSelection();
            if (selection && selection.rangeCount && this.activeEditor?.contains(selection.anchorNode)) {
                this.savedRange = selection.getRangeAt(0).cloneRange();
            }
        },

        rememberSelection() {
            this.captureSelection();
        },

        restoreSelection() {
            if (!this.activeEditor) return false;
            this.activeEditor.focus();
            if (this.savedRange) {
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(this.savedRange);
            }
            return true;
        },

        syncActiveEditor() {
            if (!this.activeEditor || !this.activeField) return;
            const key = this.activeField === 'title' ? 'name' : this.activeField;
            this.form[key] = this.activeEditor.innerHTML;
            this.captureSelection();
        },

        formatText(command, value = null) {
            if (!this.activeField) return;
            const blockCommands = ['formatBlock', 'justifyLeft', 'justifyCenter', 'justifyRight', 'insertUnorderedList', 'insertOrderedList', 'insertImage'];
            if (this.activeField !== 'description' && blockCommands.includes(command)) return;
            if (!this.restoreSelection()) return;
            document.execCommand(command, false, value);
            this.syncActiveEditor();
        },

        routeToolbarClick(event) {
            if (this.activeField === 'description') return;

            const button = event.target.closest('button');
            const colorDropdown = event.target.closest('.color-dropdown');
            const colorTrigger = event.target.closest('.dropdown-wrapper')?.querySelector('.color-dropdown');
            const isInlineField = this.activeField === 'title' || this.activeField === 'location';

            if (!isInlineField) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }

            if (button?.title === 'In đậm' || button?.title === 'In nghiêng') {
                event.preventDefault();
                event.stopPropagation();
                this.formatText(button.title === 'In đậm' ? 'bold' : 'italic');
                return;
            }

            if (colorDropdown) {
                const grid = event.target.closest('.color-grid');
                const firstGrid = colorDropdown.querySelector('.color-grid');
                const swatch = event.target.closest('.color-swatch');
                event.preventDefault();
                event.stopPropagation();
                if (swatch && grid === firstGrid) {
                    const isDefault = swatch.classList.contains('outline-swatch');
                    this.formatText('foreColor', isDefault ? '#000000' : swatch.style.backgroundColor);
                }
                return;
            }

            if (colorTrigger) return;

            event.preventDefault();
            event.stopPropagation();
        },

        insertLink() {
            if (this.activeField !== 'description') return;
            const url = window.prompt('Nhập URL liên kết');
            if (url) this.formatText('createLink', url);
        },

        sanitizeInlineHtml(html) {
            const source = new DOMParser().parseFromString(html || '', 'text/html');
            const allowed = new Set(['B', 'STRONG', 'I', 'EM', 'SPAN', 'FONT']);
            const cleanNode = (node) => {
                if (node.nodeType === Node.TEXT_NODE) return node.cloneNode();
                if (node.nodeType !== Node.ELEMENT_NODE) return document.createTextNode('');
                const children = [...node.childNodes].map(cleanNode);
                if (!allowed.has(node.tagName)) {
                    const fragment = document.createDocumentFragment();
                    children.forEach(child => fragment.appendChild(child));
                    return fragment;
                }
                const tag = node.tagName === 'STRONG' ? 'b' : node.tagName === 'EM' ? 'i' : node.tagName === 'FONT' ? 'span' : node.tagName.toLowerCase();
                const element = document.createElement(tag);
                if (tag === 'span') {
                    const color = node.style.color || node.getAttribute('color');
                    if (color) element.style.color = color;
                }
                children.forEach(child => element.appendChild(child));
                return element;
            };
            const output = document.createElement('div');
            [...source.body.childNodes].forEach(node => output.appendChild(cleanNode(node)));
            return output.innerHTML.trim();
        },

        sanitizeInlineField(field, element) {
            const clean = this.sanitizeInlineHtml(element.innerHTML);
            element.innerHTML = clean;
            this.form[field] = clean;
            this.errors[field] = '';
        },

        plainText(html) {
            const element = document.createElement('div');
            element.innerHTML = html || '';
            return (element.textContent || '').trim();
        },

        formatBytes(bytes) {
            const size = Number(bytes);
            if (!Number.isFinite(size) || size <= 0) return '50MB';
            if (size >= 1024 * 1024 * 1024) return `${(size / (1024 * 1024 * 1024)).toFixed(1)}GB`;
            if (size >= 1024 * 1024) return `${Math.round(size / (1024 * 1024))}MB`;
            return `${Math.round(size / 1024)}KB`;
        },

        async loadUploadLimit() {
            if (this.uploadLimitLoaded) return;
            this.uploadLimitLoaded = true;
            try {
                const result = await window.fetchHelper.get('setting/max_file_sizes');
                const configured = result?.data?.value?.max_size_file;
                const raw = typeof configured === 'object' ? Object.values(configured)[0] : configured;
                const size = Number(raw);
                if (Number.isFinite(size) && size > 0) this.maxUploadSizeBytes = size;
            } catch (error) {
                console.warn('Không thể đọc giới hạn upload, sử dụng mặc định 50MB.', error);
            }
        },

        selectEventImage(file) {
            if (!file) return;
            if (!['image/jpeg', 'image/png'].includes(file.type)) {
                this.errors.image = 'Chỉ hỗ trợ ảnh JPG hoặc PNG.';
                return;
            }
            if (file.size > this.maxUploadSizeBytes) {
                this.errors.image = `Ảnh không được vượt quá ${this.formatBytes(this.maxUploadSizeBytes)}.`;
                return;
            }
            if (this.imagePreview?.startsWith('blob:')) URL.revokeObjectURL(this.imagePreview);
            this.imageFile = file;
            this.imagePreview = URL.createObjectURL(file);
            this.errors.image = '';
        },

        removeEventImage() {
            if (this.imagePreview?.startsWith('blob:')) URL.revokeObjectURL(this.imagePreview);
            this.imageFile = null;
            this.imagePreview = '';
            this.form.url_image = '';
        },

        openEventMediaPicker() {
            window.dispatchEvent(new CustomEvent('editor-open-media-picker', {
                detail: { purpose: 'event-image' }
            }));
        },

        useMediaImage(media) {
            if (!media?.url || media.type !== 'image') return;
            if (this.imagePreview?.startsWith('blob:')) URL.revokeObjectURL(this.imagePreview);
            this.imageFile = null;
            this.imagePreview = media.url;
            this.form.url_image = media.url;
            this.errors.image = '';
            notify.toast.success('Đã chọn ảnh', `Đang sử dụng ảnh "${media.name || 'từ Media'}"`);
        },

        async uploadImage(file) {
            const formData = new FormData();
            formData.append('name', file.name);
            formData.append('is_folder', 'false');
            formData.append('file', file);
            const response = await fetch('/api/media', { method: 'POST', body: formData });
            const result = await response.json();
            const apiResult = result?.detail && typeof result.detail === 'object'
                ? result.detail
                : result;
            const statusCode = Number(apiResult?.status_code || response.status);
            const message = apiResult?.message
                || (typeof result?.detail === 'string' ? result.detail : '')
                || 'Tải ảnh thất bại';
            const normalizedMessage = message.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

            if (!response.ok || apiResult?.success === false || statusCode >= 400) {
                const error = new Error(message);
                error.statusCode = statusCode;
                error.apiResult = apiResult;
                if (normalizedMessage.includes('anh da ton tai') || normalizedMessage.includes('ten da ton tai') || normalizedMessage.includes('file da ton tai')) {
                    error.code = 'MEDIA_DUPLICATE';
                }
                throw error;
            }
            const url = apiResult?.data?.url || apiResult?.url;
            if (!url) {
                const error = new Error(message || 'API media không trả về URL ảnh');
                if (normalizedMessage.includes('anh da ton tai') || normalizedMessage.includes('ten da ton tai') || normalizedMessage.includes('file da ton tai')) {
                    error.code = 'MEDIA_DUPLICATE';
                }
                throw error;
            }
            return url;
        },

        async insertDescriptionImage(event) {
            const file = event.target.files?.[0];
            event.target.value = '';
            if (!file) return;
            if (!['image/jpeg', 'image/png'].includes(file.type) || file.size > this.maxUploadSizeBytes) {
                this.errors.description = `Ảnh phải là JPG/PNG và không quá ${this.formatBytes(this.maxUploadSizeBytes)}.`;
                return;
            }
            try {
                const url = await this.uploadImage(file);
                this.formatText('insertImage', url);
            } catch (error) {
                this.errors.description = error.message;
            }
        },

        validateForm() {
            const errors = {};
            if (!this.plainText(this.form.name)) errors.name = 'Vui lòng nhập tên sự kiện.';
            if (this.form.start_at && this.form.end_at && new Date(this.form.start_at) >= new Date(this.form.end_at)) {
                errors.end_at = 'Thời gian kết thúc phải sau thời gian bắt đầu.';
            }
            this.errors = errors;
            return Object.keys(errors).length === 0;
        },

        formatDateTimeForInput(isoString) {
            if (!isoString) return '';
            const date = new Date(isoString);
            if (isNaN(date.getTime())) return '';
            const pad = (n) => n.toString().padStart(2, '0');
            return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
        },

        openCreateModal() {
            this.resetForm();
            this.loadUploadLimit();
            this.isEdit = false;
            this.modalOpen = true;
            this.$nextTick(() => this.setEditorContent());
        },

        async openEditModal(data) {
            this.resetForm();
            this.loadUploadLimit();
            this.isEdit = true;
            this.currentEventId = data.id;
            this.modalOpen = true;
            try {
                const response = await fetch('/api/events/' + data.id);
                const result = await response.json();
                const fullData = result?.data || result;
                if (response.ok && fullData) {
                    this.form = {
                        name: fullData.name || '',
                        description: fullData.description || '',
                        location: fullData.location || '',
                        start_at: this.formatDateTimeForInput(fullData.start_at),
                        end_at: this.formatDateTimeForInput(fullData.end_at),
                        url_image: fullData.url_image || '',
                        url_map: fullData.url_map || ''
                    };
                    this.imagePreview = this.form.url_image;
                    this.$nextTick(() => this.setEditorContent());
                }
            } catch (err) {
                console.error('Lỗi khi lấy chi tiết sự kiện cho chỉnh sửa nhanh:', err);
            }
        },

        closeModal() {
            if (this.isLoading) return;
            this.modalOpen = false;
            this.resetForm();
        },

        async saveEvent() {
            this.form.name = this.sanitizeInlineHtml(this.$refs.titleEditor?.innerHTML || this.form.name);
            this.form.location = this.sanitizeInlineHtml(this.$refs.locationEditor?.innerHTML || this.form.location);
            this.form.description = window.myEditor?.getHTML() || '';
            if (!this.validateForm()) return;
            this.isLoading = true;
            const url = this.isEdit ? `/api/events/${this.currentEventId}` : '/api/events/';
            const method = this.isEdit ? 'PUT' : 'POST';

            try {
                if (this.imageFile) this.form.url_image = await this.uploadImage(this.imageFile);
                const payload = {
                    ...this.form,
                    start_at: this.form.start_at ? new Date(this.form.start_at).toISOString() : null,
                    end_at: this.form.end_at ? new Date(this.form.end_at).toISOString() : null,
                    url_image: this.form.url_image || null,
                    url_map: this.form.url_map || null
                };
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
                });

                const resData = await response.json();

                if (response.ok) {
                    notify.toast.success(this.isEdit ? 'Cập nhật thành công' : 'Tạo sự kiện thành công');
                    this.modalOpen = false;
                    this.resetForm();
                    document.body.dispatchEvent(new CustomEvent('refresh-events', { bubbles: true }));
                } else {
                    notify.toast.error('Có lỗi xảy ra', resData.message || resData.detail || 'Vui lòng kiểm tra lại dữ liệu');
                }
            } catch (error) {
                console.error('Error saving event:', error);
                if (error.code === 'MEDIA_DUPLICATE') {
                    notify.toast.error('Ảnh đã tồn tại', 'File này đã có trong Media và không cần tải lên lại.');
                    const useMedia = await notify.modal.confirm(
                        'Ảnh đã có trong Media',
                        'Bạn có muốn mở Media để chọn ảnh đã tồn tại không?'
                    );
                    if (useMedia) this.openEventMediaPicker();
                } else {
                    notify.toast.error('Không thể lưu sự kiện', error.message || 'Vui lòng thử lại');
                }
            } finally {
                this.isLoading = false;
            }
        },

        async deleteEvent() {
            if (!this.currentEventId) return;

            const confirmed = await notify.modal.confirm(
                'Xóa sự kiện?',
                `Bạn có chắc chắn muốn xóa sự kiện "${this.form.name}" không? Hành động này không thể hoàn tác.`,
                { icon: 'warning', confirmText: 'Đồng ý', cancelText: 'Hủy' }
            );

            if (!confirmed) return;

            this.isLoading = true;
            try {
                const response = await fetch(`/api/events/${this.currentEventId}`, {
                    method: 'DELETE'
                });

                const resData = await response.json();

                if (response.ok) {
                    notify.toast.success('Xóa sự kiện thành công');
                    this.modalOpen = false;
                    this.resetForm();
                    document.body.dispatchEvent(new CustomEvent('refresh-events', { bubbles: true }));
                } else {
                    notify.toast.error('Xóa thất bại', resData.message || resData.detail || 'Không thể xóa sự kiện');
                }
            } catch (error) {
                console.error('Error deleting event:', error);
                notify.toast.error('Lỗi kết nối', 'Không thể kết nối đến máy chủ');
            } finally {
                this.isLoading = false;
            }
        },

        async deleteEventById(id, name) {
            if (!id) return;
            const confirmed = await notify.modal.confirm(
                'Xóa sự kiện?',
                `Bạn có chắc chắn muốn xóa sự kiện "${name || 'này'}" không? Hành động này không thể hoàn tác.`,
                { icon: 'warning', confirmText: 'Đồng ý', cancelText: 'Hủy' }
            );
            if (!confirmed) return;

            try {
                const response = await fetch(`/api/events/${id}`, {
                    method: 'DELETE'
                });
                const resData = await response.json();
                if (response.ok) {
                    notify.toast.success('Xóa sự kiện thành công');
                    document.body.dispatchEvent(new CustomEvent('refresh-events', { bubbles: true }));
                } else {
                    notify.toast.error('Xóa thất bại', resData.message || resData.detail || 'Không thể xóa sự kiện');
                }
            } catch (error) {
                console.error('Lỗi khi xóa sự kiện:', error);
                notify.toast.error('Lỗi kết nối', 'Không thể kết nối đến máy chủ');
            }
        }
    };
}

window.adminEventsApp = adminEventsApp;

if (window.Alpine) {
    window.Alpine.data('adminEventsApp', adminEventsApp);
} else {
    document.addEventListener('alpine:init', () => {
        window.Alpine.data('adminEventsApp', adminEventsApp);
    });
}
