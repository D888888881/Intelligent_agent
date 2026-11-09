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

  el.textContent = msg;

  el.classList.remove("hidden");

}



document.getElementById("login-form").addEventListener("submit", async (e) => {

  e.preventDefault();

  const fd = new FormData(e.target);

  try {

    await ensureCsrf();

    await api("/api/auth/login/", {

      method: "POST",

      body: JSON.stringify({

        username: fd.get("username"),

        password: fd.get("password"),

      }),

    });

    window.location.href = "/";

  } catch (err) {

    showError(err.message);

  }

});



ensureCsrf();

