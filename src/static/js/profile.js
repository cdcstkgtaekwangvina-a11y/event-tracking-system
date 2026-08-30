/**
 * profile.js
 * Client-side logic for the user profile page (`/user/me`).
 */

document.addEventListener("alpine:init", () => {
  Alpine.data("avatarLibraryPicker", () => ({
    isOpen: false,
    loading: false,
    saving: false,
    folderId: "",
    folderStack: [],
    selected: null,
    search: "",
    viewMode: "grid",
    init() {
      window.avatarLibraryPicker = this;
    },
    async load(folderId = "", pushHistory = false) {
      const container = document.getElementById("avatar-picker-items");
      if (!container) return;
      if (pushHistory && this.folderId) this.folderStack.push(this.folderId);

      this.loading = true;
      this.folderId = folderId || "";
      this.selected = null;

      const params = new URLSearchParams();
      params.set("picker", "true");
      params.set("type_filter", "image");
      params.set("limit", "60");
      if (this.folderId) params.set("folder_id", this.folderId);
      if (this.search) params.set("search", this.search);

      const url =
        window.PROFILE_URLS.mediaManager + "/items/html?" + params.toString();
      container.innerHTML =
        '<div class="media-loading"><div class="spinner-sm"></div><span>Đang tải dữ liệu...</span></div>';
      try {
        await htmx.ajax("GET", url, {
          target: "#avatar-picker-items",
          swap: "innerHTML",
        });
      } finally {
        this.loading = false;
        this.syncSelectionClasses();
      }
    },
    syncSelectionClasses() {
      const container = document.getElementById("avatar-picker-items");
      if (!container) return;
      const selectedId = this.selected?.id;
      container
        .querySelectorAll(".media-row, .media-grid-card")
        .forEach((el) => {
          el.classList.toggle(
            "selected",
            !!selectedId && parseInt(el.dataset.id) === selectedId,
          );
        });
    },
    open() {
      window.activeMediaPicker = this;
      this.isOpen = true;
      this.folderId = "";
      this.folderStack = [];
      this.selected = null;
      this.search = "";
      this.load("");
    },
    close() {
      this.isOpen = false;
    },
    goRoot() {
      this.folderStack = [];
      this.load("");
    },
    goBack() {
      const previousFolderId = this.folderStack.pop();
      this.load(previousFolderId || "");
    },
    handleItemClick(event) {
      const itemEl = event.currentTarget.closest(
        ".media-row, .media-grid-card",
      );
      if (!itemEl) return;

      const kind = itemEl.dataset.mediaKind || itemEl.dataset.type || "file";
      if (kind === "folder") {
        this.load(itemEl.dataset.id, true);
        return;
      }

      this.selected = {
        id: parseInt(itemEl.dataset.id),
        name: itemEl.dataset.mediaName || "",
        url: itemEl.dataset.mediaUrl || "",
      };
      this.syncSelectionClasses();
    },
    async confirm() {
      if (!this.selected || this.saving) return;
      this.saving = true;
      try {
        const res = await window.fetchHelper.put("user/profile/avatar/media", {
          media_id: this.selected.id,
        });
        if (res.status_code === 200) {
          window.notify?.toast?.success?.(
            "Thành công",
            res.message || "Cập nhật ảnh đại diện thành công",
          );
          window.dispatchEvent(
            new CustomEvent("avatar-media-selected", {
              detail: { url: res.data.file_url || res.data.avatar_url },
            }),
          );
          this.close();
        } else {
          window.notify?.toast?.error?.(
            "Lỗi",
            res.message || "Cập nhật ảnh đại diện thất bại",
          );
        }
      } catch (e) {
        window.notify?.toast?.error?.("Lỗi", "Có lỗi xảy ra khi chọn ảnh");
      } finally {
        this.saving = false;
      }
    },
  }));

  Alpine.data("profilePage", (initial) => ({
    role: initial.role,
    isSuperAdmin: initial.is_super_admin,
    avatarUrl: initial.avatar_url,
    createdAt: initial.created_at,
    savingProfile: false,
    changingPassword: false,
    editModalOpen: false,
    passwordModalOpen: false,
    profileData: {
      name: initial.name || "",
      username: initial.username || "",
      email: initial.email || "",
    },
    form: {
      name: initial.name || "",
      username: initial.username || "",
      email: initial.email || "",
    },
    passwordForm: {
      current_password: "",
      new_password: "",
      confirm_new_password: "",
    },
    getInitials(name) {
      if (!name) return "U";
      const parts = name.trim().split(/\s+/).filter(Boolean);
      if (parts.length >= 2) {
        return (
          parts[parts.length - 2][0] + parts[parts.length - 1][0]
        ).toUpperCase();
      }
      return name.substring(0, 2).toUpperCase();
    },
    formatJoinedDate(dateStr) {
      if (!dateStr) return "Tham gia từ gần đây";
      try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return "Tham gia từ gần đây";
        const day = d.getDate();
        const month = d.getMonth() + 1;
        const year = d.getFullYear();
        return `Tham gia từ ${day} tháng ${month}, ${year}`;
      } catch (e) {
        return "Tham gia từ gần đây";
      }
    },
    openEditModal() {
      this.form = {
        name: this.profileData.name,
        username: this.profileData.username,
        email: this.profileData.email,
      };
      this.editModalOpen = true;
    },
    closeEditModal() {
      this.editModalOpen = false;
    },
    openPasswordModal() {
      this.passwordForm = {
        current_password: "",
        new_password: "",
        confirm_new_password: "",
      };
      this.passwordModalOpen = true;
    },
    closePasswordModal() {
      this.passwordModalOpen = false;
    },
    extractErrorMessage(res, fallback) {
      if (Array.isArray(res)) {
        return (
          res
            .map((e) => e.msg || e.message)
            .filter(Boolean)
            .join("; ") || fallback
        );
      }
      return res?.message || fallback;
    },
    goBack() {
      if (document.referrer && document.referrer !== window.location.href) {
        window.history.back();
      } else {
        window.location.href = "/admin";
      }
    },
    roleLabel(role) {
      const labels = {
        SUPPER_ADMIN: "Super Admin",
        ADMIN: "Admin",
        COMMON: "Nhân viên",
      };
      return labels[role] || role || "—";
    },
    async saveProfile() {
      if (this.savingProfile) return;
      const name = this.form.name?.trim();
      const username = this.form.username?.trim();
      const email = this.form.email?.trim();

      if (!name) {
        window.notify?.toast?.error?.("Lỗi", "Họ và tên không được để trống");
        return;
      }
      if (name.length > 300) {
        window.notify?.toast?.error?.(
          "Lỗi",
          "Họ và tên không được vượt quá 300 ký tự",
        );
        return;
      }

      if (!username) {
        window.notify?.toast?.error?.(
          "Lỗi",
          "Tên đăng nhập không được để trống",
        );
        return;
      }
      const usernamePattern = /^[a-zA-Z][a-zA-Z0-9_@]{2,19}$/;
      if (!usernamePattern.test(username)) {
        window.notify?.toast?.error?.(
          "Lỗi",
          "Tên đăng nhập phải bắt đầu bằng chữ cái, dài 3-20 ký tự, không dấu, chỉ được chứa chữ cái, số và các ký tự _ @",
        );
        return;
      }

      if (this.isSuperAdmin && email) {
        const emailPattern =
          /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailPattern.test(email)) {
          window.notify?.toast?.error?.("Lỗi", "Email không đúng định dạng");
          return;
        }
      }

      this.savingProfile = true;
      try {
        const payload = { name: name, username: username };
        if (this.isSuperAdmin && email) payload.email = email;
        const res = await window.fetchHelper.put("user/profile", payload);
        if (res.status_code === 200) {
          window.notify?.toast?.success?.(
            "Thành công",
            res.message || "Cập nhật thông tin thành công",
          );
          this.profileData.name = name;
          this.profileData.username = username;
          if (this.isSuperAdmin && email) this.profileData.email = email;
          this.closeEditModal();
        } else {
          window.notify?.toast?.error?.(
            "Lỗi",
            this.extractErrorMessage(res, "Cập nhật thông tin thất bại"),
          );
        }
      } catch (e) {
        window.notify?.toast?.error?.("Lỗi", "Có lỗi xảy ra khi lưu thông tin");
      } finally {
        this.savingProfile = false;
      }
    },
    async changePassword() {
      if (this.changingPassword) return;
      const { current_password, new_password, confirm_new_password } =
        this.passwordForm;
      if (!current_password || !new_password || !confirm_new_password) {
        window.notify?.toast?.error?.(
          "Lỗi",
          "Vui lòng nhập đầy đủ thông tin mật khẩu",
        );
        return;
      }
      if (new_password !== confirm_new_password) {
        window.notify?.toast?.error?.(
          "Lỗi",
          "Xác nhận mật khẩu mới không khớp",
        );
        return;
      }
      const passwordPattern =
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/;
      if (!passwordPattern.test(new_password.trim())) {
        window.notify?.toast?.error?.(
          "Lỗi",
          "Mật khẩu mới phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt (@$!%*?&)",
        );
        return;
      }
      this.changingPassword = true;
      try {
        const res = await window.fetchHelper.put("user/profile/password", {
          current_password: current_password.trim(),
          new_password: new_password.trim(),
          confirm_new_password: confirm_new_password.trim(),
        });
        if (res.status_code === 200) {
          window.notify?.toast?.success?.(
            "Thành công",
            "Đổi mật khẩu thành công, vui lòng đăng nhập lại",
          );
          this.closePasswordModal();
          setTimeout(() => {
            window.location.href = "/auth/login";
          }, 1500);
        } else {
          window.notify?.toast?.error?.(
            "Lỗi",
            this.extractErrorMessage(res, "Đổi mật khẩu thất bại"),
          );
        }
      } catch (e) {
        window.notify?.toast?.error?.("Lỗi", "Có lỗi xảy ra khi đổi mật khẩu");
      } finally {
        this.changingPassword = false;
      }
    },
  }));
});
