/* ==========================================
   From header.j2
   ========================================== */
var managerPageUrl = window.managerPageUrl || "/media";
    var trashPageUrl = window.trashPageUrl || "/trash";
    var deleted_media = window.location.pathname === new URL(trashPageUrl, window.location.origin).pathname;

    var syncHeaderState = window.syncHeaderState = window.syncHeaderState || (() => {
        const header = document.querySelector('.media-header');
        if (!header || !window.Alpine || typeof Alpine.$data !== 'function') return;
        const data = Alpine.$data(header);
        if (!data) return;
        const params = new URLSearchParams(window.location.search);
        const isTrashPage = window.location.pathname === new URL(trashPageUrl, window.location.origin).pathname;
        deleted_media = isTrashPage;
        data.folder_id = params.get('folder_id') || '';
        data.current_media = null;
        if (typeof data.getCurrentMedia === 'function') {
            data.getCurrentMedia();
        }
    });

    document.addEventListener('alpine:init', () => {
        window.mediaActions = {
            marqueeState: {
                active: false,
                pointerId: null,
                boundRoot: null,
                box: null,
                startX: 0,
                startY: 0,
                lastX: 0,
                lastY: 0,
                suppressClickUntil: 0,
            },
            isMarqueeActive() {
                return this.marqueeState.active;
            },
            shouldSuppressItemClick() {
                return Date.now() < this.marqueeState.suppressClickUntil;
            },
            initMarqueeSelection(root) {
                if (!root || this.marqueeState.boundRoot === root) return;
                this.marqueeState.boundRoot = root;
                this.marqueeState.box = null;
                this.marqueeState.active = false;
                this.marqueeState.pointerId = null;

                const getStore = () => Alpine.store('mediaSelection');
                const isInteractive = (target) => !!target.closest(
                    'button, a, input, textarea, select, label, [role="button"], .card-more-menu, .action-buttons, .bulk-action-toolbar'
                );

                const getItems = () => Array.from(root.querySelectorAll('.media-row, .media-grid-card'))
                    .filter((item) => item.getClientRects().length > 0);

                const ensureBox = () => {
                    let box = this.marqueeState.box;
                    if (!box) {
                        box = document.createElement('div');
                        box.className = 'media-selection-box';
                        root.appendChild(box);
                        this.marqueeState.box = box;
                    }
                    return box;
                };

                const clearBox = () => {
                    if (this.marqueeState.box) {
                        this.marqueeState.box.remove();
                        this.marqueeState.box = null;
                    }
                };

                const setSelection = (ids, additive) => {
                    const store = getStore();
                    if (!store) return;

                    if (additive) {
                        const merged = new Set(store.getSelectedIds());
                        ids.forEach(id => merged.add(id));
                        store.selectedIds = Array.from(merged);
                        return;
                    }

                    store.selectAll(ids);
                };

                const updateSelection = () => {
                    if (!this.marqueeState.active) return;

                    const rootRect = root.getBoundingClientRect();
                    const left = Math.min(this.marqueeState.startX, this.marqueeState.lastX);
                    const right = Math.max(this.marqueeState.startX, this.marqueeState.lastX);
                    const top = Math.min(this.marqueeState.startY, this.marqueeState.lastY);
                    const bottom = Math.max(this.marqueeState.startY, this.marqueeState.lastY);

                    const box = ensureBox();
                    box.style.left = `${left - rootRect.left}px`;
                    box.style.top = `${top - rootRect.top}px`;
                    box.style.width = `${Math.max(0, right - left)}px`;
                    box.style.height = `${Math.max(0, bottom - top)}px`;

                    const rect = {
                        left,
                        right,
                        top,
                        bottom,
                    };

                    const selectedIds = [];
                    for (const item of getItems()) {
                        const itemRect = item.getBoundingClientRect();
                        const intersects = !(
                            itemRect.right < rect.left ||
                            itemRect.left > rect.right ||
                            itemRect.bottom < rect.top ||
                            itemRect.top > rect.bottom
                        );
                        if (intersects) {
                            selectedIds.push(parseInt(item.dataset.id));
                        }
                    }

                    const store = getStore();
                    if (!store) return;

                    if (this.marqueeState.additive) {
                        const merged = new Set(this.marqueeState.initialSelectedIds || []);
                        selectedIds.forEach(id => merged.add(id));
                        store.selectedIds = Array.from(merged);
                    } else {
                        store.selectedIds = selectedIds;
                    }
                };

                const endSelection = () => {
                    const pointerId = this.marqueeState.pointerId;
                    if (pointerId !== null && root.hasPointerCapture?.(pointerId)) {
                        root.releasePointerCapture?.(pointerId);
                    }
                    if (!this.marqueeState.active) {
                        this.marqueeState.pointerId = null;
                        root.style.userSelect = '';
                        clearBox();
                        return;
                    }
                    this.marqueeState.active = false;
                    this.marqueeState.pointerId = null;
                    this.marqueeState.suppressClickUntil = Date.now() + 250;
                    clearBox();
                    root.style.userSelect = '';
                };

                root.addEventListener('pointerdown', (event) => {
                    if (event.button !== 0) return;
                    if (deleted_media) return;
                    if (event.pointerType === 'touch') return;
                    if (isInteractive(event.target) || event.target.closest('.media-grid-card, .media-row')) return;

                    this.marqueeState.startX = event.clientX;
                    this.marqueeState.startY = event.clientY;
                    this.marqueeState.lastX = event.clientX;
                    this.marqueeState.lastY = event.clientY;
                    this.marqueeState.pointerId = event.pointerId;
                    this.marqueeState.active = false;
                    this.marqueeState.additive = event.ctrlKey || event.metaKey || event.shiftKey;
                    this.marqueeState.initialSelectedIds = new Set((Alpine.store('mediaSelection')?.getSelectedIds?.() || []));

                    root.setPointerCapture?.(event.pointerId);
                });

                root.addEventListener('pointermove', (event) => {
                    if (this.marqueeState.pointerId !== event.pointerId) return;
                    const dx = Math.abs(event.clientX - this.marqueeState.startX);
                    const dy = Math.abs(event.clientY - this.marqueeState.startY);
                    this.marqueeState.lastX = event.clientX;
                    this.marqueeState.lastY = event.clientY;

                    if (!this.marqueeState.active) {
                        if (dx < 5 && dy < 5) return;
                        this.marqueeState.active = true;
                        root.style.userSelect = 'none';
                        if (!this.marqueeState.additive) {
                            const store = getStore();
                            store?.clear();
                        }
                        ensureBox();
                    }

                    event.preventDefault();
                    updateSelection();
                });

                root.addEventListener('pointerup', (event) => {
                    if (this.marqueeState.pointerId !== event.pointerId) return;
                    endSelection();
                });

                root.addEventListener('pointercancel', (event) => {
                    if (this.marqueeState.pointerId !== event.pointerId) return;
                    endSelection();
                });
            },
            getHeaderBottomData() {
                const headerBottom = document.querySelector('.media-header-bottom');
                if (!headerBottom || !window.Alpine || typeof Alpine.$data !== 'function') {
                    return null;
                }
                return Alpine.$data(headerBottom);
            },
            isDeletedView() {
                return deleted_media === true;
            },
            reloadItems(extraParams = {}) {
                const container = document.getElementById('media-items-container');
                if (!container) return false;

                const params = new URLSearchParams(window.location.search);
                if (Object.prototype.hasOwnProperty.call(extraParams, 'includeDeleted')) {
                    if (extraParams.includeDeleted) {
                        params.set('deleted_media', 'true');
                        deleted_media = true;
                    } else {
                        params.delete('deleted_media');
                        deleted_media = false;
                    }
                } else {
                    deleted_media = window.location.pathname === new URL(trashPageUrl, window.location.origin).pathname;
                    if (deleted_media) {
                        params.set('deleted_media', 'true');
                    } else {
                        params.delete('deleted_media');
                    }
                }

                const query = params.toString();
                const url = `{{ url_for('media_manager') }}/items/html${query ? `?${query}` : ''}`;
                const selectionStore = Alpine.store('mediaSelection');
                if (selectionStore) {
                    selectionStore.clear();
                }
                container.innerHTML = `<div class='media-loading'><div class='spinner-sm'></div><span>Đang tải dữ liệu...</span></div>`;
                htmx.ajax('GET', url, { target: '#media-items-container', swap: 'innerHTML' });
                syncHeaderState();
                return true;
            },
            setHasData(value) {
                const header = document.querySelector('.media-header');
                if (!header || !window.Alpine || typeof Alpine.$data !== 'function') return;
                const data = Alpine.$data(header);
                if (data) {
                    data.hasData = !!value;
                }
            },
            goToFolder(id) {
                const params = new URLSearchParams();
                params.set('folder_id', id);
                if (deleted_media) params.set('deleted_media', 'true');
                window.history.pushState(null, '', `?${params.toString()}`);
                this.reloadItems();
            },
            goHome() {
                const params = new URLSearchParams();
                if (deleted_media) params.set('deleted_media', 'true');
                window.history.pushState(null, '', deleted_media ? trashPageUrl : managerPageUrl);
                this.reloadItems();
            },
            showTrash(folderId) {
                const params = new URLSearchParams();
                params.set('deleted_media', 'true');
                if (folderId) params.set('folder_id', folderId);
                deleted_media = true;

                const parentXData = this.getHeaderBottomData();
                if (parentXData) {
                    parentXData.filterValue = 'all';
                    parentXData.reload({ includeDeleted: true });
                } else {
                    window.history.pushState(null, '', `?${params.toString()}`);
                    this.reloadItems({ includeDeleted: true });
                }
                syncHeaderState();
            },
            goManager() {
                deleted_media = false;
                window.history.pushState(null, '', managerPageUrl);
                this.reloadItems();
            },
            move(itemId) {
                window.dispatchEvent(new CustomEvent('open-move-modal', { detail: { itemId: itemId } }));
            },
            async edit(id, type) {
                // Find the name element in both list and grid views
                const row = document.querySelector(`.media-row[data-id="${id}"]`);
                const card = document.querySelector(`.media-grid-card[data-id="${id}"]`);
                const nameEl = row?.querySelector('.media-name-text') || card?.querySelector('.card-name');
                if (!nameEl) return;

                const oldName = nameEl.textContent.trim();

                // If in Grid view, show custom rename modal
                const isGridView = localStorage.getItem('mediaViewMode') === 'grid' || !row;
                if (isGridView) {
                    if (window.mediaRenameModal) {
                        window.mediaRenameModal.open({
                            itemId: id,
                            oldName: oldName,
                            nameEl: nameEl,
                            rowEl: row,
                            cardEl: card
                        });
                    }
                    return;
                }

                // List view: keep inline input
                if (nameEl.dataset.editing === 'true') return;
                nameEl.dataset.editing = 'true';

                // Create inline input
                const input = document.createElement('input');
                input.type = 'text';
                input.value = oldName;
                input.className = 'inline-rename-input';
                input.style.cssText = 'width: 100%; padding: 2px 6px; font-size: inherit; border: 1px solid var(--primary); border-radius: 4px; background: var(--bg-secondary); color: var(--text-primary); outline: none;';

                nameEl.textContent = '';
                nameEl.appendChild(input);
                input.focus();
                input.select();

                const save = async () => {
                    const newName = input.value.trim();
                    if (!newName || newName === oldName) {
                        // Revert
                        nameEl.textContent = oldName;
                        delete nameEl.dataset.editing;
                        return;
                    }

                    try {
                        const json = await window.fetchHelper.patch(`media/${id}`, { name: newName });
                        if (json && json.status_code === 200) {
                            nameEl.textContent = newName;
                            // Also update the other view's name if exists
                            const otherEl = row ? card?.querySelector('.card-name') : row?.querySelector('.media-name-text');
                            if (otherEl) otherEl.textContent = newName;
                            window.notify.toast.success('Thành công', 'Đã đổi tên');
                        } else {
                            nameEl.textContent = oldName;
                            window.notify.toast.error('Lỗi', json?.message || 'Đổi tên thất bại');
                        }
                    } catch (err) {
                        console.error(err);
                        nameEl.textContent = oldName;
                        window.notify.toast.error('Lỗi', 'Có lỗi xảy ra');
                    }
                    delete nameEl.dataset.editing;
                };

                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
                    if (e.key === 'Escape') { input.value = oldName; input.blur(); }
                });
                input.addEventListener('blur', save, { once: true });
            },
            async deleteItem(id, type) {
                const approved = await window.notify.modal.confirm(
                    deleted_media ? 'Xóa vĩnh viễn dữ liệu' : 'Xóa dữ liệu',
                    deleted_media
                        ? `Bạn có chắc muốn xoá vĩnh viễn ${type === 'folder' ? 'thư mục' : 'file'} này không?`
                        : `Bạn có chắc muốn xoá ${type === 'folder' ? 'thư mục' : 'file'} này không?`,
                    { icon: 'warning', confirmText: deleted_media ? 'Xóa vĩnh viễn' : 'Xóa', cancelText: 'Hủy' }
                );
                if (!approved) return;

                const loadingId = window.notify.toast.loading('Đang xử lý', 'Vui lòng chờ...');
                try {
                    const json = await window.fetchHelper.delete(`media/${id}?is_soft_delete=${!deleted_media}`);
                    window.notify.toast.dismiss(loadingId);

                    if (!json || json.status_code !== 204) {
                        window.notify.toast.error('Lỗi', json?.message || 'Xóa thất bại');
                        return;
                    }

                    window.notify.toast.success('Thành công', `Đã ${deleted_media ? 'xóa vĩnh viễn' : 'chuyển vào thùng rác'}`);
                    this.reloadItems();
                } catch (error) {
                    console.error(error);
                    window.notify.toast.dismiss(loadingId);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra khi xóa');
                }
            },
            async moveToFolder(itemId, targetFolderId) {
                const loadingId = window.notify.toast.loading('Đang xử lý', 'Vui lòng chờ...');
                try {
                    const json = await window.fetchHelper.patch(`media/${itemId}`, { folder_id: parseInt(targetFolderId) });
                    window.notify.toast.dismiss(loadingId);

                    if (!json || json.status_code !== 200 || json.success === false) {
                        window.notify.toast.error('Lỗi', json?.message || 'Di chuyển thất bại');
                        return;
                    }

                    window.notify.toast.success('Thành công', 'Đã di chuyển dữ liệu');
                    this.reloadItems();
                } catch (error) {
                    console.error(error);
                    window.notify.toast.dismiss(loadingId);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra khi di chuyển');
                }
            },
            // Selection functions
            toggleSelectItem(event, id) {
                event.stopPropagation();
                const store = Alpine.store('mediaSelection');
                if (store) {
                    store.toggle(id);
                }
            },
            toggleSelectAll(event, view) {
                const store = Alpine.store('mediaSelection');
                if (!store) return;

                const container = document.getElementById(view === 'list' ? 'media-list-view' : 'media-grid-view');
                if (!container) return;

                const checkboxes = container.querySelectorAll('.row-checkbox, .grid-checkbox');
                const ids = Array.from(checkboxes).map(cb => {
                    const row = cb.closest('.media-row, .media-grid-card');
                    return row ? parseInt(row.dataset.id) : null;
                }).filter(Boolean);

                if (event.target.checked) {
                    store.selectAll(ids);
                } else {
                    store.clear();
                }
            },
            // Bulk delete
            async bulkDelete() {
                const store = Alpine.store('mediaSelection');
                if (!store || !store.hasSelection()) return;

                const ids = store.getSelectedIds();
                const count = ids.length;

                // Sử dụng confirm modal trực tiếp thay vì info modal chỉ để hiển thị
                const approved = await window.notify.modal.confirm(
                    deleted_media ? 'Xóa vĩnh viễn nhiều mục' : 'Xóa nhiều mục',
                    deleted_media
                        ? `Bạn có chắc muốn xoá vĩnh viễn ${count} mục này không?`
                        : `Bạn có chắc muốn chuyển ${count} mục này vào thùng rác không?`,
                    {
                        icon: 'warning',
                        confirmText: deleted_media ? 'Xóa vĩnh viễn' : 'Xóa',
                        cancelText: 'Hủy'
                    }
                );

                if (!approved) return;

                const loadingId = window.notify.toast.loading('Đang xử lý', `Đang xóa ${count} mục...`);
                try {
                    const json = await window.fetchHelper.delete('media/bulk-delete', {
                        ids: ids,
                        is_soft_delete: !deleted_media
                    });
                    window.notify.toast.dismiss(loadingId);

                    if (!json || json.success === false) {
                        window.notify.toast.error('Lỗi', json?.message || 'Xóa thất bại');
                        return;
                    }

                    window.notify.toast.success('Thành công', deleted_media ? `Đã xóa vĩnh viễn ${count} mục` : `Đã chuyển ${count} mục vào thùng rác`);
                    store.clear();
                    this.reloadItems();
                } catch (error) {
                    console.error(error);
                    window.notify.toast.dismiss(loadingId);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra khi xóa');
                }
            },

            async restore(id) {
                try {
                    const res = await window.fetchHelper.patch("media/restore/" + id);
                    if (res.status_code === 200) {
                        window.notify.toast.success('Thành công', `Đã khôi phục dữ liệu`);
                        this.reloadItems({ includeDeleted: true });
                        return;
                    }
                    window.notify.toast.error('Lỗi', res?.message || 'Khôi phục thất bại');
                    return;

                }
                catch (error) {
                    console.error(error);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra khi khôi phục');
                }
            },
            async emptyTrash() {
                if (!deleted_media) {
                    this.goManager();
                    return;
                }

                const approved = await window.notify.modal.confirm(
                    'Làm trống thùng rác',
                    'Bạn có chắc muốn xoá vĩnh viễn toàn bộ dữ liệu trong thùng rác không?',
                    { icon: 'warning', confirmText: 'Xóa vĩnh viễn', cancelText: 'Hủy' }
                );
                if (!approved) return;

                const loadingId = window.notify.toast.loading('Đang xử lý', 'Vui lòng chờ...');
                try {
                    const json = await window.fetchHelper.delete('media/empty-trash');
                    window.notify.toast.dismiss(loadingId);

                    if (!json || json.success === false) {
                        window.notify.toast.error('Lỗi', json?.message || 'Làm trống thùng rác thất bại');
                        return;
                    }

                    window.notify.toast.success('Thành công', 'Đã làm trống thùng rác');
                    this.reloadItems({ includeDeleted: true });
                } catch (error) {
                    console.error(error);
                    window.notify.toast.dismiss(loadingId);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra khi làm trống thùng rác');
                }
            },
            async forceDownload(url, filename) {
                try {
                    // 1. Fetch dữ liệu từ URL về dưới dạng Blob
                    const response = await fetch(url);
                    if (!response.ok) throw new Error('Không thể tải file');

                    const blob = await response.blob();

                    // 2. Tạo một URL tạm thời trỏ đến Blob vừa tải
                    const blobUrl = window.URL.createObjectURL(blob);

                    // 3. Tạo thẻ <a> ảo và kích hoạt download
                    const a = document.createElement('a');
                    a.href = blobUrl;
                    a.download = filename || url.split('/').pop() || 'download';
                    document.body.appendChild(a);
                    a.click();

                    // 4. Dọn dẹp bộ nhớ
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(blobUrl);
                } catch (error) {
                    console.error('Lỗi tải file:', error);
                    // Phương án dự phòng nếu bị chặn CORS: Mở trực tiếp link trong tab mới
                    window.open(url, '_blank');
                }
            }
        };

        // Emit view mode changes so header and items_grid can sync
        document.addEventListener('view-mode-changed', (e) => {
            const detail = e.detail || {};
            window.dispatchEvent(new CustomEvent('view-mode-changed', { detail }))
        });
    });

