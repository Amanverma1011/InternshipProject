/**
 * Sologix Proposal Form — Live Calculation & Dynamic Rows
 */
const ProposalCalc = (function () {
  let debounceTimer = null;

  function fmt(n) {
    if (isNaN(n)) return '—';
    return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function getAddons() {
    const names = [...document.querySelectorAll('#addonsContainer input[name="addon_name"]')];
    const amounts = [...document.querySelectorAll('#addonsContainer input[name="addon_amount"]')];
    const result = [];
    names.forEach((n, i) => {
      const nm = n.value.trim();
      const am = parseFloat(amounts[i]?.value) || 0;
      if (nm) result.push({ name: nm, amount: am });
    });
    return result;
  }

  function getPayments() {
    const milestones = [...document.querySelectorAll('#paymentsContainer input[name="payment_milestone"]')];
    const amounts = [...document.querySelectorAll('#paymentsContainer input[name="payment_amount"]')];
    const result = [];
    milestones.forEach((m, i) => {
      const ms = m.value.trim();
      const am = parseFloat(amounts[i]?.value) || 0;
      if (ms) result.push({ milestone: ms, amount: am });
    });
    return result;
  }

  function recalculate() {
    const cap = parseFloat(document.getElementById('plantCapacity')?.value) || 0;
    const base = parseFloat(document.getElementById('basePrice')?.value) || 0;
    const disc = parseFloat(document.getElementById('discountPercent')?.value) || 0;
    const addons = getAddons();
    const payments = getPayments();

    fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plant_capacity: cap, base_price: base, addons, discount_percent: disc, payments })
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) return;

        // Update display fields
        if (document.getElementById('totalAreaDisplay'))
          document.getElementById('totalAreaDisplay').value = data.total_area ? data.total_area + ' sq.ft' : '';
        if (document.getElementById('inverterDisplay'))
          document.getElementById('inverterDisplay').value = data.inverter_capacity ? data.inverter_capacity + ' kW' : '';

        // Live bar
        document.getElementById('liveArea').textContent = data.total_area + ' sq.ft';
        document.getElementById('liveInverter').textContent = data.inverter_capacity + ' kW';
        document.getElementById('liveSubtotal').textContent = fmt(data.subtotal);
        document.getElementById('liveDiscount').textContent = data.discount_amount > 0 ? '-' + fmt(data.discount_amount) : '—';
        document.getElementById('liveGrandTotal').textContent = fmt(data.grand_total);
        document.getElementById('livePaymentTotal').textContent = fmt(data.payment_total);

        // Summary sidebar
        document.getElementById('sumCapacity').textContent = cap ? cap + ' kW' : '—';
        document.getElementById('sumArea').textContent = data.total_area + ' sq.ft';
        document.getElementById('sumInverter').textContent = data.inverter_capacity + ' kW';
        document.getElementById('sumBase').textContent = fmt(base);
        document.getElementById('sumAddons').textContent = fmt(data.addon_total);
        document.getElementById('sumSubtotal').textContent = fmt(data.subtotal);
        document.getElementById('sumDiscount').textContent = disc > 0 ? '-' + fmt(data.discount_amount) : '—';
        document.getElementById('sumGrandTotal').textContent = fmt(data.grand_total);
        document.getElementById('sumPaymentTotal').textContent = fmt(data.payment_total);

        const diff = Math.abs(data.grand_total - data.payment_total);
        document.getElementById('sumDiff').textContent = diff < 0.01 ? '✓ Match' : fmt(diff);
        document.getElementById('sumDiff').style.color = diff < 0.01 ? 'green' : 'red';

        // Payment match badge
        const matchEl = document.getElementById('paymentMatch');
        const warnEl = document.getElementById('paymentWarning');
        const hasPayments = payments.length > 0;
        if (!hasPayments) {
          matchEl.textContent = 'No payments';
          matchEl.className = 'badge fs-6 bg-secondary';
          warnEl?.classList.add('d-none');
        } else if (data.errors && data.errors.length > 0) {
          matchEl.textContent = '✗ Mismatch';
          matchEl.className = 'badge fs-6 bg-danger';
          warnEl?.classList.remove('d-none');
        } else {
          matchEl.textContent = '✓ Match';
          matchEl.className = 'badge fs-6 bg-success';
          warnEl?.classList.add('d-none');
        }
      })
      .catch(() => {});
  }

  function debouncedRecalc() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(recalculate, 300);
  }

  function addAddonRow(name = '', amount = '') {
    const container = document.getElementById('addonsContainer');
    const row = document.createElement('div');
    row.className = 'row g-2 mb-2 addon-row';
    row.innerHTML = `
      <div class="col-7"><input type="text" name="addon_name" class="form-control" placeholder="Add-on name" value="${name}"></div>
      <div class="col-4"><input type="number" name="addon_amount" class="form-control addon-amount" placeholder="₹ Amount" step="0.01" min="0" value="${amount}"></div>
      <div class="col-1"><button type="button" class="btn btn-outline-danger btn-sm w-100 remove-addon"><i class="bi bi-x"></i></button></div>
    `;
    container.appendChild(row);
    bindRowEvents(row);
    debouncedRecalc();
  }

  function addPaymentRow(milestone = '', amount = '') {
    const container = document.getElementById('paymentsContainer');
    const row = document.createElement('div');
    row.className = 'row g-2 mb-2 payment-row';
    row.innerHTML = `
      <div class="col-7"><input type="text" name="payment_milestone" class="form-control" placeholder="Milestone"></div>
      <div class="col-4"><input type="number" name="payment_amount" class="form-control payment-amount" placeholder="₹ Amount" step="0.01" min="0" value="${amount}"></div>
      <div class="col-1"><button type="button" class="btn btn-outline-danger btn-sm w-100 remove-payment"><i class="bi bi-x"></i></button></div>
    `;
    if (milestone) row.querySelector('input[name="payment_milestone"]').value = milestone;
    container.appendChild(row);
    bindRowEvents(row);
    debouncedRecalc();
  }

  function bindRowEvents(row) {
    row.querySelectorAll('input').forEach(inp => inp.addEventListener('input', debouncedRecalc));
    const removeAddon = row.querySelector('.remove-addon');
    const removePayment = row.querySelector('.remove-payment');
    if (removeAddon) removeAddon.addEventListener('click', () => { row.remove(); debouncedRecalc(); });
    if (removePayment) removePayment.addEventListener('click', () => { row.remove(); debouncedRecalc(); });
  }

  function init() {
    // Bind existing rows
    document.querySelectorAll('.addon-row, .payment-row').forEach(bindRowEvents);

    // Add row buttons
    document.getElementById('addAddonBtn')?.addEventListener('click', () => addAddonRow());
    document.getElementById('addPaymentBtn')?.addEventListener('click', () => addPaymentRow());

    // Live inputs
    ['plantCapacity', 'basePrice', 'discountPercent'].forEach(id => {
      document.getElementById(id)?.addEventListener('input', debouncedRecalc);
    });

    // Initial calc
    recalculate();
  }

  return { init, addAddonRow, addPaymentRow, recalculate };
})();
