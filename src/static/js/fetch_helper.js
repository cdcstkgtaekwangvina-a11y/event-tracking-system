const getToken = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
};
export const fetchHelper = {
  baseUrl: "",
  async get(
    path = "",
    payload = {},
    options = { requireAuth: true, headers: {} },
  ) {
    try {
      const queryString = new URLSearchParams(payload).toString();
      const fullPath = queryString ? `${path}?${queryString}` : path;
      const res = await fetch(`${this.baseUrl}${fullPath}`, {
        method: "GET",
        headers: {
          ...(options.headers || { "Content-Type": contentType.json }),
          ...(options.requireAuth
            ? { Authorization: `Bearer ${getToken("access_token")}` }
            : {}),
        },
      });

      return await res.json();
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },
  async post(path = "", payload = {}, options = { requireAuth: false }) {
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: {
          ...(options.headers || { "Content-Type": contentType.json }),
          ...(options.requireAuth
            ? { Authorization: `Bearer ${getToken("access_token")}` }
            : {}),
        },
        body: JSON.stringify(payload),
      });
      return await res.json();
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },
  async put(path = "", payload = {}, options = { requireAuth: false }) {
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method: "PUT",
        headers: {
          ...(options.headers || { "Content-Type": contentType.json }),
          ...(options.requireAuth
            ? { Authorization: `Bearer ${getToken("access_token")}` }
            : {}),
        },
        body: JSON.stringify(payload),
      });

      return await res.json();
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },
  async patch(path = "", payload = {}, options = { requireAuth: false }) {
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method: "PUT",
        headers: {
          ...(options.headers || { "Content-Type": contentType.json }),
          ...(options.requireAuth
            ? { Authorization: `Bearer ${getToken("access_token")}` }
            : {}),
        },
        body: JSON.stringify(payload),
      });

      return await res.json();
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },
  async delete(path = "", payload = {}, options = { requireAuth: false }) {
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method: "DELETE",
        headers: {
          ...(options.headers || { "Content-Type": contentType.json }),
          ...(options.requireAuth
            ? { Authorization: `Bearer ${getToken("access_token")}` }
            : {}),
        },
        body: JSON.stringify(payload),
      });

      return await res.json();
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },
};

export const contentType = {
  json: "application/json",
  formData: "multipart/form-data",
  text: "text/plain",
  urlencoded: "application/x-www-form-urlencoded",
  html: "text/html",
  css: "text/css",
  js: "application/javascript",
};
