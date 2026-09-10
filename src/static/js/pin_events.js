/**
 * pin_events.js
 * Quản lý ghim sự kiện (lưu danh sách id sự kiện vào localStorage 'pinned_event_ids', tối đa 5 sự kiện)
 * và tự động đồng bộ trạng thái UI trên toàn bộ hệ thống (Admin, Home, Dashboard).
 */

(function () {
    const STORAGE_KEY = 'pinned_event_ids';
    const MAX_PINNED = 5;

    function getPinnedIds() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            const parsed = JSON.parse(raw || '[]');
            if (Array.isArray(parsed)) {
                return parsed.map(id => parseInt(id)).filter(id => !isNaN(id) && id > 0);
            }
        } catch (e) {
            console.error('Error reading pinned events from localStorage:', e);
        }
        return [];
    }

    function savePinnedIds(ids) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
        } catch (e) {
            console.error('Error saving pinned events to localStorage:', e);
        }
    }

    function showNotification(type, title, message) {
        if (window.notify?.toast?.[type]) {
            window.notify.toast[type](title, message);
        } else {
            // Fallback dispatch show-toast event
            window.dispatchEvent(new CustomEvent('show-toast', {
                detail: { type, title, description: message, duration: 3500 }
            }));
        }
    }

    function updateButtonUI(btn, isPinned) {
        if (!btn) return;
        const icon = btn.querySelector('.material-symbols-outlined');
        if (isPinned) {
            btn.classList.add('is-pinned');
            btn.setAttribute('title', 'Bỏ ghim sự kiện');
            if (icon) icon.style.fontVariationSettings = "'FILL' 1";
        } else {
            btn.classList.remove('is-pinned');
            btn.setAttribute('title', 'Ghim sự kiện');
            if (icon) icon.style.fontVariationSettings = "'FILL' 0";
        }
    }

    function syncAllButtons() {
        const pins = getPinnedIds();
        document.querySelectorAll('.btn-pin-event[data-event-id], .btn-pin-toggle[data-event-id]').forEach(btn => {
            const id = parseInt(btn.getAttribute('data-event-id'));
            if (!isNaN(id)) {
                updateButtonUI(btn, pins.includes(id));
            }
        });
    }

    function togglePinEvent(eventId, btnElement, e) {
        if (e) {
            if (typeof e.preventDefault === 'function') e.preventDefault();
            if (typeof e.stopPropagation === 'function') e.stopPropagation();
        }

        const id = parseInt(eventId);
        if (!id || isNaN(id)) return false;

        let pins = getPinnedIds();
        const index = pins.indexOf(id);
        let isPinned = false;

        if (index > -1) {
            // Remove pin
            pins.splice(index, 1);
            savePinnedIds(pins);
            isPinned = false;
            showNotification('info', 'Đã bỏ ghim sự kiện');
        } else {
            // Check limit
            if (pins.length >= MAX_PINNED) {
                showNotification('warning', 'Đã đạt giới hạn', `Bạn chỉ có thể ghim tối đa ${MAX_PINNED} sự kiện`);
                return false;
            }
            pins.push(id);
            savePinnedIds(pins);
            isPinned = true;
            showNotification('success', 'Đã ghim sự kiện thành công');
        }

        // Update all buttons for this eventId
        document.querySelectorAll(`.btn-pin-event[data-event-id="${id}"], .btn-pin-toggle[data-event-id="${id}"]`).forEach(btn => {
            updateButtonUI(btn, isPinned);
        });

        // If specific button was passed
        if (btnElement) {
            updateButtonUI(btnElement, isPinned);
        }

        // Notify other listeners (e.g. Dashboard)
        window.dispatchEvent(new CustomEvent('pinned-events-changed', {
            detail: { eventId: id, isPinned, pins }
        }));

        return isPinned;
    }

    // Expose globally
    window.getPinnedEventIds = getPinnedIds;
    window.togglePinEvent = togglePinEvent;
    window.togglePinEventGlobal = (e, eventId) => togglePinEvent(eventId, null, e);
    window.syncPinnedButtons = syncAllButtons;

    // Auto sync on page load and HTMX swaps
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', syncAllButtons);
    } else {
        syncAllButtons();
    }

    document.addEventListener('htmx:afterSwap', syncAllButtons);
    document.addEventListener('htmx:load', syncAllButtons);
})();
