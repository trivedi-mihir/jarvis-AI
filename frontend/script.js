/* ==========================================================
   JARVIS Frontend v8 — Agent UI with Voice Orb Interaction
   ========================================================== */
(function () {
  'use strict';

  const BACKEND = 'http://127.0.0.1:8000';
  const $  = (s, p = document) => p.querySelector(s);
  const $$ = (s, p = document) => Array.from(p.querySelectorAll(s));

  /* ==========================================================
     STATE
     ========================================================== */
  const state = {
    apiKey: localStorage.getItem('jarvis_key') || '',
    model:  localStorage.getItem('jarvis_model') || 'openai/gpt-4o-mini',
    ttsEnabled: localStorage.getItem('jarvis_tts') !== 'false',
    orbClickEnabled: localStorage.getItem('jarvis_orb_click') !== 'false',
    pcOnline: false,
    aiOnline: false,
    listening: false,
    speaking: false,
    busy: false,
    tasks: JSON.parse(localStorage.getItem('jarvis_tasks') || '[]'),
    pendingTask: null,
    history: JSON.parse(localStorage.getItem('jarvis_history') || '[]'),
    historyIdx: -1,
    recognition: null,
    micVolume: 0,
    currentVoiceTranscript: '',
  };

  /* ==========================================================
     HELPERS
     ========================================================== */
  function setOrb(name, label, sub) {
    const o = $('#orb');
    if (o) o.className = 'orb ' + (name || 'idle');
    const s = $('#state');
    if (s) s.textContent = label || 'STANDBY';
    const ss = $('#state-sub');
    if (ss && sub) ss.textContent = sub;
  }

  function setChip(id, on) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('online', !!on);
    el.classList.toggle('offline', !on);
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = String(s ?? '');
    return d.innerHTML;
  }

  function md(text) {
    let s = escapeHtml(text);
    s = s.replace(/```(\w*)\n([\s\S]*?)```/g, (_, _l, c) => `<pre>${c.trim()}</pre>`);
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, '$1<em>$2</em>');
    s = s.replace(/\n/g, '<br>');
    return s;
  }

  function toast(msg, type = 'info', dur = 3000) {
    const c = $('#toasts');
    if (!c) return;
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => {
      t.classList.add('out');
      setTimeout(() => t.remove(), 300);
    }, dur);
  }

  /* ==========================================================
     CHAT
     ========================================================== */
  function addMsg(text, sender, isError = false) {
    const chat = $('#chat');
    const row = document.createElement('div');
    row.className = 'msg ' + sender + (isError ? ' error' : '');
    row.innerHTML = `
      <div class="avatar">${sender === 'user' ? 'YOU' : 'JARVIS'}</div>
      <div class="body">${sender === 'bot' ? md(text) : escapeHtml(text)}</div>`;
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
    $('#welcome')?.classList.add('hidden');
    return row;
  }

  function showTyping() {
    const chat = $('#chat');
    const row = document.createElement('div');
    row.className = 'msg bot';
    row.id = 'typing';
    row.innerHTML = `<div class="avatar">JARVIS</div><div class="body">thinking...</div>`;
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
  }

  function updateTyping(text) {
    const r = document.getElementById('typing');
    if (r) {
      r.querySelector('.body').innerHTML = md(text);
      $('#chat').scrollTop = $('#chat').scrollHeight;
    }
  }

  function hideTyping() {
    document.getElementById('typing')?.remove();
  }

  /* ==========================================================
     TASK MONITOR
     ========================================================== */
  function renderTask(task) {
    const mon = $('#task-monitor');
    if (!task) { mon.classList.add('hidden'); return; }
    mon.classList.remove('hidden');
    $('#task-goal').textContent = task.goal;
    const steps = $('#task-steps');
    steps.innerHTML = '';
    (task.steps || []).forEach((s, i) => {
      const cls = s.status || 'pending';
      const el = document.createElement('div');
      el.className = 'tstep ' + cls;
      const icon = { done: '✓', failed: '✕', running: '⚙', pending: '○', waiting_confirmation: '⏳' }[cls] || '•';
      el.innerHTML = `
        <span class="tstep-ic">${icon}</span>
        <span>Step ${i + 1}</span>
        <span class="tstep-tool">${escapeHtml(s.tool || '')}</span>
        <span class="tstep-obs">${escapeHtml((s.observation || '').slice(0, 100))}</span>`;
      steps.appendChild(el);
    });
  }

  function saveTask(task) {
    if (!task) return;
    const idx = state.tasks.findIndex(t => t.id === task.id);
    if (idx >= 0) state.tasks[idx] = task;
    else state.tasks.unshift(task);
    state.tasks = state.tasks.slice(0, 25);
    localStorage.setItem('jarvis_tasks', JSON.stringify(state.tasks));
    renderTaskHistory();
  }

  function renderTaskHistory() {
    const list = $('#task-history');
    if (!list) return;
    list.innerHTML = '';
    if (state.tasks.length === 0) {
      list.innerHTML = '<div class="empty-hist">No tasks yet</div>';
      return;
    }
    state.tasks.forEach(t => {
      const el = document.createElement('div');
      el.className = 'task-item';
      el.innerHTML = `
        <div class="task-item-title">${escapeHtml(t.goal)}</div>
        <div class="task-item-status ${t.status}">${(t.status || '').toUpperCase()}</div>`;
      el.addEventListener('click', () => {
        renderTask(t);
        if (t.status === 'waiting_input') {
          state.pendingTask = t;
          showConfirm(`⚠ Task needs confirmation:\n${t.goal}`);
        }
      });
      list.appendChild(el);
    });
  }

  /* ==========================================================
     VOICE INPUT
     ========================================================== */
  function initVoice() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setChip('chip-mic', false);
      $('#voice-btn').disabled = true;
      return;
    }
    setChip('chip-mic', true);

    const r = new SR();
    r.lang = 'en-US';
    r.interimResults = true;
    r.continuous = false;
    r.maxAlternatives = 1;

    r.onstart = () => {
      state.listening = true;
      state.currentVoiceTranscript = '';
      $('#voice-btn')?.classList.add('recording');
      setOrb('listening', 'LISTENING', 'SPEAK NOW — CLICK ORB TO STOP');
      toast('🎙 Listening...', 'info', 1800);
    };

    r.onresult = (e) => {
      let finalT = '', interimT = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) finalT += res[0].transcript;
        else interimT += res[0].transcript;
      }
      state.currentVoiceTranscript = finalT || interimT;
      const inp = $('#user-input');
      if (inp) inp.value = state.currentVoiceTranscript;
      setOrb('listening', 'HEARING...', state.currentVoiceTranscript.slice(0, 60) || 'LISTENING');
    };

    r.onerror = (e) => {
      state.listening = false;
      $('#voice-btn')?.classList.remove('recording');
      if (e.error === 'not-allowed') {
        setOrb('error', 'MIC BLOCKED', 'ALLOW MICROPHONE IN BROWSER');
        toast('Microphone permission denied', 'error');
      } else if (e.error === 'no-speech') {
        setOrb('idle', 'STANDBY', 'NO SPEECH DETECTED');
      } else {
        setOrb('error', 'VOICE ERROR', 'TRY AGAIN');
      }
      setTimeout(() => setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW'), 2000);
    };

    r.onend = () => {
      state.listening = false;
      $('#voice-btn')?.classList.remove('recording');
      const text = ($('#user-input')?.value || '').trim();
      if (text) {
        setTimeout(() => handleSend(), 200);
      } else {
        setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW');
      }
    };

    state.recognition = r;
  }

  function toggleVoice() {
    const r = state.recognition;
    if (!r) { toast('Voice not supported in this browser', 'error'); return; }
    if (state.speaking) stopSpeaking();
    if (state.listening) { try { r.stop(); } catch (e) {} }
    else {
      try { r.start(); }
      catch (e) {
        toast('Could not start listening', 'error');
      }
    }
  }

  /* ==========================================================
     VOICE OUTPUT
     ========================================================== */
  function speak(text) {
    if (!state.ttsEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const clean = String(text || '').replace(/[*`#_>•]/g, '').slice(0, 500);
      if (!clean.trim()) return;
      const u = new SpeechSynthesisUtterance(clean);
      u.rate = 1; u.pitch = 1;
      u.onstart = () => {
        state.speaking = true;
        setOrb('speaking', 'SPEAKING', 'VOICE OUTPUT ACTIVE');
      };
      u.onend = () => {
        state.speaking = false;
        if (!state.listening) setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW');
      };
      u.onerror = () => { state.speaking = false; };
      window.speechSynthesis.speak(u);
    } catch (e) {}
  }

  function stopSpeaking() {
    try {
      window.speechSynthesis.cancel();
      state.speaking = false;
      if (!state.listening) setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW');
    } catch (e) {}
  }

  /* ==========================================================
     BACKEND
     ========================================================== */
  async function checkBackend() {
    try {
      const r = await fetch(BACKEND + '/status', { method: 'GET' });
      if (!r.ok) throw 0;
      const d = await r.json();
      state.pcOnline = !!d.ok;
      setChip('chip-pc', true);
      $('#sb-dot')?.classList.add('online');
      const st = $('#sb-text');
      if (st) st.textContent = 'AGENT ONLINE';
      return d;
    } catch (e) {
      state.pcOnline = false;
      setChip('chip-pc', false);
      $('#sb-dot')?.classList.remove('online');
      const st = $('#sb-text');
      if (st) st.textContent = 'AGENT OFFLINE';
      return null;
    }
  }

  /* ==========================================================
     SEND / PROCESS
     ========================================================== */
  async function handleSend() {
    if (state.busy) {
      toast('JARVIS is still working on the previous request', 'warn');
      return;
    }
    const input = $('#user-input');
    const text = (input?.value || '').trim();
    if (!text) return;

    // history
    state.history.unshift(text);
    state.history = state.history.slice(0, 50);
    state.historyIdx = -1;
    localStorage.setItem('jarvis_history', JSON.stringify(state.history));

    addMsg(text, 'user');
    if (input) input.value = '';
    showTyping();
    setOrb('thinking', 'THINKING', 'PLANNING TASK');
    state.busy = true;
    $('#send-btn').disabled = true;

    try {
      const r = await fetch(BACKEND + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, api_key: state.apiKey, model: state.model }),
      });

      if (!r.ok) throw new Error('Backend error ' + r.status);
      const data = await r.json();

      if (data.handled && data.task) {
        saveTask(data.task);
        renderTask(data.task);
        hideTyping();
        setOrb('executing', 'EXECUTING', 'RUNNING TOOLS');
        addMsg(data.reply || 'Done', 'bot');
        setOrb('success', 'COMPLETED', 'TASK FINISHED');
        speak(data.reply || 'Done');
        setTimeout(() => {
          if (!state.listening && !state.speaking) {
            setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW');
          }
        }, 2400);

        if (data.task.status === 'waiting_input') {
          state.pendingTask = data.task;
          showConfirm(`⚠ Confirmation needed:\n\n${data.task.goal}\n\n${data.exec?.description || ''}`);
        }
        return;
      }

      // Fallback — AI chat
      if (!state.apiKey) {
        hideTyping();
        addMsg('Add your OpenRouter API key in ⚙ Settings so I can plan tasks and answer general questions.', 'bot', true);
        setOrb('error', 'SETUP', 'ADD API KEY');
        setTimeout(() => setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW'), 2200);
        return;
      }

      updateTyping('...');
      const aiReply = await askAI(text);
      hideTyping();
      addMsg(aiReply, 'bot');
      setOrb('speaking', 'SPEAKING', 'VOICE OUTPUT ACTIVE');
      speak(aiReply);
      setTimeout(() => {
        if (!state.listening && !state.speaking) {
          setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW');
        }
      }, 2600);

    } catch (err) {
      hideTyping();
      addMsg('⚠ ' + (err.message || String(err)), 'bot', true);
      setOrb('error', 'ERROR', 'CHECK CONNECTION');
      setTimeout(() => setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW'), 2200);
    } finally {
      state.busy = false;
      $('#send-btn').disabled = false;
      $('#user-input')?.focus();
    }
  }

  async function askAI(message) {
    const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + state.apiKey,
        'HTTP-Referer': location.origin,
        'X-Title': 'JARVIS Agent',
      },
      body: JSON.stringify({
        model: state.model || 'openai/gpt-4o-mini',
        messages: [
          { role: 'system', content: 'You are JARVIS, a concise, sharp Windows AI assistant. Answer directly and clearly. Use markdown when helpful.' },
          { role: 'user', content: message },
        ],
        max_tokens: 700,
      }),
    });
    if (!r.ok) throw new Error('AI HTTP ' + r.status);
    const d = await r.json();
    return d.choices?.[0]?.message?.content || '(no response)';
  }

  /* ==========================================================
     CONFIRM
     ========================================================== */
  function showConfirm(text) {
    const el = $('#confirm-text');
    if (el) el.textContent = text;
    $('#confirm-modal')?.classList.remove('hidden');
    setOrb('executing', 'AWAITING', 'USER CONFIRMATION');
  }

  function hideConfirm() {
    $('#confirm-modal')?.classList.add('hidden');
  }

  async function doConfirm() {
    hideConfirm();
    if (!state.pendingTask) return;
    try {
      const r = await fetch(BACKEND + '/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: state.pendingTask.id, api_key: state.apiKey }),
      });
      const d = await r.json();
      if (d.task) { saveTask(d.task); renderTask(d.task); }
      addMsg(d.reply || 'Done', 'bot');
      state.pendingTask = null;
      toast('Action confirmed', 'success');
      setOrb('success', 'COMPLETED', 'ACTION DONE');
      setTimeout(() => setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW'), 2000);
    } catch (e) {
      addMsg('⚠ ' + e.message, 'bot', true);
      setOrb('error', 'ERROR', 'ACTION FAILED');
    }
  }

  /* ==========================================================
     SETTINGS
     ========================================================== */
  function openSettings() {
    $('#api-key').value = state.apiKey;
    $('#model').value = state.model;
    $('#tts-toggle').checked = state.ttsEnabled;
    $('#orb-click-toggle').checked = state.orbClickEnabled;
    $('#settings-modal').classList.remove('hidden');
  }

  function closeSettings() {
    $('#settings-modal')?.classList.add('hidden');
  }

  async function testAI() {
    const key = $('#api-key').value.trim();
    const model = $('#model').value.trim() || 'openai/gpt-4o-mini';
    const out = $('#test-out');
    out.classList.remove('hidden', 'success', 'error');
    out.textContent = '⏳ Testing...';

    if (!key) {
      out.classList.add('error');
      out.textContent = '✕ No key entered.';
      return;
    }

    try {
      const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: 'Reply exactly: OK' }],
          max_tokens: 10,
        }),
      });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = await r.json();
      const reply = d.choices?.[0]?.message?.content || '';
      out.classList.add('success');
      out.textContent = '✓ AI ONLINE\nModel: ' + model + '\nReply: ' + reply;

      state.apiKey = key;
      state.model = model;
      localStorage.setItem('jarvis_key', key);
      localStorage.setItem('jarvis_model', model);
      setChip('chip-ai', true);
      state.aiOnline = true;
      toast('AI connected ✓', 'success');
    } catch (e) {
      out.classList.add('error');
      out.textContent = '✕ ' + e.message;
      setChip('chip-ai', false);
      state.aiOnline = false;
      toast('Connection failed', 'error');
    }
  }

  /* ==========================================================
     COMMAND PALETTE
     ========================================================== */
  const PALETTE_ITEMS = [
    { label: 'New Task', shortcut: '', action: () => newTask() },
    { label: 'Toggle Voice Input', shortcut: 'Ctrl+M', action: () => toggleVoice() },
    { label: 'Stop Speaking', shortcut: '', action: () => stopSpeaking() },
    { label: 'Open Settings', shortcut: 'Ctrl+,', action: () => openSettings() },
    { label: 'Test AI Connection', shortcut: '', action: () => openSettings() },
    { label: 'Clear Chat', shortcut: '', action: () => clearChat() },
    { label: 'What time is it?', shortcut: '', action: () => sendQuick('What time is it?') },
    { label: 'System info', shortcut: '', action: () => sendQuick('What is my RAM and CPU usage?') },
    { label: 'Take screenshot', shortcut: '', action: () => sendQuick('Take a screenshot and describe it') },
    { label: 'Open Chrome', shortcut: '', action: () => sendQuick('Open Chrome') },
    { label: 'Open Notepad', shortcut: '', action: () => sendQuick('Open Notepad') },
    { label: 'Search Google for Python tutorials', shortcut: '', action: () => sendQuick('Search Google for Python tutorials') },
    { label: 'Weather in London', shortcut: '', action: () => sendQuick("What's the weather in London?") },
    { label: 'Create folder on Desktop', shortcut: '', action: () => sendQuick('Create a folder called MyProject on my Desktop') },
  ];

  let paletteFiltered = [];
  let paletteIdx = 0;

  function openPalette() {
    const modal = $('#palette-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    const inp = $('#palette-input');
    if (inp) { inp.value = ''; inp.focus(); }
    renderPalette('');
  }

  function closePalette() {
    $('#palette-modal')?.classList.add('hidden');
  }

  function renderPalette(query) {
    const q = (query || '').toLowerCase();
    paletteFiltered = q
      ? PALETTE_ITEMS.filter(i => i.label.toLowerCase().includes(q))
      : PALETTE_ITEMS.slice();
    paletteIdx = 0;
    const list = $('#palette-list');
    if (!list) return;
    list.innerHTML = '';
    if (paletteFiltered.length === 0) {
      list.innerHTML = '<div class="palette-empty">No results</div>';
      return;
    }
    paletteFiltered.forEach((item, i) => {
      const el = document.createElement('div');
      el.className = 'palette-item' + (i === 0 ? ' active' : '');
      el.innerHTML = `<span>${escapeHtml(item.label)}</span><span class="palette-shortcut">${escapeHtml(item.shortcut || '')}</span>`;
      el.addEventListener('mouseenter', () => {
        paletteIdx = i;
        $$('.palette-item').forEach((x, j) => x.classList.toggle('active', j === i));
      });
      el.addEventListener('click', () => {
        closePalette();
        item.action();
      });
      list.appendChild(el);
    });
  }

  function paletteMove(dir) {
    if (paletteFiltered.length === 0) return;
    paletteIdx = (paletteIdx + dir + paletteFiltered.length) % paletteFiltered.length;
    $$('.palette-item').forEach((x, j) => x.classList.toggle('active', j === paletteIdx));
    const active = $$('.palette-item')[paletteIdx];
    active?.scrollIntoView({ block: 'nearest' });
  }

  function paletteSelect() {
    const item = paletteFiltered[paletteIdx];
    if (!item) return;
    closePalette();
    item.action();
  }

  /* ==========================================================
     ACTIONS
     ========================================================== */
  function newTask() {
    const chat = $('#chat');
    if (chat) chat.innerHTML = '';
    $('#welcome')?.classList.remove('hidden');
    $('#task-monitor')?.classList.add('hidden');
    const inp = $('#user-input');
    if (inp) { inp.value = ''; inp.focus(); }
    setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW');
    toast('New task ready', 'info', 1500);
  }

  function clearChat() {
    const chat = $('#chat');
    if (chat) chat.innerHTML = '';
    $('#welcome')?.classList.remove('hidden');
    toast('Chat cleared', 'info', 1500);
  }

  function sendQuick(text) {
    const inp = $('#user-input');
    if (inp) inp.value = text;
    handleSend();
  }

  function toggleSidebar() {
    const sb = $('#sidebar');
    const ov = $('#sidebar-overlay');
    const open = sb?.classList.toggle('open');
    ov?.classList.toggle('on', !!open);
  }

  function closeSidebar() {
    $('#sidebar')?.classList.remove('open');
    $('#sidebar-overlay')?.classList.remove('on');
  }

  /* ==========================================================
     ORB CLICK → VOICE
     ========================================================== */
  function onOrbClick(e) {
    e?.preventDefault?.();
    if (!state.orbClickEnabled) return;
    if (state.busy) {
      toast('JARVIS is still working...', 'warn');
      return;
    }
    if (state.speaking) {
      stopSpeaking();
      return;
    }
    toggleVoice();
  }

  /* ==========================================================
     INPUT HISTORY (UP/DOWN)
     ========================================================== */
  function historyPrev() {
    if (state.history.length === 0) return;
    state.historyIdx = Math.min(state.historyIdx + 1, state.history.length - 1);
    const inp = $('#user-input');
    if (inp) inp.value = state.history[state.historyIdx] || '';
  }

  function historyNext() {
    if (state.historyIdx <= 0) {
      state.historyIdx = -1;
      const inp = $('#user-input');
      if (inp) inp.value = '';
      return;
    }
    state.historyIdx--;
    const inp = $('#user-input');
    if (inp) inp.value = state.history[state.historyIdx] || '';
  }

  /* ==========================================================
     CLOCK
     ========================================================== */
  function tickClock() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    const el = $('#clock');
    if (el) el.textContent = `${hh}:${mm}:${ss}`;
  }

  /* ==========================================================
     INIT
     ========================================================== */
  function init() {
    checkBackend();
    setInterval(checkBackend, 7000);

    setChip('chip-ai', !!state.apiKey);
    if (state.apiKey) state.aiOnline = true;

    tickClock();
    setInterval(tickClock, 1000);

    // Example cards
    $$('.ex').forEach(el => el.addEventListener('click', () => {
      const cmd = el.dataset.cmd;
      if (!cmd) return;
      const inp = $('#user-input');
      if (inp) inp.value = cmd;
      handleSend();
    }));

    // Send / input
    $('#send-btn')?.addEventListener('click', handleSend);
    $('#user-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      } else if (e.key === 'ArrowUp' && !e.shiftKey) {
        e.preventDefault();
        historyPrev();
      } else if (e.key === 'ArrowDown' && !e.shiftKey) {
        e.preventDefault();
        historyNext();
      } else if (e.key === 'Escape') {
        hideConfirm();
      }
    });

    // Voice button
    $('#voice-btn')?.addEventListener('click', toggleVoice);

    // ORB CLICK → VOICE
    $('#orb')?.addEventListener('click', onOrbClick);
    $('#orb')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onOrbClick(e);
      }
    });
    $('#topbar-logo')?.addEventListener('click', onOrbClick);
    $('#sb-orb')?.addEventListener('click', onOrbClick);

    // Sidebar
    $('#menu-btn')?.addEventListener('click', toggleSidebar);
    $('#sidebar-close')?.addEventListener('click', closeSidebar);
    $('#sidebar-overlay')?.addEventListener('click', closeSidebar);
    $('#new-task')?.addEventListener('click', newTask);

    // Settings
    $('#settings-btn')?.addEventListener('click', openSettings);
    $('#settings-close')?.addEventListener('click', closeSettings);
    $('#test-btn')?.addEventListener('click', testAI);
    $('#settings-modal')?.addEventListener('click', (e) => {
      if (e.target.id === 'settings-modal') closeSettings();
    });
    $('#tts-toggle')?.addEventListener('change', (e) => {
      state.ttsEnabled = e.target.checked;
      localStorage.setItem('jarvis_tts', state.ttsEnabled ? 'true' : 'false');
      toast('Voice output ' + (state.ttsEnabled ? 'enabled' : 'disabled'), 'info', 1500);
    });
    $('#orb-click-toggle')?.addEventListener('change', (e) => {
      state.orbClickEnabled = e.target.checked;
      localStorage.setItem('jarvis_orb_click', state.orbClickEnabled ? 'true' : 'false');
      toast('Orb click-to-talk ' + (state.orbClickEnabled ? 'enabled' : 'disabled'), 'info', 1500);
    });

    // Confirm
    $('#confirm-yes')?.addEventListener('click', doConfirm);
    $('#confirm-no')?.addEventListener('click', () => {
      hideConfirm();
      state.pendingTask = null;
      setOrb('idle', 'STANDBY', 'ACTION CANCELLED');
      setTimeout(() => setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW'), 1600);
    });

    // Task monitor
    $('#task-toggle')?.addEventListener('click', () => {
      const steps = $('#task-steps');
      const btn = $('#task-toggle');
      if (!steps) return;
      if (steps.style.display === 'none') {
        steps.style.display = '';
        btn.textContent = 'HIDE';
      } else {
        steps.style.display = 'none';
        btn.textContent = 'SHOW';
      }
    });
    $('#task-cancel')?.addEventListener('click', () => {
      state.pendingTask = null;
      state.busy = false;
      hideConfirm();
      $('#task-monitor')?.classList.add('hidden');
      setOrb('idle', 'STANDBY', 'TASK CANCELLED');
      toast('Task cancelled', 'warn');
    });

    // Command palette
    $('#palette-btn')?.addEventListener('click', openPalette);
    $('#palette-modal')?.addEventListener('click', (e) => {
      if (e.target.id === 'palette-modal') closePalette();
    });
    $('#palette-input')?.addEventListener('input', (e) => renderPalette(e.target.value));
    $('#palette-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); paletteMove(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); paletteMove(-1); }
      else if (e.key === 'Enter') { e.preventDefault(); paletteSelect(); }
      else if (e.key === 'Escape') { e.preventDefault(); closePalette(); }
    });

    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Ctrl+K → command palette
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openPalette();
        return;
      }
      // Ctrl+M → voice
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'm') {
        e.preventDefault();
        toggleVoice();
        return;
      }
      // Ctrl+, → settings
      if ((e.ctrlKey || e.metaKey) && e.key === ',') {
        e.preventDefault();
        openSettings();
        return;
      }
      // Ctrl+/ → focus input
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        $('#user-input')?.focus();
        return;
      }
      // Space when idle + not in input → talk
      if (e.key === ' ' && document.activeElement === document.body) {
        e.preventDefault();
        onOrbClick(e);
        return;
      }
      // Escape closes modals
      if (e.key === 'Escape') {
        closeSettings();
        hideConfirm();
        closePalette();
        closeSidebar();
        if (state.speaking) stopSpeaking();
      }
    });

    initVoice();
    renderTaskHistory();

    setOrb('success', 'ONLINE', 'AGENT READY');
    setTimeout(() => setOrb('idle', 'STANDBY', 'CLICK ORB TO SPEAK · OR TYPE BELOW'), 1200);

    setTimeout(() => {
      addMsg(
        '**JARVIS Agent online.**\n\n' +
        'Give me a **goal** — I\'ll plan and execute it.\n\n' +
        '**Try:**\n' +
        '• "Open YouTube and search for travel vlogs"\n' +
        '• "Create a folder on my Desktop for my project"\n' +
        '• "Find my resume"\n' +
        '• "Open Notepad and type Hello"\n' +
        '• "Take a screenshot and describe it"\n\n' +
        '_Tip: click the orb to speak · Ctrl+K for commands · Ctrl+M for voice_',
        'bot'
      );
    }, 350);

    setTimeout(() => $('#user-input')?.focus(), 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();