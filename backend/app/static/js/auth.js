/* ===================================================================
   FinLedger — auth.js
   Handles login form + register form + validation
   =================================================================== */
(function () {
  /* ---------- Canvas particle background (left panel) ---------- */
  function initParticles(canvas) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H, particles = [];
    const COUNT = 40;
    const MAX_DIST = 130;

    function resize() {
      W = canvas.width  = canvas.offsetWidth * devicePixelRatio;
      H = canvas.height = canvas.offsetHeight * devicePixelRatio;
      ctx.scale(devicePixelRatio, devicePixelRatio);
    }
    function makeParticles() {
      particles = [];
      for (let i = 0; i < COUNT; i++) {
        particles.push({
          x: Math.random() * canvas.offsetWidth,
          y: Math.random() * canvas.offsetHeight,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
          r: 1 + Math.random() * 2
        });
      }
    }
    function step() {
      const cw = canvas.offsetWidth, ch = canvas.offsetHeight;
      ctx.clearRect(0, 0, cw, ch);

      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > cw) p.vx *= -1;
        if (p.y < 0 || p.y > ch) p.vy *= -1;
        p.x = Math.max(0, Math.min(cw, p.x));
        p.y = Math.max(0, Math.min(ch, p.y));
      });

      // Connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const d = Math.hypot(dx, dy);
          if (d < MAX_DIST) {
            ctx.strokeStyle = `rgba(255,255,255,${(1 - d / MAX_DIST) * 0.18})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      // Dots
      particles.forEach(p => {
        ctx.fillStyle = 'rgba(255,255,255,0.65)';
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      });

      requestAnimationFrame(step);
    }

    resize();
    makeParticles();
    step();
    window.addEventListener('resize', () => { resize(); makeParticles(); });
  }

  /* ---------- Validation helpers ---------- */
  function setError(input, msg) {
    const field = input.closest('.field');
    const errEl = field && field.querySelector('.field-error');
    if (errEl) errEl.textContent = msg || '';
    input.classList.toggle('error', !!msg);
  }
  function clearError(input) { setError(input, ''); }

  function validateUsername(v) {
    if (!v) return 'Username is required';
    if (v.length < 3) return 'At least 3 characters';
    if (/\s/.test(v)) return 'No spaces allowed';
    return '';
  }
  function validatePassword(v) {
    if (!v) return 'Password is required';
    if (v.length < 6) return 'At least 6 characters';
    return '';
  }
  function validateConfirm(pw, cpw) {
    if (!cpw) return 'Please confirm your password';
    if (pw !== cpw) return 'Passwords do not match';
    return '';
  }

  /* ---------- Button loading ---------- */
  function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle('loading', loading);
  }

  /* ---------- Toast (standalone for auth pages) ---------- */
  function toast(type, message) {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
    el.innerHTML = `
      <div class="toast-icon">${icon}</div>
      <div class="toast-msg">${escapeHtml(message)}</div>
      <div class="toast-bar"></div>
    `;
    container.appendChild(el);
    setTimeout(() => {
      el.classList.add('closing');
      setTimeout(() => el.remove(), 350);
    }, 3000);
  }
  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    })[c]);
  }

  /* ---------- LOGIN ---------- */
  function initLogin() {
    const form = document.getElementById('login-form');
    if (!form) return;
    const card = document.querySelector('.auth-card');
    const userIn = form.querySelector('#login-username');
    const passIn = form.querySelector('#login-password');
    const btn = form.querySelector('button[type="submit"]');

    [userIn, passIn].forEach(i => i.addEventListener('input', () => clearError(i)));

    // Password show/hide
    const toggle = form.querySelector('[data-toggle-pass]');
    if (toggle) {
      toggle.addEventListener('click', () => {
        const isPw = passIn.type === 'password';
        passIn.type = isPw ? 'text' : 'password';
        toggle.textContent = isPw ? '🙈' : '👁';
      });
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const u = userIn.value.trim();
      const p = passIn.value;
      const uErr = validateUsername(u);
      const pErr = validatePassword(p);
      setError(userIn, uErr);
      setError(passIn, pErr);
      if (uErr || pErr) return;

      setLoading(btn, true);
      try {
        const res = await API.loginForm('/users/login', { username: u, password: p });
        API.setToken(res.access_token);
        toast('success', 'Welcome back!');
        setTimeout(() => { location.href = '/dashboard'; }, 400);
      } catch (err) {
        setLoading(btn, false);
        toast('error', err.message || 'Login failed');
        if (card) { card.classList.add('shake'); setTimeout(() => card.classList.remove('shake'), 500); }
      }
    });
  }

  /* ---------- REGISTER ---------- */
  function initRegister() {
    const form = document.getElementById('register-form');
    if (!form) return;
    const userIn = form.querySelector('#reg-username');
    const passIn = form.querySelector('#reg-password');
    const confIn = form.querySelector('#reg-confirm');
    const btn = form.querySelector('button[type="submit"]');

    [userIn, passIn, confIn].forEach(i => i.addEventListener('input', () => clearError(i)));

    const toggle = form.querySelector('[data-toggle-pass]');
    if (toggle) {
      toggle.addEventListener('click', () => {
        const isPw = passIn.type === 'password';
        passIn.type = isPw ? 'text' : 'password';
        toggle.textContent = isPw ? '🙈' : '👁';
      });
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const u = userIn.value.trim();
      const p = passIn.value;
      const c = confIn.value;
      const uErr = validateUsername(u);
      const pErr = validatePassword(p);
      const cErr = validateConfirm(p, c);
      setError(userIn, uErr);
      setError(passIn, pErr);
      setError(confIn, cErr);
      if (uErr || pErr || cErr) return;

      setLoading(btn, true);
      try {
        await API.post('/users/register', {
          username: u,
          password: p,
          currency: 'INR'
        });
        toast('success', 'Account created! Redirecting to login…');
        setTimeout(() => { location.href = '/login'; }, 900);
      } catch (err) {
        setLoading(btn, false);
        toast('error', err.message || 'Registration failed');
      }
    });
  }

  /* ---------- Init ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    initParticles(document.getElementById('auth-canvas'));
    initLogin();
    initRegister();
  });
})();