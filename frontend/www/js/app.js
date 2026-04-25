/* =============================================
   SHESHIELD — app.js
   Backend: FastAPI  |  Base: /api/v1/
   Structure:
     - HTML  → index.html      (markup only)
     - CSS   → css/style.css   (all styles)
     - JS    → js/app.js       (all logic)
   Changes from original:
     - AI screen: chat flow (POST /api/v1/ai/chat)
     - SOS: calls POST /api/v1/ai/alert with contacts
     - renderReport: now handles JSON report object
     - History: handles both old (string) & new (JSON) reports
   ============================================= */

const API_BASE = 'http://192.168.18.43:8000';

// ── STATE ────────────────────────────────────
const state = {
  token:    localStorage.getItem('ss_token')    || null,
  user:     JSON.parse(localStorage.getItem('ss_user')     || 'null'),
  contacts: JSON.parse(localStorage.getItem('ss_contacts') || '[]'),
  history:  JSON.parse(localStorage.getItem('ss_history')  || '[]'),
  editContactId: null,
};

// Chat state — backend is stateless, frontend holds history
const chatState = {
  history: [],   // [{role:"user"|"assistant", content:"..."}]
  waiting: false,
};

// ── API HELPER ───────────────────────────────
async function api(method, path, body = null, auth = false) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) {
    const msg = data.detail
      ? (Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail)
      : 'Something went wrong';
    throw new Error(msg);
  }
  return data;
}

// ── INIT ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);
  if (state.token && state.user) showMainApp();
});

function updateClock() {
  const el = document.getElementById('curr-time');
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', hour12:true });
}

// ── NAVIGATION ───────────────────────────────
function goTo(screen) {
  document.querySelectorAll('.desk-nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.deskNav === screen);
  });
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(`screen-${screen}`).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.nav === screen);
  });

  const handlers = {
    home:     renderDashboard,
    ai:       initChatScreen,
    contacts: renderContacts,
    history:  renderHistory,
    profile:  renderProfile,
  };
  if (handlers[screen]) handlers[screen]();
}

// ── AUTH — LOGIN ─────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((t, i) => {
    t.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register'));
  });
  document.getElementById('form-login').classList.toggle('hidden', tab !== 'login');
  document.getElementById('form-register').classList.toggle('hidden', tab !== 'register');
  document.getElementById('auth-msg').innerHTML = '';
}

function showAuthMsg(msg, type = 'error') {
  document.getElementById('auth-msg').innerHTML =
    `<div class="alert alert-${type}"><span>${type === 'success' ? '✅' : '⚠️'}</span>${msg}</div>`;
}

async function doLogin() {
  const login_id = val('login-id');
  const password = val('login-pass');
  if (!login_id || !password) { showAuthMsg('Saare fields fill karein'); return; }
  const btn = document.getElementById('btn-login');
  btn.disabled = true; btn.textContent = 'Logging in...';
  try {
    const data = await api('POST', '/api/v1/users/login', { login_id, password });
    state.token = data.access_token;
    localStorage.setItem('ss_token', state.token);
    const user = await api('GET', '/api/v1/users/me', null, true);
    state.user = user;
    localStorage.setItem('ss_user', JSON.stringify(user));
    await syncContacts();
    showMainApp();
    renderDashboard(); // contacts sync ke baad dashboard refresh karo
  } catch (e) {
    showAuthMsg(e.message || 'Login failed');
  } finally {
    btn.disabled = false; btn.textContent = 'Sign In';
  }
}

async function doRegister() {
  const name     = val('reg-name');
  const username = val('reg-username');
  const email    = val('reg-email');
  const phone    = val('reg-phone');
  const password = val('reg-pass');
  if (!name || !username || !email || !phone || !password) {
    showAuthMsg('Saare required fields fill karein'); return;
  }
  const body = {
    name, username, email, phone, password,
    emergency_name:     val('reg-emer-name')  || undefined,
    emergency_phone:    val('reg-emer-phone') || undefined,
    emergency_relation: val('reg-emer-rel')   || undefined,
  };
  const btn = document.getElementById('btn-register');
  btn.disabled = true; btn.textContent = 'Creating account...';
  try {
    await api('POST', '/api/v1/users/', body);
    showAuthMsg('Account bana gaya! Ab login karein.', 'success');
    switchTab('login');
  } catch (e) {
    showAuthMsg(e.message || 'Registration failed');
  } finally {
    btn.disabled = false; btn.textContent = 'Create Account';
  }
}

function doLogout() {
  state.token = null; state.user = null;
  state.contacts = []; state.history = [];
  chatState.history = []; chatState.waiting = false;
  localStorage.clear();
  document.getElementById('bottom-nav').classList.add('hidden');
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screen-auth').classList.add('active');
  toast('Logged out ✓');
}

function showMainApp() {
  document.getElementById('bottom-nav').classList.remove('hidden');
  goTo('home');
}

function togglePass(inputId, iconEl) {
  const inp = document.getElementById(inputId);
  inp.type = inp.type === 'password' ? 'text' : 'password';
  const icon = iconEl.querySelector("i"); if (icon) { icon.className = inp.type === "password" ? "fas fa-eye" : "fas fa-eye-slash"; }
}

// ── DASHBOARD ────────────────────────────────
function renderDashboard() {
  if (!state.user) return;
  const firstName = state.user.name.split(' ')[0];
  document.getElementById('dash-greeting').textContent = 'Good to see you,';
  document.getElementById('dash-name').textContent = `${firstName} 👋`;
  const initials = state.user.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  document.getElementById('topbar-avatar').textContent = initials;
  const deskAv = document.getElementById('desk-avatar');
  if (deskAv) deskAv.textContent = initials;
  document.getElementById('stat-checks').textContent = state.history.length;
  const dsc = document.getElementById('desk-stat-checks'); if (dsc) dsc.textContent = state.history.length;
  document.getElementById('stat-contacts').textContent = state.contacts.length;
  const dsct = document.getElementById('desk-stat-contacts'); if (dsct) dsct.textContent = state.contacts.length;
  renderRecentChecks();
}

