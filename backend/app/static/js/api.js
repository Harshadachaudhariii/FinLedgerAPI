/* ===================================================================
   FinLedger — api.js
   Fetch wrapper + token handling + 401 auto-logout
   =================================================================== */
(function () {
  const TOKEN_KEY = 'finledger.token';

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  }
  function setToken(t) {
    try { localStorage.setItem(TOKEN_KEY, t); } catch {}
  }
  function clearToken() {
    try { localStorage.removeItem(TOKEN_KEY); } catch {}
  }

  function buildHeaders(json = true, extra = {}) {
    const h = { ...extra };
    if (json) h['Content-Type'] = 'application/json';
    const t = getToken();
    if (t) h['Authorization'] = `Bearer ${t}`;
    return h;
  }

  function handleUnauthorized() {
    clearToken();
    if (!location.pathname.startsWith('/login') && location.pathname !== '/') {
      location.href = '/login';
    }
  }

  async function parseResponse(res) {
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      try { return await res.json(); } catch { return null; }
    }
    if (ct.includes('text/csv') || ct.includes('application/pdf') || ct.includes('octet-stream')) {
      return await res.blob();
    }
    try { return await res.text(); } catch { return null; }
  }

  async function request(method, path, body, opts = {}) {
    const { form = false, raw = false } = opts;
    const headers = raw
      ? buildHeaders(false)
      : form
        ? buildHeaders(false, { 'Content-Type': 'application/x-www-form-urlencoded' })
        : buildHeaders(true);

    const init = { method, headers };

    if (body !== undefined && body !== null) {
      if (raw || form) init.body = body;
      else init.body = JSON.stringify(body);
    }

    let res;
    try {
      res = await fetch(path, init);
    } catch (e) {
      const err = new Error('Network error. Check your connection.');
      err.status = 0;
      throw err;
    }

    if (res.status === 401) {
      handleUnauthorized();
      const data = await parseResponse(res);
      const msg = (data && data.detail) || 'Session expired. Please log in again.';
      const err = new Error(msg);
      err.status = 401;
      throw err;
    }

    if (!res.ok) {
      const data = await parseResponse(res);
      const msg = (data && (data.detail || data.message)) || `Request failed (${res.status})`;
      const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return parseResponse(res);
  }

  const API = {
    get:  (path, opts)       => request('GET', path, null, opts),
    post: (path, body, opts) => request('POST', path, body, opts),
    put:  (path, body, opts) => request('PUT', path, body, opts),
    del:  (path, opts)       => request('DELETE', path, null, opts),

    // OAuth2 form-encoded login
    loginForm(path, params) {
      const usp = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => usp.append(k, v));
      return request('POST', path, usp.toString(), { form: true });
    },

    // File download (csv/pdf)
    download(path) {
      return request('GET', path, null, {});
    },

    // Upload multipart (csv import)
    upload(path, formData) {
      const headers = buildHeaders(false);
      return fetch(path, { method: 'POST', headers, body: formData })
        .then(async res => {
          if (res.status === 401) { handleUnauthorized(); throw new Error('Session expired'); }
          if (!res.ok) {
            const data = await parseResponse(res);
            throw new Error((data && (data.detail || data.message)) || `Upload failed (${res.status})`);
          }
          return parseResponse(res);
        });
    },

    token: getToken,
    setToken,
    clearToken,
    logout() {
      clearToken();
      location.href = '/login';
    },
    requireAuth() {
      if (!getToken()) location.href = '/login';
    },
    isAuthed() {
      return !!getToken();
    }
  };

  window.API = API;
})();