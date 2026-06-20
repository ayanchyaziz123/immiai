(() => {
  const messagesEl  = document.getElementById('messages');
  const inputEl     = document.getElementById('question-input');
  const sendBtn     = document.getElementById('send-btn');
  const visaChips   = document.querySelectorAll('#visa-chips .chip');
  const langSelect  = document.getElementById('language-select');
  const docTypeEl   = document.getElementById('doc-type-select');
  const docTextEl   = document.getElementById('doc-text');
  const charCountEl = document.getElementById('doc-char-count');

  const uploadZone   = document.getElementById('upload-zone');
  const fileInput    = document.getElementById('file-input');
  const fileBadge    = document.getElementById('file-badge');
  const fileNameEl   = document.getElementById('file-name');
  const removeFileEl = document.getElementById('remove-file');
  const uploadError  = document.getElementById('upload-error');

  const historySection = document.getElementById('history-section');
  const historyList    = document.getElementById('history-list');
  const newChatBtn     = document.getElementById('new-chat-btn');
  const guestNudge     = document.getElementById('guest-nudge');

  let conversationId  = null;
  let isLoading       = false;
  let isAuthenticated = false;

  // ── Visa chips ──────────────────────────────────────────────────
  visaChips.forEach(chip => {
    chip.addEventListener('click', () => {
      visaChips.forEach(c => c.classList.remove('chip-active'));
      chip.classList.add('chip-active');
    });
  });
  function getVisaType() {
    return document.querySelector('#visa-chips .chip-active')?.dataset.value ?? 'Any';
  }

  // ── Doc textarea ────────────────────────────────────────────────
  docTextEl.addEventListener('input', () => {
    charCountEl.textContent = docTextEl.value.length;
    if (!docTextEl.value) clearFile();
  });

  // ── Auto-resize question input ──────────────────────────────────
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
  });

  // ── Quick question buttons ──────────────────────────────────────
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => send(btn.dataset.question));
  });
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(inputEl.value); }
  });
  sendBtn.addEventListener('click', () => send(inputEl.value));

  // ── File upload ─────────────────────────────────────────────────
  uploadZone.addEventListener('click', () => fileInput.click());
  uploadZone.addEventListener('dragover',  e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault(); uploadZone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
    fileInput.value = '';
  });
  removeFileEl.addEventListener('click', clearFile);

  async function handleFile(file) {
    setUploadError(''); setUploadLoading(true);
    const form = new FormData(); form.append('file', file);
    try {
      const res  = await fetch('/api/v1/upload/', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { setUploadError(data.detail || 'Upload failed.'); return; }
      docTextEl.value = data.text; charCountEl.textContent = data.text.length;
      fileNameEl.textContent = data.filename;
      fileBadge.classList.remove('hidden'); uploadZone.classList.add('hidden');
      if (data.truncated) setUploadError(`Truncated to 5,000 chars (file had ${data.chars.toLocaleString()}).`);
    } catch (err) { setUploadError(`Upload error: ${err.message}`); }
    finally { setUploadLoading(false); }
  }

  function clearFile() {
    docTextEl.value = ''; charCountEl.textContent = '0';
    fileBadge.classList.add('hidden'); uploadZone.classList.remove('hidden');
    fileNameEl.textContent = ''; setUploadError('');
  }
  function setUploadLoading(on) {
    uploadZone.style.pointerEvents = on ? 'none' : '';
    uploadZone.querySelector('p').textContent = on ? 'Extracting text…' : 'Click or drop a file';
  }
  function setUploadError(msg) { uploadError.textContent = msg; uploadError.classList.toggle('hidden', !msg); }

  // ── Auth events ─────────────────────────────────────────────────
  document.addEventListener('auth:ready', e => {
    isAuthenticated = !!e.detail;
    if (isAuthenticated) {
      historySection.classList.remove('hidden');
      guestNudge.classList.add('hidden');
      loadHistory();
    } else {
      historySection.classList.add('hidden');
      guestNudge.classList.remove('hidden');
    }
  });

  document.addEventListener('auth:login', () => {
    isAuthenticated = true;
    historySection.classList.remove('hidden');
    guestNudge.classList.add('hidden');
    loadHistory();
  });

  document.addEventListener('auth:signout', () => {
    isAuthenticated = false;
    historySection.classList.add('hidden');
    guestNudge.classList.remove('hidden');
    historyList.innerHTML = '<p class="history-empty">No conversations yet.</p>';
  });

  // ── Conversation history ────────────────────────────────────────
  async function loadHistory() {
    try {
      const res = await fetch('/api/v1/chat/conversations');
      if (!res.ok) return;
      renderHistory(await res.json());
    } catch {}
  }

  function renderHistory(convos) {
    historyList.innerHTML = '';
    if (!convos.length) {
      historyList.innerHTML = '<p class="history-empty">No conversations yet.</p>';
      return;
    }
    convos.forEach(c => historyList.appendChild(makeHistoryBtn(c.id, c.title || 'Untitled')));
  }

  function makeHistoryBtn(id, title) {
    const btn = document.createElement('button');
    btn.className   = 'history-item' + (id === conversationId ? ' active' : '');
    btn.textContent = title;
    btn.title       = title;
    btn.dataset.convId = id;
    btn.addEventListener('click', () => loadConversation(id, btn));
    return btn;
  }

  // Prepend a newly created conversation to the sidebar (no round-trip)
  function prependHistory(id, title) {
    if (!isAuthenticated) return;
    historyList.querySelector('.history-empty')?.remove();
    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
    const btn = makeHistoryBtn(id, title);
    btn.classList.add('active');
    historyList.prepend(btn);
  }

  // Mark a conversation as active in the sidebar (no fetch)
  function setActiveHistory(id) {
    document.querySelectorAll('.history-item').forEach(el => {
      el.classList.toggle('active', el.dataset.convId === id);
    });
  }

  async function loadConversation(id, btn) {
    if (isLoading) return;
    try {
      const res = await fetch(`/api/v1/chat/conversations/${id}`);
      if (!res.ok) return;
      const convo = await res.json();

      document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
      btn?.classList.add('active');

      messagesEl.innerHTML = '';
      document.getElementById('empty-state')?.remove();
      conversationId = id;
      convo.messages.forEach(msg => addMessage(msg.role, msg.content));
    } catch {}
  }

  newChatBtn?.addEventListener('click', () => {
    conversationId = null;
    messagesEl.innerHTML = '';
    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
    const empty = document.createElement('div');
    empty.className = 'empty-state'; empty.id = 'empty-state';
    empty.innerHTML = `
      <div class="empty-hero">🛡️</div>
      <h2>Immigration AI Assistant</h2>
      <p>Ask me anything about US visas, green cards, asylum, citizenship, and more.</p>`;
    messagesEl.appendChild(empty);
    inputEl.focus();
  });

  // ── Message rendering ───────────────────────────────────────────
  function addMessage(role, content, isTyping = false) {
    document.getElementById('empty-state')?.remove();

    const wrap   = document.createElement('div');
    wrap.className = `message ${role}`;
    if (isTyping) wrap.id = 'typing-msg';

    const avatar = document.createElement('div');
    avatar.className    = 'avatar';
    avatar.textContent  = role === 'user' ? 'You' : '✦';

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
      tag.className   = 'model-tag';
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
    inputEl.value = ''; inputEl.style.height = 'auto';
    sendBtn.disabled = true;

    const wasNew = !conversationId;  // track before the call

    addMessage('user', question);
    addMessage('assistant', '', true);

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

      // Update sidebar without a network round-trip:
      // new conversation → prepend; existing → just highlight it
      if (wasNew) {
        prependHistory(conversationId, question.slice(0, 60));
      } else {
        setActiveHistory(conversationId);
      }
    } catch (err) {
      setTypingContent(`Sorry, something went wrong: ${err.message}`, null);
    } finally {
      isLoading = false; sendBtn.disabled = false; inputEl.focus();
    }
  }
})();
