(() => {
  const input   = document.getElementById('receipt-input');
  const btn     = document.getElementById('check-btn');
  const errorEl = document.getElementById('receipt-error');
  const REGEX   = /^[A-Z]{3}\d{10}$/i;

  btn.addEventListener('click', () => {
    const val = input.value.trim().toUpperCase();
    if (!REGEX.test(val)) {
      input.classList.add('error');
      errorEl.textContent = 'Receipt number must be 3 letters followed by 10 digits (e.g. EAC1234567890)';
      errorEl.classList.remove('hidden');
      return;
    }
    input.classList.remove('error');
    errorEl.classList.add('hidden');
    window.open(`https://egov.uscis.gov/casestatus/mycasestatus.do?appReceiptNum=${val}`, '_blank');
  });

  input.addEventListener('input', () => {
    input.classList.remove('error');
    errorEl.classList.add('hidden');
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') btn.click();
  });
})();