/* ==========================================
   From header.j2
   ========================================== */
document.addEventListener('alpine:init', () => {
        Alpine.data('folderMoveModal', () => ({
            isOpen: false,
            loading: false,
            itemId: null,
            currentParentId: null,
            folders: [],
            breadcrumbs: [],

            async openModal(itemId) {
                this.itemId = itemId;
                this.isOpen = true;
                this.breadcrumbs = [];
                this.currentParentId = null;
                await this.loadFolders(null);
            },

            closeModal() {
                this.isOpen = false;
            },

            async loadFolders(folder) {
                this.loading = true;
                try {
                    const parentId = folder ? folder.id : null;
                    this.currentParentId = parentId;

                    const payload = { type_filter: 'folder', size: 100 };
                    if (parentId) payload.parent_id = parentId;

                    const res = await window.fetchHelper.get(`media`, payload);

                    if (res && res.data) {
                        this.folders = res.data.data.filter(f => f.id != this.itemId);
                    } else {
                        this.folders = [];
                    }

                    if (!folder) {
                        this.breadcrumbs = [];
                    } else {
                        const index = this.breadcrumbs.findIndex(b => b.id === folder.id);
                        if (index >= 0) {
                            this.breadcrumbs = this.breadcrumbs.slice(0, index + 1);
                        } else {
                            this.breadcrumbs.push({ id: folder.id, name: folder.name });
                        }
                    }
                } catch (err) {
                    console.error(err);
                } finally {
                    this.loading = false;
                }
            },

            async confirmMove(targetFolderId) {
                if (targetFolderId == this.itemId) {
                    window.notify.toast.error('Lỗi', 'Không thể di chuyển thư mục vào chính nó');
                    return;
                }
                this.closeModal();
                if (window.mediaActions && window.mediaActions.moveToFolder) {
                    await window.mediaActions.moveToFolder(this.itemId, targetFolderId || -1);
                }
            }
        }));
    });