function renderRecentChecks() {
  const el = document.getElementById('recent-list');
  if (state.history.length === 0) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-icon">🔍</div>
      <h3>No check has been done yet</h3>
      <p>Use AI Safety Chat to check your area</p>
    </div>`;
    return;
  }
  el.innerHTML = state.history.slice(0, 5).map(h => {
    const riskClass = (h.risk_level || 'low').toLowerCase();
    const icons = { low: '🟢', moderate: '🟡', high: '🔴' };
    return `<div class="recent-item" onclick="openHistoryReport('${h.id}')">
      <div class="recent-dot ${riskClass}">${icons[riskClass] || '⚪'}</div>
      <div class="recent-info">
        <div class="recent-loc">${h.location}</div>
        <div class="recent-time">${h.travel_time}</div>
      </div>
      <span class="badge badge-${riskClass}">${capitalize(h.risk_level)}</span>
    </div>`;
  }).join('');
}

// ══════════════════════════════════════════════
//  AI CHAT — POST /api/v1/ai/chat
// ══════════════════════════════════════════════

function initChatScreen() {
  // Inject speaker toggle + mic toggle buttons
  setTimeout(injectAutoSpeakButton, 200);
  setTimeout(injectMicToggleButton, 200);
  // Only show greeting if chat is empty
  const msgs = document.getElementById('chat-messages');
  if (msgs && msgs.children.length === 0) {
    appendAIMessage("Hey girls! 😍 How are you? Main hoon tumhari safety companion 🛡️<br>Kahan jaana hai aaj? Batao, main check karti hoon! 💕", true);
  }
  // Restore voice mode — user ne pehle ON kiya tha to ON raho
  const savedVoiceMode = localStorage.getItem('ss_voice_mode');
  if (savedVoiceMode === '1' && !voiceAgent.isContinuous) {
    setTimeout(() => toggleVoiceMode(true), 400);
  }
  // Focus input
  setTimeout(() => document.getElementById('chat-input')?.focus(), 100);
}

function resetChatFull() {
  chatState.history = [];
  chatState.waiting = false;
  const msgs = document.getElementById('chat-messages');
  if (msgs) msgs.innerHTML = '';
  const btn = document.getElementById('btn-send');
  if (btn) btn.disabled = false;
  initChatScreen();
}

async function sendChat() {
  const inputEl = document.getElementById('chat-input');
  const message = inputEl?.value?.trim();
  if (!message || chatState.waiting) return;
  inputEl.value = '';

  const sendBtn = document.getElementById('btn-send');
  if (sendBtn) sendBtn.disabled = true;

  // Show user bubble
  appendUserMessage(message);

  // Detect language from typed/spoken message — TTS will match this
  voiceAgent.detectedLang = detectLang(message);

  // Handle bye locally — no API call needed
  const byeWords = ['bye', 'exit', 'quit', 'alvida', 'ok bye', 'goodbye', 'tata'];
  if (byeWords.includes(message.toLowerCase())) {
    appendAIMessage("Take care! Apna khayal rakhna 💕<br>if you need to check the safety again I am here 🛡️");
    chatState.history = [];
    if (sendBtn) sendBtn.disabled = false;
    return;
  }

  // Show typing indicator
  showTyping();
  chatState.waiting = true;

  try {
    const data = await api('POST', '/api/v1/ai/chat', {
      history: chatState.history,
      message,
    }, true);

    // Update conversation history
    chatState.history.push({ role: 'user',      content: message });
    chatState.history.push({ role: 'assistant', content: data.reply });

    hideTyping();
    appendAIMessage(data.reply);

    // ── SECRET CODE DETECTED → Silent SOS + Nearby ──────────────────────
    if (data.sos_triggered) {
      // Silently get GPS and fetch nearby places
      navigator.geolocation?.getCurrentPosition(async pos => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        try {
          // Nearby places fetch karo
          const nearby = await api('POST', '/api/v1/ai/nearby',
            { latitude: lat, longitude: lon, radius: 500 }, true);
          if (nearby?.nearby_places) {
            appendAIMessage(`📍 <b>Aapke aas paas:</b><br><pre style="font-size:12.5px;white-space:pre-wrap;margin:0;">${escHtml(nearby.nearby_places)}</pre>`);
          }
        } catch (_) {}
        // SOS bhi trigger karo silently
        if (state.contacts.length > 0) {
          try {
            const contacts = state.contacts.map(c => ({
              name: c.name, phone: c.phone ? `+91${c.phone}` : null, email: c.email || null,
            }));
            await api('POST', '/api/v1/ai/alert',
              { contacts, location: `${lat.toFixed(5)},${lon.toFixed(5)}`, latitude: lat, longitude: lon }, true);
          } catch (_) {}
        }
      }, () => {
        // GPS nahi mila — fir bhi SOS try karo
        if (state.contacts.length > 0) {
          const contacts = state.contacts.map(c => ({
            name: c.name, phone: c.phone ? `+91${c.phone}` : null, email: c.email || null,
          }));
          api('POST', '/api/v1/ai/alert',
            { contacts, location: 'Location unavailable' }, true).catch(() => {});
        }
      });
      return; // Normal report flow skip karo
    }

    if (data.ready && data.report) {
      // Save to local history
      const entry = {
        id:         Date.now(),
        location:   data.location,
        travel_time: data.time,
        risk_level: data.report.risk_level || 'Unknown',
        created_at: new Date().toISOString(),
        report:     data.report,
      };
      state.history.unshift(entry);
      localStorage.setItem('ss_history', JSON.stringify(state.history));

      // Render beautiful report card in chat
      appendReportCard(data.report, data.location, data.time);

      // Reset chat for next query
      chatState.history = [];
    }
  } catch (e) {
    hideTyping();
    appendAIMessage("Something went wrong 😔 Try once more!");
  } finally {
    chatState.waiting = false;
    if (sendBtn) sendBtn.disabled = false;
    document.getElementById('chat-input')?.focus();
  }
}

// ── Chat rendering helpers ────────────────────
function appendUserMessage(text) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const div = document.createElement('div');
  div.className = 'chat-msg chat-msg-user';
  div.innerHTML = `<div class="chat-bubble chat-bubble-user">${escHtml(text)}</div>`;
  msgs.appendChild(div);
  scrollChat();
}

function appendAIMessage(html) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const div = document.createElement('div');
  div.className = 'chat-msg chat-msg-ai';
  div.innerHTML = `
    <div class="chat-ai-avatar">🛡️</div>
    <div class="chat-bubble chat-bubble-ai">${html}</div>
  `;
  msgs.appendChild(div);
  scrollChat();
}

function appendReportCard(report, location, time) {
  const riskLower = (report.risk_level || 'unknown').toLowerCase();
  const riskEmoji = { low: '🟢', moderate: '🟡', high: '🔴' }[riskLower] || '⚪';
  const confidence = report.confidence_score || 0;
  const safeAlt = (report.safe_alternative || '').toLowerCase();
  const showAlt = safeAlt && safeAlt !== 'not required';

  // Build as plain chat bubble text
  let lines = [];
  lines.push(`${riskEmoji} <b>${escHtml(location)}</b> — ${escHtml(time)}`);
  lines.push(`Risk: <b>${report.risk_level}</b> &nbsp;·&nbsp; Confidence: ${confidence}%`);
  lines.push('');
  if (report.summary)    lines.push(`💡 ${escHtml(report.summary)}`);
  if (report.transport)  lines.push(`🚌 ${escHtml(report.transport)}`);
  if (report.precaution) lines.push(`⚠️ ${escHtml(report.precaution)}`);
  if (showAlt)           lines.push(`📍 Safer area: ${escHtml(report.safe_alternative)}`);
  lines.push('');

  // Links as inline text
  const mapsLink = report.maps_link
    ? `<a href="${report.maps_link}" target="_blank" style="color:var(--teal-light);text-decoration:none;">🗺️ View on Maps</a>`
    : '';
  const dirLink = report.maps_directions
    ? ` &nbsp; <a href="${report.maps_directions}" target="_blank" style="color:var(--teal-light);text-decoration:none;">🧭 Directions</a>`
    : '';
  if (mapsLink) lines.push(mapsLink + dirLink);

  // Helplines as plain text
  lines.push('🆘 <a href="tel:1090" style="color:var(--red);text-decoration:none;">1090</a> · <a href="tel:100" style="color:var(--red);text-decoration:none;">100</a> · <a href="tel:108" style="color:var(--red);text-decoration:none;">108</a>');

  appendAIMessage(lines.join('<br>'));
}

function showTyping() {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const div = document.createElement('div');
  div.className = 'typing-wrap';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="chat-ai-avatar">🛡️</div>
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  msgs.appendChild(div);
  scrollChat();
}

function hideTyping() {
  document.getElementById('typing-indicator')?.remove();
}

function scrollChat() {
  const msgs = document.getElementById('chat-messages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── History report viewer ─────────────────────
function openHistoryReport(id) {
  const h = state.history.find(x => String(x.id) === String(id));
  if (!h) return;
  goTo('ai');

  // Clear chat and show the historical report
  const msgs = document.getElementById('chat-messages');
  if (msgs) msgs.innerHTML = '';

  const dateStr = new Date(h.created_at).toLocaleDateString('en-IN',
    { day: 'numeric', month: 'short', year: 'numeric' });
  appendAIMessage(`Ye tha tumhara safety check from ${dateStr} 📋`);

  // Handle both old (string) and new (JSON object) report formats
  if (h.report && typeof h.report === 'object') {
    appendReportCard(h.report, h.location, h.travel_time);
  } else if (h.report && typeof h.report === 'string') {
    // Legacy string format — show in a bubble
    appendAIMessage(escHtml(h.report));
  } else {
    appendAIMessage(`Location: ${escHtml(h.location)}, Time: ${escHtml(h.travel_time)}<br>Risk: ${h.risk_level}`);
  }
  chatState.history = []; // Don't continue from a history view
}

// ── EMERGENCY CONTACTS ───────────────────────
async function syncContacts() {
  try {
    const data = await api('GET', '/api/v1/emergency/', null, true);
    state.contacts = Array.isArray(data) ? data : [];
    localStorage.setItem('ss_contacts', JSON.stringify(state.contacts));
  } catch (e) {
    console.error('syncContacts error:', e);
    // cached data use karo agar API fail ho
    state.contacts = JSON.parse(localStorage.getItem('ss_contacts') || '[]');
  }
}

function renderContacts() {
  const el = document.getElementById('contacts-list');
  if (state.contacts.length === 0) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-icon">📞</div>
      <h3>There is no Contact at all</h3>
      <p>Add a contact for emergency Purposes</p>
    </div>`;
    return;
  }
  el.innerHTML = state.contacts.map(c => `
    <div class="contact-card">
      <div class="contact-avatar">${c.name[0].toUpperCase()}</div>
      <div class="contact-info">
        <div class="contact-name">${c.name}</div>
        <div class="contact-rel">${c.relation || 'Contact'}</div>
        <div class="contact-phone">📱 ${c.phone}</div>
      </div>
      <div class="contact-btns">
        <a href="tel:${c.phone}" class="icon-btn icon-btn-call" title="Call"><i class="fas fa-phone"></i></a>
        <button class="icon-btn icon-btn-edit" onclick="openEditContact(${c.id})" title="Edit"><i class="fas fa-pen"></i></button>
        <button class="icon-btn icon-btn-del" onclick="deleteContact(${c.id})" title="Delete"><i class="fas fa-trash"></i></button>
      </div>
    </div>
  `).join('');
}

