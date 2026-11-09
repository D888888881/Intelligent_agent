function getCookie(name) {
  const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return m ? decodeURIComponent(m[2]) : "";
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const csrf = getCookie("csrftoken");
  if (csrf) headers["X-CSRFToken"] = csrf;
  const res = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg =
      data.detail ||
      data.non_field_errors?.[0] ||
      (data.username && (Array.isArray(data.username) ? data.username[0] : data.username)) ||
      (data.real_name && (Array.isArray(data.real_name) ? data.real_name[0] : data.real_name)) ||
      "请求失败";
    throw new Error(msg);
  }
  return data;
}

async function ensureCsrf() {
  await fetch("/api/auth/csrf/", { credentials: "same-origin" });
}

function showError(msg) {
  const el = document.getElementById("auth-error");
  const ok = document.getElementById("auth-success");
  if (ok) ok.classList.add("hidden");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function showSuccess(msg) {
  const el = document.getElementById("auth-success");
  const err = document.getElementById("auth-error");
  if (err) err.classList.add("hidden");
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
}

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await ensureCsrf();
    const data = await api("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify({
        real_name: fd.get("real_name"),
        username: fd.get("username"),
        password: fd.get("password"),
      }),
    });
    e.target.reset();
    showSuccess(data.detail || "注册申请已提交，请等待超级管理员审批。");
  } catch (err) {
    showError(err.message);
  }
});

ensureCsrf();