/* ==========================================
   From header.j2
   ========================================== */
document.addEventListener('alpine:init', () => {
        registerMediaModals();
    });

    function registerMediaModals() {
        if (!window.Alpine || window.__mediaModalsRegistered) return;
        window.__mediaModalsRegistered = true;

        Alpine.data('mediaCreateModal', () => ({
            isOpen: false,
            mode: 'folder',
            folderId: null,
            folderName: '',
            fileName: '',
            fileSizeBytes: null,
            maxFileSizeMb: 50,
            maxFileSizeLabel: '50 MB',
            isDisable: false,

            openModal(data) {
                this.mode = data.mode || 'folder';
                this.folderId = data.folderId || null;
                this.folderName = '';
                this.fileName = '';
                this.fileSizeBytes = null;
                this.isOpen = true;
                this.isDisable = false;
                if (this.mode === 'folder') {
                    setTimeout(() => {
                        this.$refs.folderInput && this.$refs.folderInput.focus();
                    }, 100);
                }
                if (this.mode === 'file') {
                    this.getMaxUploadSizeLimit();
                }
            },

            closeModal() {
                this.isOpen = false;
            },

            async getMaxUploadSizeLimit() {
                try {
                    const res = await window.fetchHelper.get('setting/max_file_sizes');
                    if (!res || res.status_code !== 200 || !res.data) {
                        return;
                    }
                    const candidate = res.data?.value.max_size_file;
                    const raw = typeof candidate === 'object' ? Object.values(candidate)[0] : candidate;
                    const size = Number(raw);
                    if (Number.isNaN(size) || size <= 0) return;
                    this.maxFileSizeMb = size / 1024 / 1024;
                    this.maxFileSizeLabel = this.formatBytes(size);
                } catch (error) {
                    console.error('Không thể lấy cấu hình upload', error);
                }
            },

            formatBytes(bytes) {
                if (!bytes || bytes <= 0) return '50 MB';
                const units = ['B', 'KB', 'MB', 'GB', 'TB'];
                const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
                return `${(bytes / Math.pow(1024, index)).toFixed(1)} ${units[index]}`;
            },

            clearFile() {
                this.fileName = '';
                this.fileSizeBytes = null;
                const fileInput = this.$refs.fileInput;
                if (fileInput) fileInput.value = '';
            },

            onFileSelected(event) {
                const file = event.target?.files?.[0];
                if (file) {
                    this.fileName = file.name;
                    this.fileSizeBytes = file.size;
                }
            },

            handleFileDrop(event) {
                const file = event.dataTransfer?.files?.[0];
                if (file) {
                    this.fileName = file.name;
                    this.fileSizeBytes = file.size;
                }
            },

            async submit() {
                if (this.mode === 'folder') {
                    if (this.isDisable) return;
                    await this.submitFolder();
                } else {
                    if (this.isDisable) return;
                    await this.submitFile();
                }
            },

            async submitFolder() {
                if (this.isDisable) return;
                if (!this.folderName.trim()) {
                    window.notify.toast.error('Lỗi', 'Vui lòng nhập tên thư mục');
                    return;
                }
                const loadingId = window.notify.toast.loading('Đang xử lý', 'Vui lòng chờ...');
                try {
                    this.isDisable = true;
                    const formData = new FormData();
                    formData.append('name', this.folderName.trim());
                    formData.append('is_folder', 'true');
                    if (this.folderId && this.folderId !== 'null' && this.folderId !== '') {
                        formData.append('folder_id', this.folderId);
                    }

                    const res = await window.fetchHelper.post('media', formData);

                    window.notify.toast.dismiss(loadingId);

                    if (res.status_code === 201) {
                        window.notify.toast.success('Thành công', 'Đã tạo thư mục');
                        this.closeModal();

                        window.mediaActions?.reloadItems();
                    } else {
                        window.notify.toast.error('Lỗi', res?.message || 'Tên thư mục đã tồn tại hoặc không hợp lệ');
                    }
                    this.isDisable = false;
                } catch (err) {
                    console.error(err);
                    window.notify.toast.dismiss(loadingId);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra khi tạo thư mục');
                    this.isDisable = false;
                }
            },

            async submitFile() {
                if (this.isDisable) return;

                const fileInput = this.$refs.fileInput;
                if (!fileInput || !fileInput.files.length) {
                    window.notify.toast.error('Lỗi', 'Vui lòng chọn file để tải lên');
                    this.isDisable = false;
                    return;
                }
                const maxBytes = this.maxFileSizeMb * 1024 * 1024;
                if (this.fileSizeBytes && maxBytes && this.fileSizeBytes > maxBytes) {
                    window.notify.toast.error('Lỗi', 'File vượt quá giới hạn cho phép');
                    this.isDisable = false;
                    return;
                }
                this.isDisable = true;
                const file = fileInput.files[0];
                const loadingId = window.notify.toast.loading('Đang xử lý', 'Vui lòng chờ...');
                try {
                    const formData = new FormData();
                    formData.append('name', this.fileName.trim() || file.name);
                    formData.append('is_folder', 'false');
                    formData.append('file', file);
                    if (this.folderId && this.folderId !== 'null' && this.folderId !== '') {
                        formData.append('folder_id', this.folderId);
                    }

                    const res = await window.fetchHelper.post('media', formData);

                    window.notify.toast.dismiss(loadingId);

                    if (res && res.success !== false && res.status_code !== 400 && res.status_code !== 422) {
                        window.notify.toast.success('Thành công', 'Đã tải file lên');
                        this.closeModal();

                        window.mediaActions?.reloadItems();
                    } else {
                        window.notify.toast.error('Lỗi', res?.message || 'Tải file thất bại');
                    }

                    this.isDisable = false;
                } catch (err) {
                    console.error(err);
                    window.notify.toast.dismiss(loadingId);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra khi tải file');
                    this.isDisable = false;
                }
            }
        }));

        Alpine.data('mediaRenameModal', () => ({
            isOpen: false,
            isDisable: false,
            itemId: null,
            newName: '',
            oldName: '',
            nameEl: null,
            rowEl: null,
            cardEl: null,

            openModal(data) {
                this.itemId = data.itemId;
                this.oldName = data.oldName;
                this.newName = data.oldName;
                this.nameEl = data.nameEl;
                this.rowEl = data.rowEl;
                this.cardEl = data.cardEl;
                this.isOpen = true;
                this.isDisable = false;
                setTimeout(() => {
                    this.$refs.renameInput && this.$refs.renameInput.focus();
                }, 100);
            },

            closeModal() {
                this.isOpen = false;
            },

            async submit() {
                if (this.isDisable) return;
                const trimmedName = this.newName.trim();
                if (!trimmedName) {
                    window.notify.toast.error('Lỗi', 'Vui lòng nhập tên mới');
                    return;
                }
                if (trimmedName === this.oldName) {
                    this.closeModal();
                    return;
                }

                const loadingId = window.notify.toast.loading('Đang xử lý', 'Vui lòng chờ...');
                try {
                    this.isDisable = true;
                    const json = await window.fetchHelper.patch(`media/${this.itemId}`, { name: trimmedName });
                    window.notify.toast.dismiss(loadingId);
                    if (json && json.status_code === 200) {
                        if (this.nameEl) this.nameEl.textContent = trimmedName;
                        const otherEl = this.rowEl ? this.cardEl?.querySelector('.card-name') : this.rowEl?.querySelector('.media-name-text');
                        if (otherEl) otherEl.textContent = trimmedName;
                        window.notify.toast.success('Thành công', 'Đã đổi tên');
                        this.closeModal();
                    } else {
                        window.notify.toast.error('Lỗi', json?.message || 'Đổi tên thất bại');
                    }
                } catch (err) {
                    console.error(err);
                    window.notify.toast.dismiss(loadingId);
                    window.notify.toast.error('Lỗi', 'Có lỗi xảy ra');
                } finally {
                    this.isDisable = false;
                }
            }
        }));

        // Expose helper trigger for Alpine
        window.mediaCreateModal = {
            open: (data) => window.dispatchEvent(new CustomEvent('open-create-modal', { detail: data }))
        };

        window.mediaRenameModal = {
            open: (data) => window.dispatchEvent(new CustomEvent('open-rename-modal', { detail: data }))
        };
    }

    if (window.Alpine) {
        registerMediaModals();
    }

/* ==========================================
   From items_grid.j2
   ========================================== */
if (window.Alpine) {
        const header = document.querySelector('.media-header');
        if (header) {
            const data = Alpine.$data(header);
            const newFolderId = "{{ folder_id if folder_id else 'null' }}";
            if (newFolderId != 'null' && data.folder_id !== newFolderId) {
                data.folder_id = newFolderId;
                if (data.folder_id) {
                    data.getCurrentMedia();
                } else {
                    data.current_media = null;
                }
            }
        };
    }