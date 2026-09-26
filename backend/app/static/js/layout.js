/* ===================================================================
   FinLedger — layout.js
   Renders sidebar + topbar on all dashboard pages.
   Exposes UI helpers. Uses Icons.render for all SVGs.
   =================================================================== */
(function () {
  const IC = (name, size = 20) =>
    (window.Icons && Icons.render(name, { size })) || '';

  const NAV_ITEMS = [
    { key: 'overview',     label: 'Overview',     href: '/dashboard',              icon: 'home' },
    { key: 'transactions', label: 'Transactions', href: '/dashboard#transactions', icon: 'creditCard' },
    { key: 'summary',      label: 'Summary',      href: '/summary',                icon: 'documentText' },
    { key: 'budgets',      label: 'Budgets',      href: '/budgets',                icon: 'target' },
    { key: 'analytics',    label: 'Analytics',    href: '/analytics',              icon: 'analytics' },
    { key: 'settings',     label: 'Settings',     href: '/dashboard#settings',     icon: 'settings' }
  ];

  function currentPageKey() {
    const p = location.pathname;
    if (p.startsWith('/summary'))   return 'summary';
    if (p.startsWith('/budgets'))   return 'budgets';
    if (p.startsWith('/analytics')) return 'analytics';
    if (p.startsWith('/dashboard')) {
      const hash = location.hash.replace('#', '');
      if (hash === 'transactions' || hash === 'settings') return hash;
      return 'overview';
    }
    return 'overview';
  }

  function buildSidebar() {
    const nav = document.getElementById('sidebar-nav');
    if (!nav) return;
    const active = currentPageKey();
    nav.innerHTML = NAV_ITEMS.map(item => `
      <a href="${item.href}" class="nav-item ${item.key === active ? 'active' : ''}" data-nav="${item.key}">
        <span class="nav-icon">${IC(item.icon, 20)}</span>
        <span>${item.label}</span>
      </a>
    `).join('');
  }

  async function buildTopbar() {
    const titleEl = document.getElementById('page-title');
    if (titleEl) titleEl.textContent = document.title.replace('FinLedger — ', '');

    const chip = document.getElementById('user-chip');
    if (chip && API.isAuthed()) {
      try {
        const me = await API.get('/users/me');
        const initial = (me.username || '?').charAt(0);
        chip.innerHTML = `
          <div class="avatar">${escapeHtml(initial)}</div>
          <span class="username">${escapeHtml(me.username)}</span>
        `;
      } catch {
        chip.innerHTML = `<div class="avatar">${IC('user', 16)}</div>`;
      }
    }

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.innerHTML = IC('logout', 20);
      logoutBtn.addEventListener('click', async () => {
        try { await API.post('/users/logout'); } catch {}
        API.logout();
      });
    }

    const ham = document.getElementById('hamburger');
    if (ham) ham.innerHTML = IC('menu', 22);

    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (ham && sidebar && overlay) {
      ham.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('active');
      });
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
      });
    }
  }

  /* ---------- TOAST ---------- */
  function ensureToastContainer() {
    let c = document.querySelector('.toast-container');
    if (!c) {
      c = document.createElement('div');
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  function toast(type, message, timeout = 3000) {
    const container = ensureToastContainer();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const iconName = type === 'success' ? 'check' : type === 'error' ? 'close' : 'info';
    el.innerHTML = `
      <div class="toast-icon">${IC(iconName, 14)}</div>
      <div class="toast-msg">${escapeHtml(message)}</div>
      <div class="toast-bar"></div>
    `;
    container.appendChild(el);
    setTimeout(() => {
      el.classList.add('closing');
      setTimeout(() => el.remove(), 350);
    }, timeout);
  }

  /* ---------- MODAL ---------- */
  function ensureModalRoot() {
    let root = document.getElementById('modal-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'modal-root';
      document.body.appendChild(root);
    }
    return root;
  }

  function openModal({ title, bodyHTML, footerHTML, size = '', onMount, onClose }) {
    const root = ensureModalRoot();
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop open';
    backdrop.innerHTML = `
      <div class="modal ${size}" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>${escapeHtml(title)}</h3>
          <button class="modal-close" data-close aria-label="Close">${IC('close', 18)}</button>
        </div>
        <div class="modal-body">${bodyHTML}</div>
        ${footerHTML ? `<div class="modal-footer">${footerHTML}</div>` : ''}
      </div>
    `;
    root.appendChild(backdrop);

    const close = () => {
      backdrop.remove();
      if (typeof onClose === 'function') onClose();
    };
    backdrop.querySelector('[data-close]').addEventListener('click', close);
    backdrop.addEventListener('click', e => { if (e.target === backdrop) close(); });
    document.addEventListener('keydown', escClose);
    function escClose(e) {
      if (e.key === 'Escape') { close(); document.removeEventListener('keydown', escClose); }
    }

    if (typeof onMount === 'function') onMount(backdrop, close);
    return { close, el: backdrop };
  }

  /* ---------- CONFIRM ---------- */
  function confirmDialog({ title = 'Are you sure?', message = '', confirmText = 'Delete', cancelText = 'Cancel' }) {
    return new Promise(resolve => {
      openModal({
        title,
        size: 'confirm',
        bodyHTML: `
          <div class="icon-circle">${IC('warning', 28)}</div>
          <p>${escapeHtml(message)}</p>
        `,
        footerHTML: `
          <button class="btn btn-ghost" data-cancel>${escapeHtml(cancelText)}</button>
          <button class="btn btn-danger" data-confirm>${escapeHtml(confirmText)}</button>
        `,
        onMount(root, doClose) {
          root.querySelector('[data-cancel]').addEventListener('click', () => { doClose(); resolve(false); });
          root.querySelector('[data-confirm]').addEventListener('click', () => { doClose(); resolve(true); });
        },
        onClose() { resolve(false); }
      });
    });
  }

  /* ---------- FORMATTERS ---------- */
  function formatMoney(value, currency = 'INR') {
    if (value === null || value === undefined || isNaN(value)) return '₹0.00';
    try {
      return new Intl.NumberFormat('en-IN', {
        style: 'currency', currency, maximumFractionDigits: 2
      }).format(Number(value));
    } catch {
      return `₹${Number(value).toFixed(2)}`;
    }
  }

  function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
  function formatMonth(ym) {
    if (!ym) return '—';
    const [y, m] = ym.split('-');
    const d = new Date(Number(y), Number(m) - 1, 1);
    return d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
  }
  function todayISO() {
    const d = new Date();
    const z = d.getTimezoneOffset() * 60000;
    return new Date(d - z).toISOString().slice(0, 10);
  }
  function currentMonth() { return todayISO().slice(0, 7); }
  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    })[c]);
  }

  /* ---------- COUNT-UP ---------- */
  function countUp(el, to, { duration = 900, formatter = v => v } = {}) {
    const from = 0;
    const start = performance.now();
    const target = Number(to) || 0;
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const val = from + (target - from) * eased;
      el.textContent = formatter(val);
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  /* ---------- SKELETON HELPERS ---------- */
  function skeletonKPIs(n = 4) {
    return Array.from({ length: n }, () => `<div class="skeleton skeleton-kpi"></div>`).join('');
  }
  function skeletonChart() { return `<div class="skeleton skeleton-chart"></div>`; }
  function skeletonRows(n = 8) {
    return Array.from({ length: n }, () => `
      <div class="skeleton-row">
        <span class="skeleton skeleton-line"></span>
        <span class="skeleton skeleton-line"></span>
        <span class="skeleton skeleton-line"></span>
        <span class="skeleton skeleton-line"></span>
        <span class="skeleton skeleton-line"></span>
      </div>`).join('');
  }
  function skeletonCards(n = 6) {
    return Array.from({ length: n }, () => `<div class="skeleton skeleton-card"></div>`).join('');
  }
  function skeletonBlocks(n = 3) {
    return Array.from({ length: n }, () => `<div class="skeleton skeleton-block"></div>`).join('');
  }

  /* ---------- INIT ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    buildSidebar();
    buildTopbar();
  });

  /* ---------- EXPORT ---------- */
  window.UI = {
    toast, openModal, confirmDialog,
    formatMoney, formatDate, formatMonth,
    todayISO, currentMonth, escapeHtml, countUp,
    skeletonKPIs, skeletonChart, skeletonRows, skeletonCards, skeletonBlocks,
    icon: IC  // expose icon renderer for other scripts
  };
})();