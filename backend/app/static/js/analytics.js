/* ===================================================================
   FinLedger — analytics.js
   =================================================================== */
(function () {
  let trendChart = null;

  function filters() {
    const p = new URLSearchParams();
    const s = document.getElementById('a-start')?.value;
    const e = document.getElementById('a-end')?.value;
    if (s) p.append('start_date', s);
    if (e) p.append('end_date', e);
    return p.toString();
  }

  function renderTrendChart(months) {
    const ctx = document.getElementById('a-trend-chart');
    if (!ctx) return;
    if (trendChart) trendChart.destroy();

    const palette = ['#6d5efc','#22d3ee','#17b872','#f5a524','#f0466e','#8b5cf6','#3b82f6','#e879f9'];
    const labels = months.map(m => UI.formatMonth(m.month));
    const values = months.map(m => m.expense);

    trendChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: labels.map((_, i) => palette[i % palette.length]),
          borderRadius: 10,
          borderSkipped: false,
          maxBarThickness: 46
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: c => `Expense: ${UI.formatMoney(c.parsed.y)}` } }
        },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: 'rgba(128,128,150,.12)' }, ticks: { callback: v => UI.formatMoney(v) } }
        }
      }
    });
  }

  async function load() {
    const grid = document.getElementById('analytics-grid');
    grid.innerHTML = `
      <div class="skeleton skeleton-block" style="min-height:380px;"></div>
      <div class="skeleton skeleton-block"></div>
      <div class="skeleton skeleton-block"></div>
    `;

    const qs = filters();
    const suffix = qs ? `?${qs}` : '';
    const month = document.getElementById('a-month')?.value || UI.currentMonth();

    let avg, mom, high, monthly;
    try {
      const results = await Promise.allSettled([
        API.get(`/api/analytics/average-daily-spend${suffix}`),
        API.get(`/api/analytics/month-over-month?target_month=${month}`),
        API.get(`/api/analytics/highest-spending-day${suffix}`),
        API.get(`/transactions/summary/monthly${suffix}`)
      ]);
      avg     = results[0].status === 'fulfilled' ? results[0].value : null;
      mom     = results[1].status === 'fulfilled' ? results[1].value : null;
      high    = results[2].status === 'fulfilled' ? results[2].value : null;
      monthly = results[3].status === 'fulfilled' ? results[3].value : null;
    } catch (e) {
      grid.innerHTML = `<div class="card no-hover">Failed to load analytics: ${UI.escapeHtml(e.message)}</div>`;
      return;
    }

    renderTrendChart((monthly && monthly.monthly_summary) || []);

    const tiles = [];

    // Average daily spend — primary bento tile
    if (avg) {
      tiles.push(`
        <div class="bento-tile bento-main" style="animation:fadeInUp .35s ease both;">
          <div>
            <div class="bento-eyebrow">${UI.icon('rupee', 16)} Average Daily Spend</div>
            <div class="bento-figure">${UI.formatMoney(avg.average_daily_spend)}</div>
            <div class="bento-sub">
              ${UI.formatMoney(avg.total_expenses)} total across ${avg.days_in_periods} day(s)
            </div>
          </div>
          <div>
            <div class="divider" style="margin:20px 0 14px;"></div>
            <div class="flex-between">
              <span class="text-muted" style="font-size:13px;">Period</span>
              <span style="font-weight:600;font-size:13px;">
                ${UI.formatDate(avg.period.start_date)} → ${UI.formatDate(avg.period.end_date)}
              </span>
            </div>
          </div>
        </div>
      `);
    } else {
      tiles.push(`
        <div class="bento-tile bento-main">
          <div class="empty" style="padding:24px 0;">${UI.icon('document', 48)}<h3>No spending data</h3><p>No data available for this period.</p></div>
        </div>
      `);
    }

    // Month-over-month
    if (mom) {
      const growth = mom.growth_percentage;
      const trend = mom.trend || 'stable';
      const chipCls = trend === 'increased' ? 'down' : trend === 'decreased' ? 'up' : 'flat';
      const chipIcon = trend === 'increased' ? UI.icon('arrowUp', 12) : trend === 'decreased' ? UI.icon('arrowDown', 12) : UI.icon('trendUp', 12);
      const growthText = growth === null || growth === undefined
        ? 'No comparison'
        : `${growth > 0 ? '+' : ''}${growth.toFixed(1)}%`;

      tiles.push(`
        <div class="bento-tile" style="animation:fadeInUp .35s ease .05s both;">
          <div class="bento-eyebrow">${UI.icon('trendUp', 16)} Month-over-Month</div>
          <div class="flex-between" style="margin-top:10px;">
            <div class="bento-figure">${growthText}</div>
            <span class="chip ${chipCls}">${chipIcon} ${UI.escapeHtml(trend)}</span>
          </div>
          <div class="bento-sub" style="margin-top:8px;">
            ${UI.formatMonth(mom.previous_month)}: ${UI.formatMoney(mom.previous_month_spending)}<br>
            ${UI.formatMonth(mom.current_month)}: ${UI.formatMoney(mom.current_month_spending)}
          </div>
        </div>
      `);
    } else {
      tiles.push(`
        <div class="bento-tile">
          <div class="empty" style="padding:16px 0;">${UI.icon('document', 40)}<p style="margin-top:8px;">No comparison data.</p></div>
        </div>
      `);
    }

    // Highest spending day
    if (high) {
      tiles.push(`
        <div class="bento-tile" style="animation:fadeInUp .35s ease .1s both;">
          <div class="bento-eyebrow">${UI.icon('calendar', 16)} Highest Spending Day</div>
          <div class="bento-figure" style="color:var(--expense);">${UI.formatMoney(high.amount_spent)}</div>
          <div class="bento-sub">
            ${UI.formatDate(high.highest_spending_date)} · ${high.transaction_count_on_that_day} transaction(s)
          </div>
        </div>
      `);
    } else {
      tiles.push(`
        <div class="bento-tile">
          <div class="empty" style="padding:16px 0;">${UI.icon('document', 40)}<p style="margin-top:8px;">No expenses in this period.</p></div>
        </div>
      `);
    }

    grid.innerHTML = tiles.join('');
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