function openAddContact() {
  state.editContactId = null;
  document.getElementById('modal-title').textContent = 'Add Contact';
  ['c-name','c-phone','c-email','c-relation'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('contact-modal-msg').innerHTML = '';
  document.getElementById('contact-modal').classList.remove('hidden');
}

function openEditContact(id) {
  const c = state.contacts.find(x => x.id === id);
  if (!c) return;
  state.editContactId = id;
  document.getElementById('modal-title').textContent = 'Edit Contact';
  document.getElementById('c-name').value     = c.name;
  document.getElementById('c-phone').value    = c.phone;
  document.getElementById('c-email').value    = c.email || '';
  document.getElementById('c-relation').value = c.relation || '';
  document.getElementById('contact-modal-msg').innerHTML = '';
  document.getElementById('contact-modal').classList.remove('hidden');
}

async function saveContact() {
  const name     = val('c-name');
  const phone    = val('c-phone');
  const email    = val('c-email');
  const relation = val('c-relation');
  if (!name || !phone) {
    document.getElementById('contact-modal-msg').innerHTML =
      '<div class="alert alert-error"><span>⚠️</span>Name aur Phone required hai</div>';
    return;
  }
  const body = { name, phone, email: email || null, relation: relation || null };
  const btn = document.getElementById('btn-save-contact');
  btn.disabled = true;
  try {
    if (state.editContactId) {
      const updated = await api('PUT', `/api/v1/emergency/${state.editContactId}`, body, true);
      const idx = state.contacts.findIndex(x => x.id === state.editContactId);
      if (idx !== -1) state.contacts[idx] = updated;
      toast('Contact update ho gaya ✓', 'success');
    } else {
      const created = await api('POST', '/api/v1/emergency/', body, true);
      state.contacts.push(created);
      toast('Contact add ho gaya ✓', 'success');
    }
    localStorage.setItem('ss_contacts', JSON.stringify(state.contacts));
    closeContactModal();
    renderContacts();
    document.getElementById('stat-contacts').textContent = state.contacts.length;
    const dsct = document.getElementById('desk-stat-contacts'); if (dsct) dsct.textContent = state.contacts.length;
  } catch (e) {
    document.getElementById('contact-modal-msg').innerHTML =
      `<div class="alert alert-error"><span>⚠️</span>${e.message}</div>`;
  } finally {
    btn.disabled = false;
  }
}

async function deleteContact(id) {
  if (!confirm('Yeh contact delete karein?')) return;
  try {
    await api('DELETE', `/api/v1/emergency/${id}`, null, true);
    state.contacts = state.contacts.filter(c => c.id !== id);
    localStorage.setItem('ss_contacts', JSON.stringify(state.contacts));
    renderContacts();
    toast('Contact delete ho gaya', 'error');
    document.getElementById('stat-contacts').textContent = state.contacts.length;
    const dsct = document.getElementById('desk-stat-contacts'); if (dsct) dsct.textContent = state.contacts.length;
  } catch (e) {
    toast(e.message || 'Delete failed', 'error');
  }
}

function closeContactModal() {
  document.getElementById('contact-modal').classList.add('hidden');
  state.editContactId = null;
}

// ── HISTORY ──────────────────────────────────
function renderHistory() {
  const el = document.getElementById('history-list');
  if (state.history.length === 0) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-icon">📋</div>
      <h3>There is no history ⟳ </h3>
      <p>Your safety Check will be visible here 💕</p>
    </div>`;
    return;
  }
  el.innerHTML = state.history.map(h => {
    const riskClass = (h.risk_level || 'low').toLowerCase();
    const dt = new Date(h.created_at);
    const dateStr = dt.toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' });

    // Preview: handle both string and JSON report
    let preview = '';
    if (h.report && typeof h.report === 'object') {
      preview = h.report.summary ? `<div class="history-preview-json">${h.report.summary.slice(0, 90)}${h.report.summary.length > 90 ? '…' : ''}</div>` : '';
    } else if (h.report && typeof h.report === 'string') {
      preview = `<div class="history-preview">${h.report.slice(0, 90)}${h.report.length > 90 ? '…' : ''}</div>`;
    }

    return `<div class="history-card" onclick="openHistoryReport('${h.id}')">
      <div class="history-top">
        <div>
          <div class="history-loc">📍 ${h.location}</div>
          <div class="history-meta">🕐 ${h.travel_time} &nbsp;·&nbsp; ${dateStr}</div>
        </div>
        <span class="badge badge-${riskClass}">${capitalize(h.risk_level)}</span>
      </div>
      ${preview}
    </div>`;
  }).join('');
}

// ── PROFILE ──────────────────────────────────
function renderProfile() {
  if (!state.user) return;
  const u = state.user;
  const initials = u.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  document.getElementById('pf-avatar').textContent   = initials;
  document.getElementById('pf-name-big').textContent = u.name;
  document.getElementById('pf-role').textContent     = u.role.toUpperCase();
  document.getElementById('pf-name').textContent     = u.name;
  document.getElementById('pf-email').textContent    = u.email;
  document.getElementById('pf-phone').textContent    = u.phone;
  document.getElementById('pf-username').textContent = `@${u.username}`;
  document.getElementById('pf-status').textContent   = u.is_active ? '✅ Active' : '❌ Inactive';
  loadSecretCode();
}

// ── SOS ──────────────────────────────────────
function showSOSPopup(msg, type) {
  // type: 'success' | 'error' | 'loading'
  // NOTE: SOS screen is disguised — only show very subtle status
  const popup = document.getElementById('sos-popup');
  if (!popup) return;
  // Subtle colours — blend into the fake weather background
  const bg = {
    success: 'rgba(255,255,255,0.12)',
    error:   'rgba(255,255,255,0.12)',
    loading: 'rgba(255,255,255,0.08)'
  };
  // Map messages to innocuous-looking text (attacker-proof)
  const safeMsg = {
    '⏳ The Alert is sending':     'Updating...',
    '✅ The Alert has been sent.': '✓ Done',
  };
  popup.style.background = bg[type] || bg.loading;
  popup.classList.remove('hidden');
  popup.textContent      = safeMsg[msg] || '...';
}

function hideSOSPopup() {
  const popup = document.getElementById('sos-popup');
  if (popup) popup.classList.add('hidden');
}

async function triggerSOS() {
  document.getElementById('sos-overlay').classList.add('active');
  hideSOSPopup();
  if (navigator.vibrate) navigator.vibrate([300, 100, 300, 100, 300]);

  // No contacts — error immediately
  if (state.contacts.length === 0) {
    showSOSPopup('⚠️ There is no emergency contact. add a contact.', 'error');
    return;
  }

  // Show loading
  showSOSPopup('⏳ The Alert is sending', 'loading');

  // Get location — pehle cached map location try karo, warna fresh GPS
  let latitude = null, longitude = null;
  let locationStr = 'Location unavailable';
  try {
    // Agar map wali location already hai to wahi use karo (fastest)
    if (typeof currentLocation !== 'undefined' && currentLocation) {
      latitude = currentLocation.lat;
      longitude = currentLocation.lng;
      locationStr = `${latitude.toFixed(5)},${longitude.toFixed(5)}`;
    } else if (navigator.geolocation) {
      // Fresh GPS — 15 second timeout (5s bahut kam tha)
      await new Promise(resolve => {
        navigator.geolocation.getCurrentPosition(
          pos => {
            latitude = pos.coords.latitude;
            longitude = pos.coords.longitude;
            locationStr = `${latitude.toFixed(5)},${longitude.toFixed(5)}`;
            resolve();
          },
          () => resolve(),
          { timeout: 15000, enableHighAccuracy: true, maximumAge: 30000 }
        );
      });
    }
  } catch (_) {}

  // Call backend
  try {
    const contacts = state.contacts.map(c => ({
      name:  c.name,
      phone: c.phone ? `+91${c.phone}` : null,
      email: c.email || null,
    }));
    await api('POST', '/api/v1/ai/alert', {
      contacts,
      location: locationStr,
      latitude: latitude,
      longitude: longitude
    }, true);
    showSOSPopup('✅ The Alert has been sent.', 'success');
    
    // ✨ START LIVE TRACKING (if location available)
    if (latitude && longitude) {
      console.log('🚀 Starting LIVE TRACKING...');
      setTimeout(() => {
        startLiveTracking(latitude, longitude);
      }, 1500);
    }
    
  } catch (e) {
    const msg = (e.message || '').toLowerCase();
    if (msg.includes('fetch') || msg.includes('network') || msg.includes('failed')) {
      showSOSPopup('⚠️ There is a network issue,Check the Internet.', 'error');
    } else {
      showSOSPopup(`⚠️ The Alert was not Sent: ${e.message || 'Unknown error'}`, 'error');
    }
  }
}

function closeSOS() {
  document.getElementById('sos-overlay').classList.remove('active');
  hideSOSPopup();
  toast('SOS cancelled', 'error');
}

// ── PROFILE UPDATE ───────────────────────────
let currentEditType = null;

function openEditProfile(type) {
  currentEditType = type;
  ['email','phone','password'].forEach(t => {
    document.getElementById(`edit-${t}-fields`).classList.add('hidden');
  });
  document.getElementById(`edit-${type}-fields`).classList.remove('hidden');
  document.getElementById('profile-modal-msg').innerHTML = '';
  const titles = { email: '📧 Update Email', phone: '📱 Update Phone', password: '🔒 Change Password' };
  document.getElementById('profile-modal-title').textContent = titles[type];
  if (type === 'email') document.getElementById('edit-email').value = state.user?.email || '';
  if (type === 'phone') document.getElementById('edit-phone').value = state.user?.phone || '';
  if (type === 'password') {
    document.getElementById('edit-pass').value = '';
    document.getElementById('edit-pass-confirm').value = '';
  }
  document.getElementById('profile-edit-modal').classList.remove('hidden');
}

function closeProfileModal() {
  document.getElementById('profile-edit-modal').classList.add('hidden');
  currentEditType = null;
}

async function saveProfileUpdate() {
  const btn = document.getElementById('btn-save-profile');
  const msgEl = document.getElementById('profile-modal-msg');
  msgEl.innerHTML = '';
  let body = {};
  if (currentEditType === 'email') {
    const email = val('edit-email');
    if (!email) { msgEl.innerHTML = '<div class="alert alert-error"><span>⚠️</span>Email daalo</div>'; return; }
    body = { email };
  } else if (currentEditType === 'phone') {
    const phone = val('edit-phone');
    if (!phone || phone.length !== 10) { msgEl.innerHTML = '<div class="alert alert-error"><span>⚠️</span>Enter a valid 10-digit phone number</div>'; return; }
    body = { phone };
  } else if (currentEditType === 'password') {
    const pass = val('edit-pass');
    const confirm = val('edit-pass-confirm');
    if (!pass || pass.length < 6) { msgEl.innerHTML = '<div class="alert alert-error"><span>⚠️</span>Enter a password at least 6 characters</div>'; return; }
    if (pass !== confirm) { msgEl.innerHTML = '<div class="alert alert-error"><span>⚠️</span>both password and login id do not match</div>'; return; }
    body = { password: pass };
  }
  btn.disabled = true; btn.textContent = 'Saving...';
  try {
    const updated = await api('PUT', `/api/v1/users/${state.user.id}`, body, true);
    state.user = { ...state.user, ...updated };
    localStorage.setItem('ss_user', JSON.stringify(state.user));
    closeProfileModal();
    renderProfile();
    toast('Profile update ho gaya ✓', 'success');
  } catch (e) {
    msgEl.innerHTML = `<div class="alert alert-error"><span>⚠️</span>${e.message}</div>`;
  } finally {
    btn.disabled = false; btn.textContent = 'Save Changes';
  }
}

// ── SECRET CODE ──────────────────────────────
async function loadSecretCode() {
  try {
    const data = await api('GET', '/api/v1/users/me/secret-code', null, true);
    const el = document.getElementById('secret-code-status');
    if (el) {
      el.textContent = data.secret_code
        ? `Set: "${data.secret_code}" — tap to change`
        : 'Not set — tap to add';
    }
    // Voice listener ko user ka real secret code do
    if (data.secret_code && typeof voiceState !== 'undefined') {
      voiceState.secretCode = data.secret_code.trim().toLowerCase();
      console.log('🔐 Voice secret code loaded from profile');
    }
  } catch (_) {}
}

function openSecretCodeModal() {
  document.getElementById('sc-word').value = '';
  document.getElementById('secret-code-modal-msg').innerHTML = '';
  document.getElementById('secret-code-modal').classList.remove('hidden');
  setTimeout(() => document.getElementById('sc-word')?.focus(), 200);
}

function closeSecretCodeModal() {
  document.getElementById('secret-code-modal').classList.add('hidden');
}

async function saveSecretCode() {
  const word = val('sc-word');
  const msgEl = document.getElementById('secret-code-modal-msg');
  if (!word || word.length < 2) {
    msgEl.innerHTML = '<div class="alert alert-error"><span>⚠️</span>Kam se kam 2 characters ka word daalo</div>';
    return;
  }
  const btn = document.getElementById('btn-save-secret');
  btn.disabled = true; btn.textContent = 'Saving...';
  try {
    await api('POST', '/api/v1/users/me/secret-code', { secret_code: word }, true);
    closeSecretCodeModal();
    toast(`Secret code "${word}" save ho gaya 🛡️`, 'success');
    loadSecretCode(); // status refresh karo
  } catch (e) {
    msgEl.innerHTML = `<div class="alert alert-error"><span>⚠️</span>${e.message}</div>`;
  } finally {
    btn.disabled = false; btn.textContent = 'Save Secret Code';
  }
}

// ── UTILS ────────────────────────────────────
function val(id) { return document.getElementById(id)?.value?.trim() || ''; }
function capitalize(str) { if (!str) return ''; return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase(); }
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast show${type ? ' toast-' + type : ''}`;
  setTimeout(() => el.classList.remove('show'), 3200);
}

// ── MAP ──────────────────────────────────────
let map = null, directionsService = null, directionsRenderer = null;
let placesService = null, userMarker = null, placeMarkers = [];
let currentLocation = null, mapInitialized = false;
let activeFilters = new Set(['hospital', 'restaurant', 'shopping_mall', 'police']);

function initMap() {
  mapInitialized = true;
  const defaultCenter = { lat: 26.8467, lng: 80.9462 };
  map = new google.maps.Map(document.getElementById('google-map'), {
    center: defaultCenter, zoom: 15,
    mapTypeControl: false, fullscreenControl: false, streetViewControl: false,
    zoomControlOptions: { position: google.maps.ControlPosition.RIGHT_CENTER },
    styles: mapStyles(),
  });
  directionsService  = new google.maps.DirectionsService();
  directionsRenderer = new google.maps.DirectionsRenderer({
    suppressMarkers: false,
    polylineOptions: { strokeColor: '#0b1d3a', strokeWeight: 5, strokeOpacity: 0.85 }
  });
  directionsRenderer.setMap(map);
  placesService = new google.maps.places.PlacesService(map);
  const locBtn = document.createElement('button');
  locBtn.className = 'my-location-btn';
  locBtn.innerHTML = '📍';
  locBtn.title = 'My Location';
  locBtn.onclick = goToMyLocation;
  document.getElementById('screen-map').appendChild(locBtn);
  goToMyLocation();
}

function goToMyLocation() {
  if (!navigator.geolocation) { toast('Geolocation not supported', 'error'); return; }
  navigator.geolocation.getCurrentPosition(pos => {
    currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    map.setCenter(currentLocation); map.setZoom(16);
    if (userMarker) userMarker.setMap(null);
    userMarker = new google.maps.Marker({
      position: currentLocation, map, title: 'You are here',
      icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: '#0b1d3a', fillOpacity: 1, strokeColor: 'white', strokeWeight: 3 },
      zIndex: 999,
    });
    loadNearbyPlaces(currentLocation);
  }, () => toast('Location access denied', 'error'));
}

