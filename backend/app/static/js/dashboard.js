/* ===================================================================
   FinLedger — dashboard.js
   Sections: Overview, Transactions, Settings
   =================================================================== */
(function () {
  const CATEGORIES = [
    "Rent","Mortgage","Utilities","Internet & Phone","Home Maintenance","Insurance",
    "Food","Groceries","Dining Out","Coffee Shops",
    "Transport","Fuel","Car Maintenance","Taxi & Ride Share","Public Transit",
    "Shopping","Clothing","Personal Care","Electronics","Household Supplies",
    "Health","Pharmacy","Gym & Fitness","Dental & Vision",
    "Entertainment","Subscriptions","Travel","Hobbies","Gaming",
    "Savings","Investments","Debt Repayment","Credit Card Payment","Taxes","Charity",
    "Education","Childcare","Pets","Donations","Gift",
    "Salary","Freelance","Bonus","Gift Received","Dividends","Interest","Refunds","Business Income","Rental Income",
    "Other"
  ];

  const PAYMENT_METHODS = ["Debit Card","Credit Card","UPI","Cash","Bank Transfer"];
  const MERCHANTS = [
    "Employer Payroll","Apartment Management","Local Grocery & Restaurant","Local Transport",
    "Utility Provider","Freelance Client","Entertainment Service","Healthcare Provider",
    "Retail Store","Online Learning Platform","Family"
  ];

  let chartMonthly = null;
  let chartCategory = null;
  let allTransactions = [];

  /* ================= ROUTER ================= */
  function showSection(name) {
    document.querySelectorAll('.section').forEach(s => {
      s.classList.toggle('hidden', s.dataset.section !== name);
    });
    document.querySelectorAll('.nav-item').forEach(a => {
      a.classList.toggle('active', a.dataset.nav === name);
    });
    const titles = { overview: 'Dashboard', transactions: 'Transactions', settings: 'Settings' };
    const t = document.getElementById('page-title');
    if (t) t.textContent = titles[name] || 'Dashboard';

    if (name === 'transactions') loadTransactions();
    if (name === 'settings') loadSettings();
    if (name === 'overview') loadOverview();
  }

  function handleHash() {
    const hash = location.hash.replace('#', '');
    if (hash === 'transactions') showSection('transactions');
    else if (hash === 'settings') showSection('settings');
    else showSection('overview');
  }

  /* ================= OVERVIEW ================= */
  async function loadOverview() {
    const kpiGrid = document.getElementById('kpi-grid');
    const recentBody = document.getElementById('recent-body');

    kpiGrid.innerHTML = UI.skeletonKPIs(4);
    recentBody.innerHTML = `<tr><td colspan="4"><div class="skeleton skeleton-line" style="margin:12px 0;"></div></td></tr>`;

    let dashboard = null, monthly = null, byCat = null, overview = null;
    try {
      [dashboard, monthly, byCat, overview] = await Promise.all([
        API.get('/transactions/dashboard'),
        API.get('/transactions/summary/monthly'),
        API.get('/transactions/summary/by-category'),
        API.get('/transactions/summary/overview')
      ]);
    } catch (e) {
      kpiGrid.innerHTML = `<div class="card no-hover">Failed to load: ${UI.escapeHtml(e.message)}</div>`;
      return;
    }

    const currency = overview.currency || 'INR';

        kpiGrid.innerHTML = `
      <div class="kpi">
        <div class="kpi-label">Total Income</div>
        <div class="kpi-value income" data-kpi="income">${UI.formatMoney(0, currency)}</div>
        <div class="kpi-sub">All-time earnings</div>
        <div class="kpi-icon income">${UI.icon('arrowUp', 20)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Total Expense</div>
        <div class="kpi-value expense" data-kpi="expense">${UI.formatMoney(0, currency)}</div>
        <div class="kpi-sub">All-time spending</div>
        <div class="kpi-icon expense">${UI.icon('arrowDown', 20)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Net Balance</div>
        <div class="kpi-value primary" data-kpi="net">${UI.formatMoney(0, currency)}</div>
        <div class="kpi-sub">Income − Expense</div>
        <div class="kpi-icon bare rupee">${UI.icon('rupee', 28)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">This Month</div>
        <div class="kpi-value" data-kpi="month">${UI.formatMoney(0, currency)}</div>
        <div class="kpi-sub">Net balance this month</div>
        <div class="kpi-icon warning">${UI.icon('calendar', 20)}</div>
      </div>
    `;

    const incEl = kpiGrid.querySelector('[data-kpi="income"]');
    const expEl = kpiGrid.querySelector('[data-kpi="expense"]');
    const netEl = kpiGrid.querySelector('[data-kpi="net"]');
    const monEl = kpiGrid.querySelector('[data-kpi="month"]');

    UI.countUp(incEl, overview.total_income, { formatter: v => UI.formatMoney(v, currency) });
    UI.countUp(expEl, overview.total_expense, { formatter: v => UI.formatMoney(v, currency) });
    UI.countUp(netEl, overview.net_balance, { formatter: v => UI.formatMoney(v, currency) });
    UI.countUp(monEl, dashboard.current_month_net_balance, { formatter: v => UI.formatMoney(v, currency) });

    // --- RECENT TRANSACTIONS ---
    const recent = dashboard.recent_transactions || [];
    if (!recent.length) {
      recentBody.innerHTML = `
        <tr><td colspan="4">
          <div class="empty">
            ${UI.icon('inbox', 56)}
            <h3>No transactions yet</h3>
            <p>Add your first transaction to see it here.</p>
          </div>
        </td></tr>`;
    } else {
      recentBody.innerHTML = recent.map((t, i) => `
        <tr style="animation:fadeInUp .3s ease ${i * 40}ms both;">
          <td data-label="Date">${UI.formatDate(t.dates)}</td>
          <td data-label="Category">${UI.escapeHtml(t.category)}</td>
          <td data-label="Type"><span class="pill ${t.type}">${t.type}</span></td>
          <td data-label="Amount" class="right ${t.type === 'income' ? 'text-income' : 'text-expense'}" style="font-weight:600;">
            ${t.type === 'income' ? '+' : '−'}${UI.formatMoney(t.amount, currency)}
          </td>
        </tr>
      `).join('');
    }

    // --- CHARTS ---
    renderMonthlyChart(monthly.monthly_summary || [], currency);
    renderCategoryChart(byCat.breakdown || [], currency);
  }

  function renderMonthlyChart(data, currency) {
    const ctx = document.getElementById('chart-monthly');
    if (!ctx) return;
    if (chartMonthly) chartMonthly.destroy();

    const labels = data.map(d => UI.formatMonth(d.month));
    const income = data.map(d => d.income);
    const expense = data.map(d => d.expense);

    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--muted').trim();
    const borderColor = styles.getPropertyValue('--border').trim();

    chartMonthly = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Income',  data: income,  backgroundColor: '#10b981', borderRadius: 6 },
          { label: 'Expense', data: expense, backgroundColor: '#ef4444', borderRadius: 6 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: textColor, font: { family: 'Inter' } } },
          tooltip: {
            callbacks: {
              label: c => `${c.dataset.label}: ${UI.formatMoney(c.parsed.y, currency)}`
            }
          }
        },
        scales: {
          x: { ticks: { color: textColor }, grid: { display: false } },
          y: {
            ticks: { color: textColor, callback: v => UI.formatMoney(v, currency) },
            grid: { color: borderColor }
          }
        }
      }
    });
  }

  function renderCategoryChart(data, currency) {
    const ctx = document.getElementById('chart-category');
    if (!ctx) return;
    if (chartCategory) chartCategory.destroy();

    const top = data.slice(0, 5);
    const rest = data.slice(5);
    let labels = top.map(d => d.category);
    let values = top.map(d => d.amount);
    if (rest.length) {
      labels.push('Other');
      values.push(rest.reduce((s, d) => s + d.amount, 0));
    }

    if (!labels.length) {
      labels = ['No data'];
      values = [1];
    }

    const palette = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#64748b'];
    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--muted').trim();

    chartCategory = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: palette.slice(0, labels.length),
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: textColor, font: { family: 'Inter' }, boxWidth: 12, padding: 12 }
          },
          tooltip: {
            callbacks: {
              label: c => `${c.label}: ${UI.formatMoney(c.parsed, currency)}`
            }
          }
        }
      }
    });
  }

  /* ================= TRANSACTIONS ================= */
  function fillCategoryFilter() {
    const sel = document.getElementById('f-category');
    if (!sel || sel.dataset.filled) return;
    CATEGORIES.forEach(c => {
      const o = document.createElement('option');
      o.value = c; o.textContent = c;
      sel.appendChild(o);
    });
    sel.dataset.filled = '1';
  }

  async function loadTransactions(filters = {}) {
    const tbody = document.getElementById('tx-body');
    const skel = document.getElementById('tx-skeleton');
    if (!tbody) return;

    fillCategoryFilter();
    tbody.innerHTML = '';
    skel.classList.remove('hidden');
    skel.innerHTML = UI.skeletonRows(6);

    try {
      const params = new URLSearchParams();
      if (filters.type)      params.append('type', filters.type);
      if (filters.category)  params.append('category', filters.category);
      if (filters.start_date)params.append('start_date', filters.start_date);
      if (filters.end_date)  params.append('end_date', filters.end_date);
      if (filters.search)    params.append('search', filters.search);

      const path = params.toString() ? `/transactions/filter?${params}` : '/transactions?limit=100';
      const res = await API.get(path);

      // /transactions returns {data: [...]}, /filter returns list
      allTransactions = Array.isArray(res) ? res : (res.data || []);

      renderTransactionsTable(allTransactions);
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="6"><div class="empty">Failed to load: ${UI.escapeHtml(e.message)}</div></td></tr>`;
    } finally {
      skel.classList.add('hidden');
      skel.innerHTML = '';
    }
  }

  function renderTransactionsTable(items) {
    const tbody = document.getElementById('tx-body');
    if (!items.length) {
      tbody.innerHTML = `
        <tr><td colspan="6">
          <div class="empty">
            ${UI.icon('inbox', 56)}
            <h3>No transactions found</h3>
            <p>Try changing filters or add a new transaction.</p>
          </div>
        </td></tr>`;
      return;
    }
    tbody.innerHTML = items.map((t, i) => `
      <tr style="animation:fadeInUp .25s ease ${Math.min(i*20,300)}ms both;">
        <td data-label="Date">${UI.formatDate(t.dates)}</td>
        <td data-label="Category">${UI.escapeHtml(t.category)}</td>
        <td data-label="Type"><span class="pill ${t.type}">${t.type}</span></td>
        <td data-label="Description">${UI.escapeHtml(t.description || t.notes || '—')}</td>
        <td data-label="Amount" class="right ${t.type === 'income' ? 'text-income' : 'text-expense'}" style="font-weight:600;">
          ${t.type === 'income' ? '+' : '−'}${UI.formatMoney(t.amount)}
        </td>
        <td data-label="Actions" class="actions">
          <button class="btn-icon" data-edit="${t.id}" title="Edit">${UI.icon('edit', 18)}</button>
          <button class="btn-icon danger" data-del="${t.id}" title="Delete">${UI.icon('trash', 18)}</button>
        </td>
    `).join('');

    tbody.querySelectorAll('[data-edit]').forEach(b => {
      b.addEventListener('click', () => {
        const id = b.dataset.edit;
        const tx = allTransactions.find(x => x.id === id);
        if (tx) openTransactionModal(tx);
      });
    });
    tbody.querySelectorAll('[data-del]').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.dataset.del;
        const ok = await UI.confirmDialog({
          title: 'Delete transaction?',
          message: 'This action cannot be undone.',
          confirmText: 'Delete'
        });
        if (!ok) return;
        try {
          await API.del(`/transactions/delete/${id}`);
          UI.toast('success', 'Transaction deleted');
          loadTransactions(currentFilters());
        } catch (e) {
          UI.toast('error', e.message);
        }
      });
    });
  }

  function currentFilters() {
    return {
      type: document.getElementById('f-type')?.value || '',
      category: document.getElementById('f-category')?.value || '',
      start_date: document.getElementById('f-start')?.value || '',
      end_date: document.getElementById('f-end')?.value || '',
      search: document.getElementById('f-search')?.value || ''
    };
  }

  /* ================= TRANSACTION MODAL ================= */
  function openTransactionModal(tx = null) {
    const isEdit = !!tx;
    const body = `
      <form id="tx-form" novalidate>
        <div class="field">
          <label>Type <span class="req">*</span></label>
          <div class="radio-row">
            <label class="radio-pill income">
              <input type="radio" name="type" value="income" ${tx?.type === 'income' ? 'checked' : ''} />
              <span>Income</span>
            </label>
            <label class="radio-pill expense">
              <input type="radio" name="type" value="expense" ${(!tx || tx?.type === 'expense') ? 'checked' : ''} />
              <span>Expense</span>
            </label>
          </div>
          <div class="field-error" data-for="type"></div>
        </div>

        <div class="field">
          <label>Amount (₹) <span class="req">*</span></label>
          <input type="number" step="0.01" min="0" class="input" name="amount"
                 value="${tx?.amount ?? ''}" placeholder="0.00" />
          <div class="field-error" data-for="amount"></div>
        </div>

        <div class="field">
          <label>Category <span class="req">*</span></label>
          <select class="select" name="category">
            <option value="">Select a category</option>
            ${CATEGORIES.map(c => `<option value="${c}" ${tx?.category === c ? 'selected' : ''}>${c}</option>`).join('')}
          </select>
          <div class="field-error" data-for="category"></div>
        </div>

        <div class="field">
          <label>Date <span class="req">*</span></label>
          <input type="date" class="input" name="dates" value="${tx?.dates || UI.todayISO()}" />
          <div class="field-error" data-for="dates"></div>
        </div>

        <div class="field">
          <label>Payment Method</label>
          <select class="select" name="payment_method">
            <option value="">—</option>
            ${PAYMENT_METHODS.map(p => `<option value="${p}" ${tx?.payment_method === p ? 'selected' : ''}>${p}</option>`).join('')}
          </select>
        </div>

        <div class="field">
          <label>Description</label>
          <textarea class="textarea" name="description" placeholder="Optional notes…">${tx?.description ?? ''}</textarea>
        </div>

        <div class="field">
          <label>Recurring</label>
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <input type="checkbox" name="is_recurring" ${tx?.is_recurring ? 'checked' : ''} />
            <span>Repeat this transaction monthly</span>
          </label>
        </div>

        <div class="field" id="rec-day-field" style="display:${tx?.is_recurring ? 'block' : 'none'};">
          <label>Recurrence day (1–31)</label>
          <input type="number" min="1" max="31" class="input" name="recurrence_day"
                 value="${tx?.recurrence_day ?? ''}" placeholder="Day of month" />
        </div>
      </form>
    `;

    const footer = `
      <button class="btn btn-ghost" data-cancel>Cancel</button>
      <button class="btn btn-primary" id="tx-save">
        <span class="spinner"></span>
        <span class="btn-label">${isEdit ? 'Update' : 'Create'}</span>
      </button>
    `;

    UI.openModal({
      title: isEdit ? 'Edit Transaction' : 'Add Transaction',
      bodyHTML: body,
      footerHTML: footer,
      onMount(root, close) {
        const form = root.querySelector('#tx-form');
        const recurring = form.querySelector('[name="is_recurring"]');
        const recField = form.querySelector('#rec-day-field');
        recurring.addEventListener('change', () => {
          recField.style.display = recurring.checked ? 'block' : 'none';
        });

        root.querySelector('[data-cancel]').addEventListener('click', close);

        root.querySelector('#tx-save').addEventListener('click', async () => {
          const saveBtn = root.querySelector('#tx-save');

          // Clear old errors
          form.querySelectorAll('.field-error').forEach(e => e.textContent = '');
          form.querySelectorAll('.error').forEach(e => e.classList.remove('error'));

          const fd = new FormData(form);
          const type = fd.get('type');
          const amount = parseFloat(fd.get('amount'));
          const category = fd.get('category');
          const dates = fd.get('dates');
          const is_recurring = fd.get('is_recurring') === 'on';
          const recurrence_day_raw = fd.get('recurrence_day');

          let hasError = false;
          if (!type) {
            form.querySelector('[data-for="type"]').textContent = 'Select a type';
            hasError = true;
          }
          if (!amount || amount <= 0) {
            form.querySelector('[data-for="amount"]').textContent = 'Amount must be greater than 0';
            form.querySelector('[name="amount"]').classList.add('error');
            hasError = true;
          }
          if (!category) {
            form.querySelector('[data-for="category"]').textContent = 'Select a category';
            form.querySelector('[name="category"]').classList.add('error');
            hasError = true;
          }
          if (!dates) {
            form.querySelector('[data-for="dates"]').textContent = 'Date is required';
            form.querySelector('[name="dates"]').classList.add('error');
            hasError = true;
          }
          if (hasError) return;

          const payload = {
            type,
            amount,
            category,
            dates,
            description: fd.get('description') || null,
            payment_method: fd.get('payment_method') || null,
            is_recurring,
            recurrence_day: is_recurring && recurrence_day_raw ? parseInt(recurrence_day_raw, 10) : null,
            currency: 'INR'
          };

          saveBtn.disabled = true;
          saveBtn.classList.add('loading');

          try {
            if (isEdit) {
              await API.put(`/transactions/update/${tx.id}`, payload);
              UI.toast('success', 'Transaction updated');
            } else {
              await API.post('/transactions/create', payload);
              UI.toast('success', 'Transaction created');
            }
            close();
            loadTransactions(currentFilters());
          } catch (e) {
            UI.toast('error', e.message);
            saveBtn.disabled = false;
            saveBtn.classList.remove('loading');
          }
        });
      }
    });
  }

  /* ================= SETTINGS ================= */
  async function loadSettings() {
    try {
      const me = await API.get('/users/me');
      const uEl = document.getElementById('acc-username');
      const iEl = document.getElementById('acc-userid');
      const cEl = document.getElementById('acc-created');
      if (uEl) uEl.textContent = me.username || '—';
      if (iEl) iEl.textContent = me.user_id || '—';
      if (cEl) cEl.textContent = me.created_at ? UI.formatDate(me.created_at) : '—';
    } catch {}
  }

  /* ================= EXPORTS ================= */
  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  /* ================= INIT ================= */
  document.addEventListener('DOMContentLoaded', () => {
    API.requireAuth();

    // Router
    document.querySelectorAll('.nav-item').forEach(a => {
      a.addEventListener('click', e => {
        const href = a.getAttribute('href') || '';
        if (href.startsWith('#') || href.includes('#')) {
          e.preventDefault();
          const hash = href.split('#')[1] || 'overview';
          location.hash = hash;
          showSection(hash);
        }
      });
    });
    window.addEventListener('hashchange', handleHash);
    handleHash();

    // Add transaction
    document.getElementById('btn-add-tx')?.addEventListener('click', () => openTransactionModal(null));

    // Filters
    document.getElementById('btn-apply-filter')?.addEventListener('click', () => loadTransactions(currentFilters()));
    document.getElementById('btn-reset-filter')?.addEventListener('click', () => {
      document.getElementById('f-type').value = '';
      document.getElementById('f-category').value = '';
      document.getElementById('f-start').value = '';
      document.getElementById('f-end').value = '';
      document.getElementById('f-search').value = '';
      loadTransactions();
    });

    // Exports
    document.getElementById('btn-export-csv')?.addEventListener('click', async () => {
      try {
        const blob = await API.download('/transactions/export-csv');
        downloadBlob(new Blob([blob], { type: 'text/csv' }), 'transactions.csv');
        UI.toast('success', 'CSV downloaded');
      } catch (e) { UI.toast('error', e.message); }
    });
    document.getElementById('btn-export-pdf')?.addEventListener('click', async () => {
      try {
        const blob = await API.download('/transactions/export-pdf');
        downloadBlob(new Blob([blob], { type: 'application/pdf' }), 'transactions.pdf');
        UI.toast('success', 'PDF downloaded');
      } catch (e) { UI.toast('error', e.message); }
    });

    // Settings
    document.getElementById('btn-theme-toggle')?.addEventListener('click', () => window.FinLedgerTheme?.toggle());
    document.getElementById('btn-logout-settings')?.addEventListener('click', async () => {
      try { await API.post('/users/logout'); } catch {}
      API.logout();
    });
    document.getElementById('btn-change-pw')?.addEventListener('click', async () => {
      const oldPw = document.getElementById('pw-old').value;
      const newPw = document.getElementById('pw-new').value;
      if (!oldPw || !newPw) { UI.toast('error', 'Fill both fields'); return; }
      if (newPw.length < 6) { UI.toast('error', 'Password must be ≥ 6 characters'); return; }
      try {
        const params = new URLSearchParams({ old_password: oldPw, new_password: newPw });
        await API.put(`/users/change-password?${params}`);
        UI.toast('success', 'Password changed');
        document.getElementById('pw-old').value = '';
        document.getElementById('pw-new').value = '';
      } catch (e) { UI.toast('error', e.message); }
    });
  });
})();