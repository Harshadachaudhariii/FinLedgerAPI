/* ===================================================================
   FinLedger — summary.js
   =================================================================== */
(function () {
  let trendChart = null;

  function filters() {
    const p = new URLSearchParams();
    const s = document.getElementById('s-start')?.value;
    const e = document.getElementById('s-end')?.value;
    if (s) p.append('start_date', s);
    if (e) p.append('end_date', e);
    return p.toString();
  }

  function renderTrendChart(months, currency) {
    const ctx = document.getElementById('s-trend-chart');
    if (!ctx) return;
    if (trendChart) trendChart.destroy();

    const labels = months.map(m => UI.formatMonth(m.month));
    const income = months.map(m => m.income);
    const expense = months.map(m => m.expense);

    const incomeGrad = ctx.getContext('2d').createLinearGradient(0, 0, 0, 260);
    incomeGrad.addColorStop(0, 'rgba(23,184,114,.35)');
    incomeGrad.addColorStop(1, 'rgba(23,184,114,0)');
    const expenseGrad = ctx.getContext('2d').createLinearGradient(0, 0, 0, 260);
    expenseGrad.addColorStop(0, 'rgba(240,70,110,.30)');
    expenseGrad.addColorStop(1, 'rgba(240,70,110,0)');

    const sparse = labels.length < 3;

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Income', data: income, borderColor: '#17b872', backgroundColor: incomeGrad,
            fill: true, tension: sparse ? 0 : .4, pointRadius: sparse ? 5 : 0, pointBackgroundColor: '#17b872', pointHoverRadius: 6, borderWidth: 2.5
          },
          {
            label: 'Expense', data: expense, borderColor: '#f0466e', backgroundColor: expenseGrad,
            fill: true, tension: sparse ? 0 : .4, pointRadius: sparse ? 5 : 0, pointBackgroundColor: '#f0466e', pointHoverRadius: 6, borderWidth: 2.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: !!labels.length, position: 'top', align: 'end', labels: { boxWidth: 10, usePointStyle: true, pointStyle: 'circle' } },
          tooltip: { callbacks: { label: c => `${c.dataset.label}: ${UI.formatMoney(c.parsed.y, currency)}` } }
        },
        scales: {
          x: { grid: { display: false }, offset: sparse },
          y: { grid: { color: 'rgba(128,128,150,.12)' }, ticks: { callback: v => UI.formatMoney(v, currency) } }
        }
      }
    });
  }

  function renderRadial(income, expense, currency) {
    const el = document.getElementById('s-radial');
    if (!el) return;
    const total = income + expense;
    const pct = total > 0 ? Math.round((income / total) * 100) : 50;

    el.innerHTML = `
      <div class="radial-ratio" style="--pct:${pct}">
        <div class="radial-ratio-inner">
          <div class="rr-value">${pct}%</div>
          <div class="rr-label">Income share</div>
        </div>
      </div>
      <div class="radial-legend">
        <span class="rl-item"><span class="dot" style="background:var(--income)"></span>Income ${UI.formatMoney(income, currency)}</span>
        <span class="rl-item"><span class="dot" style="background:var(--expense)"></span>Expense ${UI.formatMoney(expense, currency)}</span>
      </div>
    `;
  }

  async function load() {
    const qs = filters();
    const suffix = qs ? `?${qs}` : '';

    const kpi = document.getElementById('s-kpis');
    const monthlyBody = document.getElementById('s-monthly');
    const catBody = document.getElementById('s-cat');
    const radialEl = document.getElementById('s-radial');

    kpi.innerHTML = UI.skeletonKPIs(3);
    monthlyBody.innerHTML = `<tr><td colspan="5"><div class="skeleton skeleton-line" style="margin:12px 0;"></div></td></tr>`;
    catBody.innerHTML = `<tr><td colspan="3"><div class="skeleton skeleton-line" style="margin:12px 0;"></div></td></tr>`;
    if (radialEl) radialEl.innerHTML = `<div class="skeleton skeleton-circle" style="width:148px;height:148px;"></div>`;

    try {
      const [overview, monthly, byCat] = await Promise.all([
        API.get(`/transactions/summary/overview${suffix}`),
        API.get(`/transactions/summary/monthly${suffix}`),
        API.get(`/transactions/summary/by-category${suffix}`)
      ]);

      const currency = overview.currency || 'INR';

      kpi.innerHTML = `
        <div class="stat-card income">
          <div class="stat-top">
            <div class="stat-avatar soft">${UI.icon('arrowUp', 20)}</div>
          </div>
          <div class="stat-body">
            <div class="stat-value">${UI.formatMoney(overview.total_income, currency)}</div>
            <div class="stat-label">Income · ${overview.transaction_count} transactions</div>
          </div>
        </div>
        <div class="stat-card expense">
          <div class="stat-top">
            <div class="stat-avatar soft">${UI.icon('arrowDown', 20)}</div>
          </div>
          <div class="stat-body">
            <div class="stat-value">${UI.formatMoney(overview.total_expense, currency)}</div>
            <div class="stat-label">Expense · this period</div>
          </div>
        </div>
        <div class="stat-card primary">
          <div class="stat-top">
            <div class="stat-avatar">${UI.icon('rupee', 20)}</div>
          </div>
          <div class="stat-body">
            <div class="stat-value">${UI.formatMoney(overview.net_balance, currency)}</div>
            <div class="stat-label">Net balance</div>
          </div>
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
      renderTrendChart(months, currency);
      renderRadial(overview.total_income || 0, overview.total_expense || 0, currency);

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