// ── searchLocation is handled in map-filters.js ──

// Store all fetched places per type for filter toggling
let allFetchedPlaces = { hospital: [], police: [], shopping_mall: [], restaurant: [] };

// ── Load Nearby Places via Backend Overpass API (free, no billing needed) ──
async function loadNearbyPlaces(location) {
  placeMarkers.forEach(m => m.setMap(null));
  placeMarkers = [];
  allFetchedPlaces = { hospital: [], police: [], shopping_mall: [], restaurant: [] };

  try {
    const data = await api('POST', '/api/v1/ai/nearby', {
      latitude:  location.lat,
      longitude: location.lng,
      radius:    3000
    }, false);

    if (!data || !data.places || data.places.length === 0) return;

    let nearestHospital = null;

    data.places.forEach(place => {
      // backend returns 'mall' — map to 'shopping_mall' for frontend
      const typeKey = place.type === 'mall' ? 'shopping_mall' : place.type;
      if (!allFetchedPlaces[typeKey]) allFetchedPlaces[typeKey] = [];
      allFetchedPlaces[typeKey].push(place);

      const placeLatLng = new google.maps.LatLng(place.lat, place.lng);

      if (place.type === 'hospital') {
        if (!nearestHospital || place.distance < nearestHospital.dist) {
          nearestHospital = { place, placeLatLng, dist: place.distance };
        }
      }

      const marker = new google.maps.Marker({
        position: placeLatLng, map,
        title: place.name,
        icon: placeIcon(typeKey),
        animation: google.maps.Animation.DROP,
        visible: true,
      });

      marker.addListener('click', () => {
        showPlaceDetailBackend(place, typeKey, placeLatLng);
      });

      marker._placeType = typeKey;
      placeMarkers.push(marker);
    });

    if (nearestHospital) {
      const ll = nearestHospital.placeLatLng;
      await getRouteTo(ll.lat(), ll.lng(), nearestHospital.place.name);
    }
  } catch (e) {
    console.error('loadNearbyPlaces error:', e);
  }
}

