const getTimezone = () => {
  try {
    return (
      Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Ho_Chi_Minh"
    );
  } catch (e) {
    return "Asia/Ho_Chi_Minh";
  }
};

const getDefaultHeaders = () => ({
  "X-Timezone": getTimezone(),
});

const getToken = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
};

const resolveUrl = (path = "") => {
  if (/^https?:\/\//i.test(path)) return path;
  return `${fetchHelper.baseUrl}/${path}`;
};

const buildAuthHeaders = () => {
  const token = getToken("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

async function returnValue(res) {
  if (res.status == 204) return { status_code: 204 };
  const data = await res.json();
  if (data.detail) return data.detail;
  return data;
}

export const contentType = {
  json: "application/json",
  formData: "multipart/form-data",
  text: "text/plain",
  urlencoded: "application/x-www-form-urlencoded",
  html: "text/html",
  css: "text/css",
  js: "application/javascript",
};

export const fetchHelper = {
  baseUrl: "",
  async rawGet(
    path = "",
    payload = {},
    options = { requireAuth: true, headers: {} },
  ) {
    try {
      const queryString = new URLSearchParams(payload).toString();
      const fullPath = queryString ? `${path}?${queryString}` : path;
      const res = await fetch(resolveUrl(fullPath), {
        method: "GET",
        headers: {
          ...getDefaultHeaders(),
          ...(options.headers || { "Content-Type": contentType.json }),
          ...buildAuthHeaders(),
        },
        ...(options.fetchOptions || {}),
      });
      return res;
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },

  async get(
    path = "",
    payload = {},
    options = { requireAuth: true, headers: {} },
  ) {
    try {
      const queryString = new URLSearchParams(payload).toString();
      const fullPath = queryString ? `${path}?${queryString}` : path;
      const res = await fetch(resolveUrl(fullPath), {
        method: "GET",
        headers: {
          ...getDefaultHeaders(),
          ...(options.headers || { "Content-Type": contentType.json }),
          ...buildAuthHeaders(),
        },
      });

      return await returnValue(res);
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },

  async post(
    path = "",
    payload = {},
    options = { requireAuth: false, headers: {} },
  ) {
    try {
      const isFormData = payload instanceof FormData;
      const headers = {
        ...getDefaultHeaders(),
        ...options.headers,
        ...buildAuthHeaders(),
      };
      // Only set Content-Type if not FormData (fetch sets it automatically with boundary)
      if (!isFormData && !headers["Content-Type"]) {
        headers["Content-Type"] = contentType.json;
      }

      const res = await fetch(resolveUrl(path), {
        method: "POST",
        headers,
        body: isFormData ? payload : JSON.stringify(payload),
      });
      return await returnValue(res);
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },

  async put(
    path = "",
    payload = {},
    options = { requireAuth: false, headers: {} },
  ) {
    try {
      const isFormData = payload instanceof FormData;
      const headers = {
        ...getDefaultHeaders(),
        ...(options.headers || {}),
        ...buildAuthHeaders(),
      };
      if (!isFormData && !headers["Content-Type"]) {
        headers["Content-Type"] = contentType.json;
      }

      const res = await fetch(resolveUrl(path), {
        method: "PUT",
        headers,
        body: isFormData ? payload : JSON.stringify(payload),
      });

      return await returnValue(res);
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },

  async patch(
    path = "",
    payload = {},
    options = { requireAuth: false, headers: {} },
  ) {
    try {
      const res = await fetch(resolveUrl(path), {
        method: "PATCH",
        headers: {
          ...getDefaultHeaders(),
          ...(options.headers || { "Content-Type": contentType.json }),
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(payload),
      });

      return await returnValue(res);
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },

  async delete(
    path = "",
    payload = {},
    options = { requireAuth: false, headers: {} },
  ) {
    try {
      const res = await fetch(resolveUrl(path), {
        method: "DELETE",
        headers: {
          ...getDefaultHeaders(),
          ...(options.headers || { "Content-Type": contentType.json }),
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(payload),
      });

      return await returnValue(res);
    } catch (error) {
      console.error("Error fetching data:", error);
      return null;
    }
  },
};
