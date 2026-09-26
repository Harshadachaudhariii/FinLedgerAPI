/* ===================================================================
   FinLedger — analytics.js
   =================================================================== */
(function () {
  function filters() {
    const p = new URLSearchParams();
    const s = document.getElementById('a-start')?.value;
    const e = document.getElementById('a-end')?.value;
    if (s) p.append('start_date', s);
    if (e) p.append('end_date', e);
    return p.toString();
  }

  async function load() {
    const grid = document.getElementById('analytics-grid');
    grid.innerHTML = UI.skeletonBlocks(3);

    const qs = filters();
    const suffix = qs ? `?${qs}` : '';
    const month = document.getElementById('a-month')?.value || UI.currentMonth();

    let avg, mom, high;
    try {
      const results = await Promise.allSettled([
        API.get(`/api/analytics/average-daily-spend${suffix}`),
        API.get(`/api/analytics/month-over-month?target_month=${month}`),
        API.get(`/api/analytics/highest-spending-day${suffix}`)
      ]);
      avg  = results[0].status === 'fulfilled' ? results[0].value : null;
      mom  = results[1].status === 'fulfilled' ? results[1].value : null;
      high = results[2].status === 'fulfilled' ? results[2].value : null;
    } catch (e) {
      grid.innerHTML = `<div class="card no-hover">Failed to load analytics: ${UI.escapeHtml(e.message)}</div>`;
      return;
    }

    const cards = [];

    // Average daily spend
    if (avg) {
      cards.push(`
        <div class="card no-hover" style="animation:fadeInUp .35s ease both;">
          <div class="kpi-label">Average Daily Spend</div>
          <div class="kpi-value primary" style="margin:6px 0;">${UI.formatMoney(avg.average_daily_spend)}</div>
          <div class="kpi-sub">
            ${UI.formatMoney(avg.total_expenses)} across ${avg.days_in_periods} day(s)
          </div>
          <div class="kpi-sub" style="margin-top:6px;">
            ${UI.formatDate(avg.period.start_date)} → ${UI.formatDate(avg.period.end_date)}
          </div>
        </div>
      `);
    } else {
      cards.push(`
        <div class="card no-hover">
          <div class="kpi-label">Average Daily Spend</div>
          <div class="empty" style="padding:24px 0;">${UI.icon('document', 42)}<p style="margin-top:8px;">No data for this period.</p></div>
        </div>
      `);
    }

    // Month-over-month
    if (mom) {
      const growth = mom.growth_percentage;
      const trend = mom.trend || 'stable';
      const chipCls = trend === 'increased' ? 'down' : trend === 'decreased' ? 'up' : 'flat';
      const chipIcon = trend === 'increased' ? UI.icon('arrowUp', 12) : trend === 'decreased' ? UI.icon('arrowDown', 12) : '→';
      const growthText = growth === null || growth === undefined
        ? 'No comparison'
        : `${growth > 0 ? '+' : ''}${growth.toFixed(1)}%`;

      cards.push(`
        <div class="card no-hover" style="animation:fadeInUp .35s ease .05s both;">
          <div class="kpi-label">Month-over-Month</div>
          <div class="flex-between" style="margin:6px 0;">
            <div class="kpi-value primary">${growthText}</div>
            <span class="chip ${chipCls}">${chipIcon} ${UI.escapeHtml(trend)}</span>
          </div>
          <div class="kpi-sub">
            ${UI.formatMonth(mom.previous_month)}: ${UI.formatMoney(mom.previous_month_spending)}
          </div>
          <div class="kpi-sub">
            ${UI.formatMonth(mom.current_month)}: ${UI.formatMoney(mom.current_month_spending)}
          </div>
        </div>
      `);
    } else {
      cards.push(`
        <div class="card no-hover">
          <div class="kpi-label">Month-over-Month</div>
            <div class="empty" style="padding:24px 0;">${UI.icon('document', 42)}<p style="margin-top:8px;">No comparison data.</p></div>
        </div>
      `);
    }

    // Highest spending day
    if (high) {
      cards.push(`
        <div class="card no-hover" style="animation:fadeInUp .35s ease .1s both;">
          <div class="kpi-label">Highest Spending Day</div>
          <div class="kpi-value expense" style="margin:6px 0;">${UI.formatMoney(high.amount_spent)}</div>
          <div class="kpi-sub">
            📅 ${UI.formatDate(high.highest_spending_date)}
          </div>
          <div class="kpi-sub" style="margin-top:6px;">
            ${high.transaction_count_on_that_day} transaction(s) that day
          </div>
        </div>
      `);
    } else {
      cards.push(`
        <div class="card no-hover">
          <div class="kpi-label">Highest Spending Day</div>
            <div class="empty" style="padding:24px 0;">${UI.icon('document', 42)}<p style="margin-top:8px;">No expenses in this period.</p></div>
        </div>
      `);
    }

    grid.innerHTML = cards.join('');
  }

  document.addEventListener('DOMContentLoaded', () => {
    API.requireAuth();
    const monthInput = document.getElementById('a-month');
    if (monthInput) monthInput.value = UI.currentMonth();
    document.getElementById('a-apply')?.addEventListener('click', load);
    document.getElementById('a-reset')?.addEventListener('click', () => {
      document.getElementById('a-start').value = '';
      document.getElementById('a-end').value = '';
      if (monthInput) monthInput.value = UI.currentMonth();
      load();
    });
    load();
  });
})();