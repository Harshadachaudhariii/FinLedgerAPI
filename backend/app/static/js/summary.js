/* ===================================================================
   FinLedger — summary.js
   =================================================================== */
(function () {
  function filters() {
    const p = new URLSearchParams();
    const s = document.getElementById('s-start')?.value;
    const e = document.getElementById('s-end')?.value;
    if (s) p.append('start_date', s);
    if (e) p.append('end_date', e);
    return p.toString();
  }

  async function load() {
    const qs = filters();
    const suffix = qs ? `?${qs}` : '';

    const kpi = document.getElementById('s-kpis');
    const monthlyBody = document.getElementById('s-monthly');
    const catBody = document.getElementById('s-cat');

    kpi.innerHTML = UI.skeletonKPIs(3);
    monthlyBody.innerHTML = `<tr><td colspan="5"><div class="skeleton skeleton-line" style="margin:12px 0;"></div></td></tr>`;
    catBody.innerHTML = `<tr><td colspan="3"><div class="skeleton skeleton-line" style="margin:12px 0;"></div></td></tr>`;

    try {
      const [overview, monthly, byCat] = await Promise.all([
        API.get(`/transactions/summary/overview${suffix}`),
        API.get(`/transactions/summary/monthly${suffix}`),
        API.get(`/transactions/summary/by-category${suffix}`)
      ]);

      const currency = overview.currency || 'INR';

      kpi.innerHTML = `
        <div class="kpi">
          <div class="kpi-label">Income</div>
          <div class="kpi-value income">${UI.formatMoney(overview.total_income, currency)}</div>
          <div class="kpi-sub">${overview.transaction_count} transactions</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Expense</div>
          <div class="kpi-value expense">${UI.formatMoney(overview.total_expense, currency)}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Net Balance</div>
          <div class="kpi-value primary">${UI.formatMoney(overview.net_balance, currency)}</div>
        </div>
      `;

      // Monthly
      const months = monthly.monthly_summary || [];
      if (!months.length) {
        monthlyBody.innerHTML = `<tr><td colspan="5"><div class="empty">${UI.icon('document', 42)}<p style="margin-top:8px;">No data for this period.</p></div></td></tr>`;
      } else {
        monthlyBody.innerHTML = months.map(m => `
          <tr>
            <td data-label="Month">${UI.formatMonth(m.month)}</td>
            <td data-label="Income" class="right text-income">${UI.formatMoney(m.income, currency)}</td>
            <td data-label="Expense" class="right text-expense">${UI.formatMoney(m.expense, currency)}</td>
            <td data-label="Net" class="right" style="font-weight:600;">${UI.formatMoney(m.net_balance, currency)}</td>
            <td data-label="Txns" class="right">${m.transactions_count}</td>
          </tr>
        `).join('');
      }

      // Category
      const cats = byCat.breakdown || [];
      if (!cats.length) {
        catBody.innerHTML = `<tr><td colspan="3"><div class="empty">${UI.icon('document', 42)}<p style="margin-top:8px;">No expenses in this period.</p></div></td></tr>`;
      } else {
        catBody.innerHTML = cats.map(c => `
          <tr>
            <td data-label="Category"><span class="pill primary">${UI.escapeHtml(c.category)}</span></td>
            <td data-label="Amount" class="right">${UI.formatMoney(c.amount, currency)}</td>
            <td data-label="% of Total" class="right">${c.percentage}%</td>
          </tr>
        `).join('');
      }
    } catch (e) {
      kpi.innerHTML = `<div class="card no-hover">Failed to load: ${UI.escapeHtml(e.message)}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    API.requireAuth();
    document.getElementById('s-apply')?.addEventListener('click', load);
    document.getElementById('s-reset')?.addEventListener('click', () => {
      document.getElementById('s-start').value = '';
      document.getElementById('s-end').value = '';
      load();
    });
    load();
  });
})();