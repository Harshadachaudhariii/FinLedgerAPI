/* ===================================================================
   FinLedger — budgets.js
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
    "Other"
  ];

    // Map category → Icons key. Anything not listed falls back to 'tag'.
  const CAT_ICON_MAP = {
    "Rent": "rent",
    "Mortgage": "home",
    "Utilities": "settings",           // gear as stand-in
    "Internet & Phone": "settings",
    "Home Maintenance": "settings",
    "Insurance": "wallet",
    "Food": "shopping",
    "Groceries": "shopping",
    "Dining Out": "shopping",
    "Coffee Shops": "shopping",
    "Transport": "creditCard",
    "Fuel": "creditCard",
    "Car Maintenance": "settings",
    "Taxi & Ride Share": "creditCard",
    "Public Transit": "creditCard",
    "Shopping": "shopping",
    "Clothing": "shopping",
    "Personal Care": "shopping",
    "Electronics": "shopping",
    "Household Supplies": "shopping",
    "Health": "wallet",
    "Pharmacy": "wallet",
    "Gym & Fitness": "wallet",
    "Dental & Vision": "wallet",
    "Entertainment": "analytics",
    "Subscriptions": "analytics",
    "Travel": "creditCard",
    "Hobbies": "tag",
    "Gaming": "tag",
    "Savings": "banknotes",
    "Investments": "analytics",
    "Debt Repayment": "creditCard",
    "Credit Card Payment": "creditCard",
    "Taxes": "documentText",
    "Charity": "wallet",
    "Education": "documentText",
    "Childcare": "wallet",
    "Pets": "wallet",
    "Donations": "wallet",
    "Gift": "wallet",
    "Other": "tag"
  };

  function categoryIcon(cat) {
    const key = CAT_ICON_MAP[cat] || 'tag';
    return UI.icon(key, 20);
  }

  function currentMonth() { return UI.currentMonth(); }

  async function loadBudgets() {
    const month = document.getElementById('b-month').value || currentMonth();
    const grid = document.getElementById('budget-grid');
    grid.innerHTML = UI.skeletonCards(6);

    try {
      const res = await API.get(`/api/budgets/status?month=${month}`);
      const items = res.budgets_status || [];

      if (!items.length) {
          grid.innerHTML = `
          <div class="card no-hover" style="grid-column:1/-1;">
            <div class="empty">
              ${UI.icon('folder', 56)}
              <h3>No budgets for ${UI.formatMonth(month)}</h3>
              <p>Add your first budget to start tracking.</p>
            </div>
          </div>`;
        return;
      }

        grid.innerHTML = items.map((b, i) => {
        const pct = Math.min(100, b.percentage_used);
        return `
          <div class="budget-card" style="animation:fadeInUp .35s ease ${i * 50}ms both;">
            <div class="budget-header">
              <div class="budget-cat">
                <div class="cat-icon">${categoryIcon(b.category)}</div>
                <span>${UI.escapeHtml(b.category)}</span>
              </div>
              <div class="budget-actions">
                <button class="btn-icon" data-edit="${b.budget_id}" title="Edit">${UI.icon('edit', 18)}</button>
                <button class="btn-icon danger" data-del="${b.budget_id}" title="Delete">${UI.icon('trash', 18)}</button>
              </div>
            </div>

            <div class="budget-amounts">
              <span class="budget-spent">${UI.formatMoney(b.spent_amount)}</span>
              <span class="budget-total">of ${UI.formatMoney(b.budget_amount)}</span>
            </div>

            <div class="progress-track">
              <div class="progress-fill ${b.status}" data-width="${pct}"></div>
            </div>

            <div class="budget-meta">
              <span>Remaining: <strong>${UI.formatMoney(b.remaining_amount)}</strong></span>
              <span class="pct ${b.status}">${b.percentage_used.toFixed(1)}%</span>
            </div>
          </div>
        `;
      }).join('');

      // Animate progress
      requestAnimationFrame(() => {
        grid.querySelectorAll('.progress-fill').forEach(el => {
          const w = el.dataset.width;
          requestAnimationFrame(() => { el.style.width = `${w}%`; });
        });
      });

      // Edit
      grid.querySelectorAll('[data-edit]').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.dataset.edit;
          const b = items.find(x => x.budget_id === id);
          if (b) openBudgetModal({
            id: b.budget_id,
            category: b.category,
            amount: b.budget_amount,
            month: b.month
          });
        });
      });

      // Delete
      grid.querySelectorAll('[data-del]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.del;
          const ok = await UI.confirmDialog({
            title: 'Delete budget?',
            message: 'This budget will be removed.',
            confirmText: 'Delete'
          });
          if (!ok) return;
          try {
            await API.del(`/api/budgets/delete/${id}`);
            UI.toast('success', 'Budget deleted');
            loadBudgets();
          } catch (e) { UI.toast('error', e.message); }
        });
      });
    } catch (e) {
      grid.innerHTML = `<div class="card no-hover">Failed to load: ${UI.escapeHtml(e.message)}</div>`;
    }
  }

  function openBudgetModal(existing = null) {
    const isEdit = !!existing;
    const body = `
      <form id="b-form" novalidate>
        <div class="field">
          <label>Category <span class="req">*</span></label>
          <select class="select" name="category">
            <option value="">Select a category</option>
            ${CATEGORIES.map(c => `<option value="${c}" ${existing?.category === c ? 'selected' : ''}>${c}</option>`).join('')}
          </select>
          <div class="field-error" data-for="category"></div>
        </div>

        <div class="field">
          <label>Budget amount (₹) <span class="req">*</span></label>
          <input type="number" step="0.01" min="0" class="input" name="amount"
                 value="${existing?.amount ?? ''}" placeholder="0.00" />
          <div class="field-error" data-for="amount"></div>
        </div>

        <div class="field">
          <label>Month <span class="req">*</span></label>
          <input type="month" class="input" name="month" value="${existing?.month || currentMonth()}" />
          <div class="field-error" data-for="month"></div>
        </div>
      </form>
    `;

    const footer = `
      <button class="btn btn-ghost" data-cancel>Cancel</button>
      <button class="btn btn-primary" id="b-save">
        <span class="spinner"></span>
        <span class="btn-label">${isEdit ? 'Update' : 'Create'}</span>
      </button>
    `;

    UI.openModal({
      title: isEdit ? 'Edit Budget' : 'Add Budget',
      bodyHTML: body,
      footerHTML: footer,
      onMount(root, close) {
        const form = root.querySelector('#b-form');
        root.querySelector('[data-cancel]').addEventListener('click', close);

        root.querySelector('#b-save').addEventListener('click', async () => {
          form.querySelectorAll('.field-error').forEach(e => e.textContent = '');

          const fd = new FormData(form);
          const category = fd.get('category');
          const amount = parseFloat(fd.get('amount'));
          const month = fd.get('month');

          let hasError = false;
          if (!category) { form.querySelector('[data-for="category"]').textContent = 'Required'; hasError = true; }
          if (!amount || amount <= 0) { form.querySelector('[data-for="amount"]').textContent = 'Amount must be > 0'; hasError = true; }
          if (!month) { form.querySelector('[data-for="month"]').textContent = 'Required'; hasError = true; }
          if (hasError) return;

          const payload = { category, amount, month, period: 'monthly' };
          const saveBtn = root.querySelector('#b-save');
          saveBtn.disabled = true;
          saveBtn.classList.add('loading');

          try {
            if (isEdit) await API.put(`/api/budgets/update/${existing.id}`, payload);
            else       await API.post('/api/budgets/create', payload);
            UI.toast('success', isEdit ? 'Budget updated' : 'Budget created');
            close();
            loadBudgets();
          } catch (e) {
            UI.toast('error', e.message);
            saveBtn.disabled = false;
            saveBtn.classList.remove('loading');
          }
        });
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    API.requireAuth();
    const monthInput = document.getElementById('b-month');
    if (monthInput) monthInput.value = currentMonth();
    monthInput?.addEventListener('change', loadBudgets);
    document.getElementById('btn-add-budget')?.addEventListener('click', () => openBudgetModal(null));
    loadBudgets();
  });
})();