function showPlaceDetail(place, type, placeLatLng, dist) {
  const sheet = document.getElementById('place-sheet');
  const content = document.getElementById('place-sheet-content');
  const typeInfo = placeTypeInfo(type);
  const isOpen = place.opening_hours?.isOpen?.() ?? null;
  const phone  = place.formatted_phone_number || '';
  const rating = place.rating ? `⭐ ${place.rating}` : '';
  const distStr = dist < 1000 ? `${Math.round(dist)}m away` : `${(dist/1000).toFixed(1)}km away`;
  content.innerHTML = `
    <div class="place-detail">
      <div class="place-name">${place.name}</div>
      <span class="place-type-badge place-type-${typeInfo.cls}">${typeInfo.icon} ${typeInfo.label}</span>
      <div class="place-info-row"><span class="place-info-icon">📍</span><span>${place.vicinity || 'Address not available'}</span></div>
      <div class="place-info-row"><span class="place-info-icon">📏</span><span>${distStr}</span>${rating ? `<span style="margin-left:auto">${rating}</span>` : ''}</div>
      ${isOpen !== null ? `<div class="place-info-row"><span class="place-info-icon">🕐</span><span class="${isOpen ? 'open-badge' : 'closed-badge'}">${isOpen ? 'Open Now' : 'Closed'}</span></div>` : ''}
      <div class="place-action-row">
        <button class="place-action-btn btn-route" onclick="getRouteTo(${placeLatLng.lat},${placeLatLng.lng},'${place.name.replace(/'/g,'')}')">🛣️ Safe Route</button>
        ${phone
          ? `<a href="tel:${phone}" class="place-action-btn btn-call-place">📞 Call</a>`
          : `<button class="place-action-btn btn-call-place" onclick="openInMaps(${placeLatLng.lat},${placeLatLng.lng})">🗺️ Open Maps</button>`}
      </div>
    </div>`;
  sheet.classList.add('open');
}

// Show place detail from backend Overpass API data
function showPlaceDetailBackend(place, type, placeLatLng) {
  const sheet   = document.getElementById('place-sheet');
  const content = document.getElementById('place-sheet-content');
  const typeInfo = placeTypeInfo(type);
  const distStr  = place.distance < 1000
    ? `${place.distance}m door`
    : `${(place.distance / 1000).toFixed(1)}km door`;

  content.innerHTML = `
    <div class="place-detail">
      <div class="place-name">${place.name}</div>
      <span class="place-type-badge place-type-${typeInfo.cls}">${typeInfo.icon} ${typeInfo.label}</span>
      <div class="place-info-row">
        <span class="place-info-icon">📍</span>
        <span>${place.address || 'Address not available'}</span>
      </div>
      <div class="place-info-row">
        <span class="place-info-icon">📏</span>
        <span>${distStr}</span>
      </div>
      <div class="place-action-row">
        <button class="place-action-btn btn-route"
          onclick="getRouteTo(${placeLatLng.lat()},${placeLatLng.lng()},'${place.name.replace(/'/g, '')}')">
          🛣️ Safe Route
        </button>
        <button class="place-action-btn btn-call-place"
          onclick="openInMaps(${placeLatLng.lat()},${placeLatLng.lng()})">
          🗺️ Open Maps
        </button>
      </div>
    </div>`;
  sheet.classList.add('open');
}

function closePlaceSheet() { document.getElementById('place-sheet').classList.remove('open'); }

async function getRouteTo(destLat, destLng, placeName) {
  if (!currentLocation) { toast('Pehle location set karo', 'error'); return; }
  closePlaceSheet();
  try {
    // Free OSRM API - no API key needed
    const url = `https://router.project-osrm.org/route/v1/foot/${currentLocation.lng},${currentLocation.lat};${destLng},${destLat}?overview=full&geometries=geojson`;
    const res = await fetch(url);
    const data = await res.json();
    if (data.code === 'Ok' && data.routes.length > 0) {
      const route = data.routes[0];
      const coords = route.geometry.coordinates.map(([lng, lat]) => ({ lat, lng }));
      // Draw polyline on map
      if (window._routePolyline) window._routePolyline.setMap(null);
      window._routePolyline = new google.maps.Polyline({
        path: coords, map,
        strokeColor: '#0b1d3a', strokeWeight: 5, strokeOpacity: 0.85
      });
      // Fit map to route
      const bounds = new google.maps.LatLngBounds();
      coords.forEach(c => bounds.extend(c));
      map.fitBounds(bounds);
      // Show banner
      const distKm = (route.distance / 1000).toFixed(1);
      const durMin = Math.round(route.duration / 60);
      const banner = document.getElementById('route-banner');
      if (banner) {
        banner.querySelector('.route-info').textContent = `🚶 ${placeName} — ${distKm} km · ${durMin} min`;
        banner.classList.add('show');
      }
    } else {
      toast('Route nahi mila', 'error');
    }
  } catch(e) {
    toast('Route nahi mila', 'error');
  }
}

function openInMaps(lat, lng) { window.open(`https://www.google.com/maps/search/?api=1&query=${lat},${lng}`, '_blank'); }

// ── Filter button state tracker ──
let activeFilterType = null;
let filterResultMarker = null;

