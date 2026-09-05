/**
 * account.js
 * Client-side logic for the Account admin module.
 */

window.accountActions = {
  async toggleActive(id, isActive) {
    const actionLabel = isActive ? "chặn" : "bỏ chặn";
    const approved = await window.notify.modal.confirm(
      "Xác nhận",
      `Bạn có chắc muốn ${actionLabel} tài khoản này?`,
    );
    if (!approved) return;

    const res = await window.fetchHelper.put("account/" + id, {
      is_active: !isActive,
    });
    if (res.status_code === 200) {
      window.notify?.toast?.success?.(
        "Thành công",
        res.message || "Cập nhật trạng thái thành công",
      );
      const tableUrl = new URL(
        window.ACCOUNT_URLS.accountsTable,
        window.location.origin,
      );
      const curParams = new URLSearchParams(window.location.search);
      ["page", "limit", "search", "sort_field", "is_desc"].forEach((k) => {
        if (curParams.has(k)) tableUrl.searchParams.set(k, curParams.get(k));
      });
      htmx.ajax("GET", tableUrl.toString(), {
        target: "#acc-table-container",
        swap: "innerHTML",
      });
    } else {
      window.notify?.toast?.error?.(
        "Lỗi",
        res.message || "Cập nhật trạng thái thất bại",
      );
    }
  },
};

function accountFormModalComponent(canEditEmail) {
  return {
    isOpen: false,
    mode: "create",
    account: null,
    loading: false,
    showPassword: false,
    canEditEmail: !!canEditEmail,
    errors: {},
    form: {
      name: "",
      username: "",
      email: "",
      password: "",
    },
    init() {
      window.accountFormModalInstance = this;
    },
    open(options = {}) {
      this.mode = options.mode || "create";
      this.showPassword = false;
      this.errors = {};
      if (this.mode === "edit" && options.account) {
        this.account = options.account;
        this.form = {
          name: options.account.name || "",
          username: options.account.username || "",
          email: options.account.email || "",
          password: "",
        };
      } else {
        this.account = null;
        this.form = { name: "", username: "", email: "", password: "" };
      }
      this.isOpen = true;
    },
    close() {
      this.isOpen = false;
      this.showPassword = false;
    },
    generatePassword() {
      const lowercase = "abcdefghijklmnopqrstuvwxyz";
      const uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
      const numbers = "0123456789";
      const specials = "@$!%*?&";
      const allChars = lowercase + uppercase + numbers + specials;

      const pwd = [
        lowercase[Math.floor(Math.random() * lowercase.length)],
        uppercase[Math.floor(Math.random() * uppercase.length)],
        numbers[Math.floor(Math.random() * numbers.length)],
        specials[Math.floor(Math.random() * specials.length)],
      ];

      const length = 12;
      for (let i = pwd.length; i < length; i++) {
        pwd.push(allChars[Math.floor(Math.random() * allChars.length)]);
      }

      for (let i = pwd.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [pwd[i], pwd[j]] = [pwd[j], pwd[i]];
      }

      this.form.password = pwd.join("");
      this.showPassword = true;
      window.notify?.toast?.success?.(
        "Thành công",
        "Đã tạo mật khẩu ngẫu nhiên",
      );
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
    validateForm() {
      const name = this.form.name?.trim();
      const username = this.form.username?.trim();
      const email = this.form.email?.trim();
      const password = this.form.password;

      this.errors = {};

      // 1. Validate Họ và tên (name)
      if (!name) {
        this.errors.name = "Họ và tên không được để trống";
        return false;
      }
      if (name.length > 300) {
        this.errors.name = "Họ và tên không được vượt quá 300 ký tự";
        return false;
      }

      // 2. Validate Tên đăng nhập (username)
      if (!username) {
        this.errors.username = "Tên đăng nhập không được để trống";
        return false;
      }
      const usernamePattern = /^[a-zA-Z][a-zA-Z0-9_@]{2,19}$/;
      if (!usernamePattern.test(username)) {
        this.errors.username =
          "Tên đăng nhập phải bắt đầu bằng chữ cái, dài 3-20 ký tự, không dấu, chỉ được chứa chữ cái, số và các ký tự _ @";
        return false;
      }

      // 3. Validate Email
      if (this.mode === "create" && !email) {
        this.errors.email = "Email không được để trống";
        return false;
      }
      if (email && (this.mode === "create" || this.canEditEmail)) {
        const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailPattern.test(email)) {
          this.errors.email = "Email không đúng định dạng";
          return false;
        }
        if (email.length > 300) {
          this.errors.email = "Email không được vượt quá 300 ký tự";
          return false;
        }
      }

      // 4. Validate Mật khẩu (password)
      if (this.mode === "create" && (!password || !password.trim())) {
        this.errors.password = "Mật khẩu không được để trống";
        return false;
      }

      if (password) {
        const passwordPattern =
          /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/;
        if (!passwordPattern.test(password.trim())) {
          this.errors.password =
            "Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt (@$!%*?&)";
          return false;
        }
      }

      return true;
    },
    clearFieldError(field) {
      if (this.errors[field]) {
        this.errors[field] = null;
      }
    },
    async submit() {
      if (this.loading) return;
      if (!this.validateForm()) return;

      this.loading = true;
      try {
        let res;
        if (this.mode === "edit") {
          const payload = {
            name: this.form.name.trim(),
            username: this.form.username.trim(),
          };
          if (this.form.password) payload.password = this.form.password.trim();
          if (this.canEditEmail && this.form.email)
            payload.email = this.form.email.trim();
          res = await window.fetchHelper.put(
            "account/" + this.account.id,
            payload,
          );
        } else {
          res = await window.fetchHelper.post("account", {
            name: this.form.name.trim(),
            username: this.form.username.trim(),
            email: this.form.email.trim(),
            password: this.form.password.trim(),
          });
        }

        if (res.status_code === 200 || res.status_code === 201) {
          window.notify?.toast?.success?.(
            "Thành công",
            res.message ||
              (this.mode === "edit"
                ? "Cập nhật thành công"
                : "Tạo tài khoản thành công"),
          );
          this.close();
          const tableUrl = new URL(
            window.ACCOUNT_URLS.accountsTable,
            window.location.origin,
          );
          const curParams = new URLSearchParams(window.location.search);
          ["page", "limit", "search", "sort_field", "is_desc"].forEach((k) => {
            if (curParams.has(k))
              tableUrl.searchParams.set(k, curParams.get(k));
          });
          if (this.mode === "create") tableUrl.searchParams.set("page", "1");
          htmx.ajax("GET", tableUrl.toString(), {
            target: "#acc-table-container",
            swap: "innerHTML",
          });
        } else {
          window.notify?.toast?.error?.(
            "Lỗi",
            this.extractErrorMessage(res, "Có lỗi xảy ra"),
          );
        }
      } catch (e) {
        window.notify?.toast?.error?.("Lỗi", "Có lỗi xảy ra khi lưu dữ liệu");
      } finally {
        this.loading = false;
      }
    },
  };
}

accountFormModalComponent.open = function (options = {}) {
  if (
    window.accountFormModalInstance &&
    typeof window.accountFormModalInstance.open === "function"
  ) {
    window.accountFormModalInstance.open(options);
  }
};

window.accountFormModal = accountFormModalComponent;

function initAlpineAccount() {
  if (!window.Alpine || typeof window.Alpine.data !== "function") return;
  window.Alpine.data("accountFormModal", accountFormModalComponent);
}

if (window.Alpine) {
  initAlpineAccount();
} else {
  document.addEventListener("alpine:init", initAlpineAccount);
}
