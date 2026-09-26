/* ===================================================================
   FinLedger — theme.js
   Dark mode: reads localStorage → OS preference → applies + toggle
   Uses Icons.render for sun/moon SVGs.
   =================================================================== */
(function () {
  const KEY = 'finledger.theme';

  function getStoredTheme() {
    try { return localStorage.getItem(KEY); } catch { return null; }
  }
  function setStoredTheme(t) {
    try { localStorage.setItem(KEY, t); } catch {}
  }
  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    const iconName = t === 'dark' ? 'sun' : 'moon';
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
      // If Icons is not loaded yet, fall back to text emoji
      if (window.Icons && Icons.render) {
        btn.innerHTML = Icons.render(iconName, { size: 20 });
      } else {
        btn.textContent = t === 'dark' ? '☀️' : '🌙';
      }
      btn.setAttribute('aria-label', t === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    });
  }
  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }
  function toggleTheme() {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    setStoredTheme(next);
    applyTheme(next);
  }

  // Apply immediately
  const stored = getStoredTheme();
  const initial = stored || (systemPrefersDark() ? 'dark' : 'light');
  applyTheme(initial);

  if (!stored && window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      if (!getStoredTheme()) applyTheme(e.matches ? 'dark' : 'light');
    });
  }

  window.FinLedgerTheme = { toggle: toggleTheme, current: currentTheme };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
      btn.addEventListener('click', toggleTheme);
      const t = currentTheme();
      if (window.Icons && Icons.render) {
        btn.innerHTML = Icons.render(t === 'dark' ? 'sun' : 'moon', { size: 20 });
      } else {
        btn.textContent = t === 'dark' ? '☀️' : '🌙';
      }
    });
  });
})();