async function toggleFilter(el, type) {
  // Same button dobara press → clear
  if (activeFilterType === type) { clearActiveFilter(); return; }

  clearActiveFilter();
  activeFilterType = type;

  document.querySelectorAll('.filter-chip').forEach(btn => btn.classList.remove('active'));
  el.classList.add('active');

  if (!currentLocation) {
    toast('Pehle apni location set karo', 'error');
    clearActiveFilter();
    return;
  }

  const iconMap  = { hospital: '🏥', restaurant: '🍽️', shopping_mall: '🏬', police: '👮' };
  const labelMap = { hospital: 'Hospital', restaurant: 'Restaurant', shopping_mall: 'Mall', police: 'Police Station' };
  // backend uses 'mall', frontend uses 'shopping_mall'
  const backendType = type === 'shopping_mall' ? 'mall' : type;

  toast(iconMap[type] + ' ' + labelMap[type] + ' dhundh raha hoon...', 'info');

  try {
    const data = await api('POST', '/api/v1/ai/nearby', {
      latitude:  currentLocation.lat,
      longitude: currentLocation.lng,
      radius:    3000
    }, false);

    if (!data || !data.places || data.places.length === 0) {
      toast('no  ' + labelMap[type] + ' under the 3 km ', 'error');
      clearActiveFilter();
      return;
    }

    // Filter results to requested type
    const filtered = data.places.filter(p => {
      const pt = p.type === 'mall' ? 'shopping_mall' : p.type;
      return pt === type;
    });

    if (filtered.length === 0) {
      toast('no ' + labelMap[type] + ' under the 3 km', 'error');
      clearActiveFilter();
      return;
    }

    // Nearest place (backend already sorts, but just in case)
    const nearest = filtered.reduce((a, b) => a.distance < b.distance ? a : b);

    if (filterResultMarker) { filterResultMarker.setMap(null); filterResultMarker = null; }

    filterResultMarker = new google.maps.Marker({
      position: { lat: nearest.lat, lng: nearest.lng },
      map,
      title: nearest.name,
      icon: placeIcon(type),
      zIndex: 100,
      animation: google.maps.Animation.DROP,
    });

    map.panTo({ lat: nearest.lat, lng: nearest.lng });
    map.setZoom(16);

    _showFilterInfoCard(
      nearest.name,
      nearest.distance,
      nearest.address || '',
      nearest.lat,
      nearest.lng,
      currentLocation.lat,
      currentLocation.lng,
      iconMap[type]
    );

    toast('✅ ' + nearest.name + ' — ' + nearest.distance + 'm door', 'success');

  } catch (e) {
    console.error('Filter error:', e);
    toast('Kuch galat hua, dobara try karo', 'error');
    clearActiveFilter();
  }
}

function clearActiveFilter() {
  activeFilterType = null;
  document.querySelectorAll('.filter-chip').forEach(btn => btn.classList.remove('active'));
  if (filterResultMarker) { filterResultMarker.setMap(null); filterResultMarker = null; }
  const card = document.getElementById('filter-info-card');
  if (card) card.remove();
}

function _showFilterInfoCard(name, distM, address, placeLat, placeLng, userLat, userLng, icon) {
  const old = document.getElementById('filter-info-card');
  if (old) old.remove();

  const directionsUrl = `https://www.google.com/maps/dir/?api=1&origin=${userLat},${userLng}&destination=${placeLat},${placeLng}&travelmode=walking`;

  const card = document.createElement('div');
  card.id = 'filter-info-card';
  card.className = 'filter-info-card';
  card.innerHTML =
    `<span class="fic-icon">${icon}</span>
     <div class="fic-body">
       <strong class="fic-name">${name}</strong>
       <span class="fic-dist">📏 ${distM}m door</span>
       <small class="fic-addr">${address}</small>
     </div>
     <div class="fic-actions">
       <a href="${directionsUrl}" target="_blank" class="fic-btn fic-btn-dir">🗺️ Directions</a>
       <button onclick="clearActiveFilter()" class="fic-btn fic-btn-close">✕ Band karo</button>
     </div>`;
  document.body.appendChild(card);
}

async function routeToNearestOfType(type) {
  if (!currentLocation) return;
  try {
    const data = await api('POST', '/api/v1/ai/nearby', {
      latitude:  currentLocation.lat,
      longitude: currentLocation.lng,
      radius:    3000
    }, false);
    if (!data || !data.places) { toast('Koi jagah nahi mili', 'error'); return; }
    const backendType = type === 'shopping_mall' ? 'mall' : type;
    const filtered = data.places.filter(p => p.type === backendType);
    if (filtered.length === 0) { toast('Koi jagah nahi mili', 'error'); return; }
    const nearest = filtered.reduce((a, b) => a.distance < b.distance ? a : b);
    await getRouteTo(nearest.lat, nearest.lng, nearest.name);
  } catch(e) {
    console.error('routeToNearestOfType error:', e);
  }
}

