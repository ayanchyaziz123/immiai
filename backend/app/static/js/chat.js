(() => {
  const messagesEl  = document.getElementById('messages');
  const emptyState  = document.getElementById('empty-state');
  const inputEl     = document.getElementById('question-input');
  const sendBtn     = document.getElementById('send-btn');
  const visaChips   = document.querySelectorAll('#visa-chips .chip');
  const langSelect  = document.getElementById('language-select');
  const docTypeEl   = document.getElementById('doc-type-select');
  const docTextEl   = document.getElementById('doc-text');
  const charCountEl = document.getElementById('doc-char-count');

  // File upload elements
  const fileInput    = document.getElementById('file-input');
  const uploadBtn    = document.getElementById('upload-btn');
  const fileBadge    = document.getElementById('file-badge');
  const fileNameEl   = document.getElementById('file-name');
  const removeFileEl = document.getElementById('remove-file');
  const uploadError  = document.getElementById('upload-error');

  let conversationId = null;
  let isLoading = false;

  // ── Chip selection ──────────────────────────────────────────────
  visaChips.forEach(chip => {
    chip.addEventListener('click', () => {
      visaChips.forEach(c => c.classList.remove('chip-active'));
      chip.classList.add('chip-active');
    });
  });

  function getVisaType() {
    const active = document.querySelector('#visa-chips .chip-active');
    return active ? active.dataset.value : 'Any';
  }

  // ── Doc text char counter ───────────────────────────────────────
  docTextEl.addEventListener('input', () => {
    charCountEl.textContent = docTextEl.value.length;
    // Clear file badge if user manually edits
    if (docTextEl.value === '') clearFile();
  });

  // ── Auto-resize textarea ────────────────────────────────────────
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
  });

  // ── Quick question buttons ──────────────────────────────────────
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => send(btn.dataset.question));
  });

  // ── Send on Enter (Shift+Enter = newline) ───────────────────────
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(inputEl.value); }
  });
  sendBtn.addEventListener('click', () => send(inputEl.value));

  // ── File upload ─────────────────────────────────────────────────
  uploadBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;
    fileInput.value = '';   // reset so same file can be re-selected

    setUploadError('');
    setUploadLoading(true);

    const form = new FormData();
    form.append('file', file);

    try {
      const res  = await fetch('/api/v1/upload/', { method: 'POST', body: form });
      const data = await res.json();

      if (!res.ok) {
        setUploadError(data.detail || 'Upload failed.');
        return;
      }

      docTextEl.value        = data.text;
      charCountEl.textContent = data.text.length;
      fileNameEl.textContent  = data.filename;
      fileBadge.classList.remove('hidden');

      if (data.truncated) {
        setUploadError(`File truncated to 5,000 characters (original: ${data.chars.toLocaleString()} chars).`);
      }
    } catch (err) {
      setUploadError(`Upload error: ${err.message}`);
    } finally {
      setUploadLoading(false);
    }
  });

  removeFileEl.addEventListener('click', clearFile);

  function clearFile() {
    docTextEl.value         = '';
    charCountEl.textContent = '0';
    fileBadge.classList.add('hidden');
    fileNameEl.textContent  = '';
    setUploadError('');
  }

  function setUploadLoading(loading) {
    uploadBtn.disabled    = loading;
    uploadBtn.textContent = loading ? 'Extracting…' : '';
    if (!loading) {
      uploadBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        Upload file`;
    }
  }

  function setUploadError(msg) {
    uploadError.textContent = msg;
    uploadError.classList.toggle('hidden', !msg);
  }

  // ── Render helpers ──────────────────────────────────────────────
  function addMessage(role, content, isTyping = false) {
    emptyState?.remove();

    const wrap = document.createElement('div');
    wrap.className = `message ${role}`;
    wrap.id = isTyping ? 'typing-msg' : '';

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? 'You' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (isTyping) {
      bubble.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
    } else {
      bubble.textContent = content;
    }

    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return wrap;
  }

  function setTypingContent(text, modelVersion) {
    const wrap = document.getElementById('typing-msg');
    if (!wrap) return;
    wrap.removeAttribute('id');
    const bubble = wrap.querySelector('.bubble');
    bubble.textContent = text;

    if (modelVersion) {
      const tag = document.createElement('div');
      tag.className = 'model-tag';
      tag.textContent = modelVersion;
      bubble.appendChild(tag);
    }

    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ── Send ────────────────────────────────────────────────────────
  async function send(text) {
    const question = (text || '').trim();
    if (!question || isLoading) return;

    isLoading = true;
    inputEl.value = '';
    inputEl.style.height = 'auto';
    sendBtn.disabled = true;

    addMessage('user', question);
    addMessage('assistant', '', true);   // typing indicator

    try {
      const res = await fetch('/api/v1/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          conversation_id: conversationId ?? undefined,
          language:        langSelect.value,
          visa_type:       getVisaType(),
          document_type:   docTypeEl.value,
          category:        'General',
          document_text:   docTextEl.value || '',
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'API error');

      conversationId = data.conversation_id;
      setTypingContent(data.answer, data.model_version);
    } catch (err) {
      setTypingContent(`Sorry, something went wrong: ${err.message}`, null);
    } finally {
      isLoading = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }
})();
