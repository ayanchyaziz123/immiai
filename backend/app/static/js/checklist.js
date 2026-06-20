(() => {
  const resultEl  = document.getElementById('checklist-result');
  const loadingEl = document.getElementById('checklist-loading');
  const emptyEl   = document.getElementById('checklist-empty');
  const titleEl   = document.getElementById('checklist-title');
  const summaryEl = document.getElementById('checklist-summary');
  const itemsEl   = document.getElementById('checklist-items');

  document.querySelectorAll('.visa-card').forEach(card => {
    card.addEventListener('click', async () => {
      document.querySelectorAll('.visa-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');

      emptyEl.classList.add('hidden');
      resultEl.classList.add('hidden');
      loadingEl.classList.remove('hidden');

      try {
        const res  = await fetch('/api/v1/checklist/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ visa_type: card.dataset.visa }),
        });
        const data = await res.json();

        titleEl.textContent   = data.visa_type;
        const required = data.items.filter(i => i.required).length;
        summaryEl.textContent = `${required} required · ${data.items.length - required} optional`;

        itemsEl.innerHTML = '';
        data.items.forEach(item => {
          const li = document.createElement('li');
          li.className = 'checklist-item';
          li.innerHTML = `
            <span class="item-badge ${item.required ? 'badge-required' : 'badge-optional'}">
              ${item.required ? 'Required' : 'Optional'}
            </span>
            <div>
              <div class="item-text">${item.item}</div>
              ${item.notes ? `<div class="item-notes">${item.notes}</div>` : ''}
            </div>`;
          itemsEl.appendChild(li);
        });

        loadingEl.classList.add('hidden');
        resultEl.classList.remove('hidden');
      } catch {
        loadingEl.classList.add('hidden');
        emptyEl.classList.remove('hidden');
        emptyEl.querySelector('p').textContent = 'Failed to load checklist. Is the API running?';
      }
    });
  });
})();