function getDistance(loc1, loc2) {
  const R = 6371000;
  const dLat = (loc2.lat - loc1.lat) * Math.PI / 180;
  const dLng = (loc2.lng - loc1.lng) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 + Math.cos(loc1.lat*Math.PI/180)*Math.cos(loc2.lat*Math.PI/180)*Math.sin(dLng/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function placeIcon(type) {
  const icons = {
    hospital:      { url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="14" fill="%23c8102e"/><text x="16" y="21" text-anchor="middle" font-size="16">🏥</text></svg>' },
    restaurant:    { url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="14" fill="%23b45309"/><text x="16" y="21" text-anchor="middle" font-size="16">🍽️</text></svg>' },
    shopping_mall: { url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="14" fill="%230b1d3a"/><text x="16" y="21" text-anchor="middle" font-size="16">🏬</text></svg>' },
    police:        { url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="14" fill="%230b7a74"/><text x="16" y="21" text-anchor="middle" font-size="16">👮</text></svg>' },
  };
  return { url: icons[type]?.url, scaledSize: new google.maps.Size(36, 36) };
}

function placeTypeInfo(type) {
  const m = {
    hospital:      { icon: '🏥', label: 'Hospital',   cls: 'hospital' },
    restaurant:    { icon: '🍽️', label: 'Restaurant', cls: 'restaurant' },
    shopping_mall: { icon: '🏬', label: 'Mall',        cls: 'mall' },
    police:        { icon: '👮', label: 'Police',      cls: 'police' },
  };
  return m[type] || { icon: '📍', label: type, cls: 'hospital' };
}

// Override goTo for map resize + chat init
const _origGoTo = goTo;
window.goTo = function(screen) {
  _origGoTo(screen);
  if (screen === 'map') {
    document.getElementById('place-sheet')?.classList.remove('open');
    if (mapInitialized && map) {
      setTimeout(() => { google.maps.event.trigger(map, 'resize'); if (currentLocation) map.setCenter(currentLocation); }, 100);
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const mapScreen = document.getElementById('screen-map');
  if (mapScreen) {
    const banner = document.createElement('div');
    banner.id = 'route-banner'; banner.className = 'route-banner';
    banner.innerHTML = `<span class="route-info"></span><button class="route-banner-close" onclick="clearRoute()">✕</button>`;
    mapScreen.appendChild(banner);
    mapScreen.addEventListener('click', e => {
      const sheet = document.getElementById('place-sheet');
      if (sheet.classList.contains('open') && !sheet.contains(e.target)) closePlaceSheet();
    });
  }
});

function clearRoute() {
  if (window._routePolyline) { window._routePolyline.setMap(null); window._routePolyline = null; }
  document.getElementById('route-banner')?.classList.remove('show');
}

function mapStyles() {
  return [
    { featureType:'all',            elementType:'geometry',            stylers:[{color:'#f5f5f5'}] },
    { featureType:'road.highway',   elementType:'geometry',            stylers:[{color:'#dadada'}] },
    { featureType:'road.arterial',  elementType:'geometry',            stylers:[{color:'#ffffff'}] },
    { featureType:'road.local',     elementType:'geometry',            stylers:[{color:'#ffffff'}] },
    { featureType:'road',           elementType:'labels.text.fill',    stylers:[{color:'#4a5878'}] },
    { featureType:'water',          elementType:'geometry',            stylers:[{color:'#c8dff5'}] },
    { featureType:'landscape',       elementType:'geometry',            stylers:[{color:'#d5e8d4'}] },
    { featureType:'poi',            elementType:'labels',              stylers:[{visibility:'off'}] },
    { featureType:'transit',        elementType:'labels',              stylers:[{visibility:'off'}] },
    { featureType:'administrative', elementType:'geometry.stroke',     stylers:[{color:'#c0cce0'}] },
    { featureType:'administrative.land_parcel', elementType:'labels',  stylers:[{visibility:'off'}] },
  ];
}

// ══════════════════════════════════════════════════════
//  🎙️ VOICE AGENT — SheShield
//
//  Mic button behaviour:
//    • Single tap  → voice-to-text (speak → text fills input → auto send)
//    • Long press (600ms+) → toggle continuous voice-to-voice mode
//      - Voice mode ON  → mic turns teal, AI replies are also spoken
//      - Voice mode OFF → mic returns to normal
//
//  Language: auto-detected from user speech → TTS replies in same language
// ══════════════════════════════════════════════════════

const voiceAgent = {
  recognition:   null,
  synthesis:     window.speechSynthesis,
  isListening:   false,
  isSpeaking:    false,
  isContinuous:  false,   // voice-to-voice mode
  detectedLang:  'hi-IN', // updated from user speech
  autoListen:    false,
  autoSpeak:     localStorage.getItem('ss_auto_speak') !== '0', // default ON
};

let longPressTimer = null;
let tapHandled    = false;

/* ── Language detection ────────────────────────── */
function detectLang(text) {
  const hindiChars = (text.match(/[\u0900-\u097F]/g) || []).length;
  if (hindiChars > 2) return 'hi-IN';
  const hinglish = /\b(karo|bolo|hai|hoon|hain|kahan|kab|kya|aur|nahi|haan|theek|accha|suno|batao|jaana|raat|subah|shaam|abhi|bahut|bilkul|toh|woh|yeh|mujhe|tumhe|aapko|main|tum|aap|kaise|pyaari|yaar|dost|arre|oye)\b/i;
  if (hinglish.test(text)) return 'hi-IN';
  return 'en-IN';
}

/* ── Browser support check ─────────────────────── */
function checkVoiceSupport() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

/* ── Init recognition ──────────────────────────── */
function initVoiceRecognition() {
  if (voiceAgent.recognition) return;
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;

  const rec = new SR();
  rec.lang = 'hi-IN';
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;

  rec.onstart = () => {
    voiceAgent.isListening = true;
    setMicState('listening');
    setVoiceStatus('🎙️ I am listening...');
  };

  rec.onresult = (e) => {
    let interim = '', final = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t;
      else interim += t;
    }
    const preview = final || interim;
    // Show live transcript in the input box itself
    const inp = document.getElementById('chat-input');
    if (inp) inp.value = preview;
    document.getElementById('voice-transcript-preview').textContent = '';
    if (final) {
      voiceAgent.detectedLang = detectLang(final);
      // Update recognition language for next time
      rec.lang = voiceAgent.detectedLang;
    }
  };

  rec.onend = () => {
    voiceAgent.isListening = false;
    const transcript = (document.getElementById('chat-input')?.value || '').trim();
    document.getElementById('voice-transcript-preview').textContent = '';

    if (transcript) {
      setVoiceStatus('');
      sendChat(); // auto-send
    } else {
      setVoiceStatus('No audio detected — tap again');
      setTimeout(() => setVoiceStatus(''), 2500);
      if (voiceAgent.isContinuous) {
        setTimeout(startListening, 1200);
      }
    }
    if (!voiceAgent.isContinuous) setMicState('idle');
    else setMicState('voice-mode-on');
  };

  rec.onerror = (e) => {
    voiceAgent.isListening = false;
    setMicState(voiceAgent.isContinuous ? 'voice-mode-on' : 'idle');
    const msgs = {
      'no-speech':    '🤫 Nothing say',
      'not-allowed':  '🚫 give Mic permission',
      'audio-capture':'⚠️ Mic not found',
      'network':      '📡 Network error',
    };
    setVoiceStatus(msgs[e.error] || 'Error: ' + e.error);
    setTimeout(() => setVoiceStatus(''), 2500);
  };

  voiceAgent.recognition = rec;
}

/* ── Start / Stop listening ─────────────────────── */
function startListening() {
  if (voiceAgent.isListening) return;
  // Agar TTS bol rahi ho — user ne mic tap kiya matlab "band karo aur suno"
  if (voiceAgent.isSpeaking) {
    stopSpeaking();
    voiceAgent.isSpeaking = false;
    setTimeout(() => startListening(), 200);
    return;
  }
  if (!checkVoiceSupport()) { toast('Browser voice support nahi hai 😔', 'error'); return; }
  initVoiceRecognition();
  try { voiceAgent.recognition.start(); }
  catch(e) { voiceAgent.recognition.stop(); setTimeout(() => voiceAgent.recognition.start(), 300); }
}

function stopListening() {
  if (voiceAgent.recognition && voiceAgent.isListening) voiceAgent.recognition.stop();
}

/* ── Long press logic ───────────────────────────── */
function startLongPress(e) {
  if (e) e.preventDefault();
  tapHandled = false;
  longPressTimer = setTimeout(() => {
    tapHandled = true; // prevent tap from also firing
    toggleVoiceMode(!voiceAgent.isContinuous);
  }, 600);
}

function cancelLongPress() {
  if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
}

/* ── Mic tap (single tap = voice to text) ────────── */
function handleMicTap() {
  if (tapHandled) { tapHandled = false; return; } // was a long press
  if (voiceAgent.isListening) {
    stopListening();
  } else if (voiceAgent.isContinuous) {
    // tap in voice mode = listen once more
    startListening();
  } else {
    startListening();
  }
}

// Legacy compat
function startVoiceInput() { handleMicTap(); }

/* ── Toggle voice-to-voice mode ─────────────────── */
function toggleVoiceMode(enabled) {
  voiceAgent.isContinuous = enabled;
  localStorage.setItem('ss_voice_mode', enabled ? '1' : '0');
  if (enabled) {
    setMicState('voice-mode-on');
    setVoiceStatus('Mic ON ');
    toast('🎙️ Mic Toggle ON ', 'success');
    initVoiceRecognition();
    startListening();
  } else {
    setMicState('idle');
    setVoiceStatus('');
    stopListening();
    stopSpeaking();
    toast('🔇 Mic Toggle OFF', 'info');
  }
  updateMicToggleBtn();
}

/* ── Persistent mic toggle button ───────────────── */
function updateMicToggleBtn() {
  const btn = document.getElementById('btn-mic-toggle');
  if (!btn) return;
  const icon = btn.querySelector('i');
  if (voiceAgent.isContinuous) {
    btn.classList.add('mic-toggle-on');
    btn.title = 'Mic Toggle ON — tap to turn off';
    if (icon) icon.className = 'fas fa-microphone-lines';
    // Agar AI bol rahi hai to "interrupt" hint dikhao
    if (voiceAgent.isSpeaking) {
      btn.title = '🎙️ Bolne ke liye tap karo — AI ruk jaayegi';
    }
  } else {
    btn.classList.remove('mic-toggle-on');
    btn.title = 'Mic Toggle OFF — tap to turn on';
    if (icon) icon.className = 'fas fa-microphone-slash';
  }
}

function injectMicToggleButton() {
  if (document.getElementById('btn-mic-toggle')) return;
  const micBtn = document.getElementById('btn-mic');
  if (!micBtn) return;

  const btn = document.createElement('button');
  btn.id        = 'btn-mic-toggle';
  btn.className = 'mic-toggle-btn';
  btn.title     = 'Mic Toggle — ON karo to baar baar press karna nahi padega';
  btn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
  btn.onclick = () => {
    if (voiceAgent.isContinuous && voiceAgent.isSpeaking) {
      // AI bol rahi hai — interrupt karo
      stopSpeaking();
      startListening();
    } else {
      toggleVoiceMode(!voiceAgent.isContinuous);
    }
  };

  // Style for when toggle is ON
  const style = document.createElement('style');
  style.textContent = `
    #btn-mic-toggle.mic-toggle-on {
      opacity: 1 !important;
      background: var(--teal-light, #00b4d8) !important;
      color: #fff !important;
      box-shadow: 0 0 10px var(--teal-light, #00b4d8);
      animation: mic-pulse 1.6s infinite;
    }
    @keyframes mic-pulse {
      0%,100% { box-shadow: 0 0 6px var(--teal-light, #00b4d8); }
      50%      { box-shadow: 0 0 16px var(--teal-light, #00b4d8); }
    }
  `;
  document.head.appendChild(style);

  micBtn.parentNode.insertBefore(btn, micBtn.nextSibling);
  updateMicToggleBtn();
}

/* ── Mic button visual state ─────────────────────── */
function setMicState(state) {
  const btn  = document.getElementById('btn-mic');
  const icon = document.getElementById('voice-orb-icon');
  if (!btn) return;
  btn.classList.remove('listening', 'voice-mode-on');
  if (state === 'listening') {
    btn.classList.add('listening');
    if (icon) icon.className = 'fas fa-stop';
  } else if (state === 'voice-mode-on') {
    btn.classList.add('voice-mode-on');
    if (icon) icon.className = 'fas fa-microphone-lines';
  } else {
    if (icon) icon.className = 'fas fa-microphone';
  }
}
// alias used elsewhere
function setVoiceOrbState(s) { setMicState(s); }

function setVoiceStatus(msg) {
  const el = document.getElementById('voice-status-text');
  if (el) el.textContent = msg;
}

/* ── Clean text before speaking ─────────────────── */
function cleanTextForSpeech(html) {
  let t = html || '';

  // <br> → pause
  t = t.replace(/<br\s*\/?>/gi, '. ');

  // Strip all HTML tags
  t = t.replace(/<[^>]+>/g, ' ');

  // HTML entities
  t = t.replace(/&amp;/gi, 'and')
       .replace(/&lt;/gi, '')
       .replace(/&gt;/gi, '')
       .replace(/&nbsp;/gi, ' ')
       .replace(/&quot;/gi, '')
       .replace(/&#\d+;/g, '');

  // URLs — don't read them out
  t = t.replace(/https?:\/\/[^\s]+/g, '');

  // Remove ALL emoji / Unicode pictographs
  t = t.replace(/[\u{1F000}-\u{1FFFF}]/gu, '');
  t = t.replace(/[\u{2600}-\u{27BF}]/gu, '');
  t = t.replace(/[\u{FE00}-\u{FE0F}]/gu, '');
  t = t.replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '');
  // Stray emoji that sometimes slip through as multi-byte chars
  t = t.replace(/[^\x00-\x7F\u0900-\u097F\u00C0-\u024F]/g, ' ');

  // Remove markdown bold/italic markers
  t = t.replace(/\*\*/g, '').replace(/\*/g, '');

  // Replace separators / bullets with pauses
  t = t.replace(/[·•|→←]/g, ', ');

  // Collapse whitespace
  t = t.replace(/\s{2,}/g, ' ').replace(/\.{2,}/g, '.').trim();

  return t;
}

/* ── TTS — speak AI reply ───────────────────────── */

// Barge-in: AI bol rahi ho tab bhi user ki awaaz suno
let _bargeInRec = null;

function startBargeIn() {
  if (_bargeInRec) return;
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  try {
    _bargeInRec = new SR();
    _bargeInRec.lang          = voiceAgent.detectedLang || 'hi-IN';
    _bargeInRec.interimResults = true;
    _bargeInRec.continuous     = false;
    _bargeInRec.onresult = () => {
      // User ne bola — AI ko roko, ab user ko suno
      stopBargeIn();
      stopSpeaking();
      setVoiceStatus('🎙️ I am listening..');
      setTimeout(startListening, 150);
    };
    _bargeInRec.onerror = () => { _bargeInRec = null; };
    _bargeInRec.onend   = () => { _bargeInRec = null; };
    _bargeInRec.start();
  } catch(e) { _bargeInRec = null; }
}

function stopBargeIn() {
  if (_bargeInRec) {
    try { _bargeInRec.stop(); } catch(e) {}
    _bargeInRec = null;
  }
}

function speakText(text) {
  if (!window.speechSynthesis) return;
  const clean = cleanTextForSpeech(text);
  if (!clean) return;
  stopBargeIn();
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(clean);
  utt.lang   = voiceAgent.detectedLang || 'hi-IN';
  utt.rate   = 0.95;
  utt.pitch  = 1.05;
  utt.volume = 1;
  const voices = window.speechSynthesis.getVoices();
  const lang0  = utt.lang;
  const best   = voices.find(v => v.lang === lang0)
    || voices.find(v => v.lang.startsWith(lang0.split('-')[0]))
    || null;
  if (best) utt.voice = best;
  utt.onstart = () => {
    voiceAgent.isSpeaking = true;
    setVoiceStatus('🔊 speaking!)');
    updateMicToggleBtn();
    // Continuous mode mein barge-in suno
    if (voiceAgent.isContinuous) setTimeout(startBargeIn, 600);
  };
  utt.onend = () => {
    stopBargeIn();
    voiceAgent.isSpeaking = false;
    setVoiceStatus('');
    updateMicToggleBtn();
    setMicState(voiceAgent.isContinuous ? 'voice-mode-on' : 'idle');
    if (voiceAgent.isContinuous) setTimeout(startListening, 400);
  };
  utt.onerror = () => {
    stopBargeIn();
    voiceAgent.isSpeaking = false;
    updateMicToggleBtn();
    setMicState(voiceAgent.isContinuous ? 'voice-mode-on' : 'idle');
  };
  window.speechSynthesis.speak(utt);
}

function stopSpeaking() {
  voiceAgent.autoListen = false;
  stopBargeIn();
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  voiceAgent.isSpeaking = false;
  updateMicToggleBtn();
  setMicState(voiceAgent.isContinuous ? 'voice-mode-on' : 'idle');
}

// Load voices
if (window.speechSynthesis) window.speechSynthesis.getVoices();

/* ── Auto-Speak toggle ─────────────────────────── */
function toggleAutoSpeak() {
  voiceAgent.autoSpeak = !voiceAgent.autoSpeak;
  localStorage.setItem('ss_auto_speak', voiceAgent.autoSpeak ? '1' : '0');
  const btn = document.getElementById('btn-auto-speak');
  if (btn) {
    btn.title   = voiceAgent.autoSpeak ? 'Auto-speak ON (tap to turn off)' : 'Auto-speak OFF (tap to turn on)';
    btn.style.opacity = voiceAgent.autoSpeak ? '1' : '0.4';
    btn.querySelector('i').className = voiceAgent.autoSpeak ? 'fas fa-volume-up' : 'fas fa-volume-xmark';
  }
  if (!voiceAgent.autoSpeak) stopSpeaking();
  toast(voiceAgent.autoSpeak ? '🔊 Auto-speak ON' : '🔇 Auto-speak OFF');
}

function injectAutoSpeakButton() {
  // Add speaker toggle button next to the reset/mic buttons in chat header
  const existing = document.getElementById('btn-auto-speak');
  if (existing) return;
  // Find the chat action area — look for btn-reset-chat
  const resetBtn = document.getElementById('btn-reset-chat');
  if (!resetBtn) return;
  const btn = document.createElement('button');
  btn.id        = 'btn-auto-speak';
  btn.className = resetBtn.className; // same style
  btn.title     = voiceAgent.autoSpeak ? 'Auto-speak ON (tap to turn off)' : 'Auto-speak OFF (tap to turn on)';
  btn.style.opacity = voiceAgent.autoSpeak ? '1' : '0.4';
  btn.innerHTML = `<i class="${voiceAgent.autoSpeak ? 'fas fa-volume-up' : 'fas fa-volume-xmark'}"></i>`;
  btn.onclick   = toggleAutoSpeak;
  resetBtn.parentNode.insertBefore(btn, resetBtn.nextSibling);
}

/* ── Patch appendAIMessage to also SPEAK in voice mode ── */
const _origAppendAIMsg = typeof appendAIMessage === 'function' ? appendAIMessage : null;
if (_origAppendAIMsg) {
  // noSpeak = true pass karo to silent rahega (e.g. greeting)
  window.appendAIMessage = function(html, noSpeak = false) {
    _origAppendAIMsg(html);
    if (!noSpeak && (voiceAgent.isContinuous || voiceAgent.autoSpeak)) speakText(html);
  };
}

// Inject speaker button once DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(injectAutoSpeakButton, 500);
});

if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}