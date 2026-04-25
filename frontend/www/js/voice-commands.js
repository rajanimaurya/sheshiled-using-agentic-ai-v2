/* ═══════════════════════════════════════════════════════════════════════════
   SHESHIELD — VOICE COMMANDS + AUTO-CLOSE SOS

   Features:
   ✓ App kholne par TURANT secret code sunna shuru — bina kuch press kiye
   ✓ User ka saved secret code backend se load karta hai (hardcoded nahi)
   ✓ Secret code bola → SOS silently trigger hoti hai
   ✓ Auto-close SOS after 30 seconds (with countdown)
   ✓ Manual close SOS button
   ═══════════════════════════════════════════════════════════════════════════ */


// ─────────────────────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────────────────────

const voiceState = {
  listening:   false,
  secretCode:  null,       // null jab tak backend se load na ho
  isSpeaking:  false,
  recognition: null,
  started:     false       // ek baar se zyada start na ho
};

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;


// ─────────────────────────────────────────────────────────────────────────────
// SECRET CODE — BACKEND SE LOAD KARO
// ─────────────────────────────────────────────────────────────────────────────

/**
 * User ka saved secret code fetch karo aur voiceState mein set karo.
 * app.js ka `api()` function use karta hai.
 */
async function loadVoiceSecretCode() {
  try {
    const data = await api('GET', '/api/v1/users/me/secret-code', null, true);
    if (data && data.secret_code) {
      voiceState.secretCode = data.secret_code.trim().toLowerCase();
      console.log('🔐 Voice secret code loaded:', voiceState.secretCode);
    } else {
      console.log('ℹ️ No secret code set by user yet');
    }
  } catch (e) {
    console.warn('Could not load secret code:', e);
  }
}


// ─────────────────────────────────────────────────────────────────────────────
// VOICE LISTENER
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Microphone sunna shuru karo.
 * Yeh continuously background mein chalta rehta hai.
 */
function startVoiceCommandListener() {
  if (!SpeechRecognition) {
    console.warn('⚠️ Speech Recognition not supported in this browser.');
    return;
  }

  // Already chalu hai to dobara mat shuru karo
  if (voiceState.started && voiceState.listening) return;
  voiceState.started = true;

  const recognition = new SpeechRecognition();
  recognition.continuous      = true;
  recognition.interimResults  = true;
  recognition.lang            = 'hi-IN';   // Hindi + English dono samjhega

  voiceState.recognition = recognition;

  recognition.onstart = () => {
    voiceState.listening = true;
    console.log('🎤 Voice listener active — background mein sun raha hoon...');
  };

  recognition.onresult = (event) => {
    // Secret code set nahi hua to kuch mat karo
    if (!voiceState.secretCode) return;

    let finalTranscript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript.toLowerCase();
      }
    }

    if (finalTranscript && finalTranscript.includes(voiceState.secretCode)) {
      console.log('🚨 SECRET CODE SUNA! SOS trigger ho raha hai...');
      triggerSOSByVoice();
    }
  };

  recognition.onerror = (event) => {
    voiceState.started = false;
    // no-speech normal hai — ignore karo
    if (event.error === 'no-speech') return;
    console.warn('⚠️ Voice error:', event.error);
  };

  recognition.onend = () => {
    voiceState.listening = false;
    voiceState.started   = false;
    // Automatically restart — hamesha sunta rahe
    setTimeout(startVoiceCommandListener, 1000);
  };

  try {
    recognition.start();
  } catch (e) {
    voiceState.started = false;
    console.warn('Voice start error:', e);
    setTimeout(startVoiceCommandListener, 2000);
  }
}


// ─────────────────────────────────────────────────────────────────────────────
// TTS — USER KO FEEDBACK
// ─────────────────────────────────────────────────────────────────────────────

function speakFeedback(text) {
  if (!('speechSynthesis' in window)) return;
  const u  = new SpeechSynthesisUtterance(text);
  u.rate   = 1;
  u.pitch  = 1;
  u.volume = 0.7;
  u.lang   = 'en-US';
  u.onend  = () => { voiceState.isSpeaking = false; };
  voiceState.isSpeaking = true;
  speechSynthesis.speak(u);
}


// ─────────────────────────────────────────────────────────────────────────────
// VOICE SOS TRIGGER
// ─────────────────────────────────────────────────────────────────────────────

async function triggerSOSByVoice() {
  console.log('🚨 Voice SOS firing...');

  // Screen pe koi SOS indicator nahi — SILENT trigger
  // Sirf ek bahut subtle vibration
  if (navigator.vibrate) navigator.vibrate([200, 100, 200]);

  // app.js ka triggerSOS wait karke call karo
  let attempts = 0;
  while (typeof window._originalTriggerSOS !== 'function' &&
         typeof window.triggerSOS !== 'function' &&
         attempts < 30) {
    await new Promise(r => setTimeout(r, 200));
    attempts++;
  }

  const fn = window._originalTriggerSOS || window.triggerSOS;
  if (typeof fn === 'function') {
    await fn.call(window);
  } else {
    console.error('❌ triggerSOS not found');
  }
}


// ─────────────────────────────────────────────────────────────────────────────
// AUTO-CLOSE SOS
// ─────────────────────────────────────────────────────────────────────────────

const sosAutoClose = {
  active:            false,
  timer:             null,
  countdownInterval: null,
  delayMs:           30000
};


/** Alerts bhejne ke baad call karo — 30s countdown shuru hoga */
function enableAutoCloseSOS() {
  if (sosAutoClose.active) return;
  sosAutoClose.active = true;

  console.log('⏱️ SOS auto-close in 30s...');
  _showCountdownBanner();

  sosAutoClose.timer = setTimeout(() => {
    if (sosAutoClose.active) _doCloseSOS();
  }, sosAutoClose.delayMs);
}


/** User ne "Close Now" dabaya */
async function manualCloseSOS() {
  if (!confirm('SOS band karo?')) return;
  _doCloseSOS();
}


/** Internal — sab kuch clean karo */
async function _doCloseSOS() {
  sosAutoClose.active = false;
  clearTimeout(sosAutoClose.timer);
  clearInterval(sosAutoClose.countdownInterval);

  const banner = document.getElementById('sos-countdown-banner');
  if (banner) banner.remove();

  // Live tracking band karo
  try {
    if (typeof liveTrackingState !== 'undefined' && liveTrackingState.isActive) {
      await api('POST', '/api/v1/live/end', {}, true);
    }
  } catch (_) {}

  // SOS overlay band karo
  if (typeof closeSOS === 'function') {
    closeSOS();
  } else {
    const ov = document.getElementById('sos-overlay');
    if (ov) ov.classList.remove('active');
  }

  if (typeof showAlert === 'function') showAlert('✅ Safe hain aap. SOS band hua.', 'success');
  setTimeout(() => { if (typeof goTo === 'function') goTo('home'); }, 2000);
}


/** Countdown banner — top-right mein subtle */
function _showCountdownBanner() {
  const old = document.getElementById('sos-countdown-banner');
  if (old) old.remove();

  const b = document.createElement('div');
  b.id = 'sos-countdown-banner';
  b.className = 'sos-countdown-banner';
  b.innerHTML = `
    <span>⏱️ <span id="sos-countdown-sec">30</span>s</span>
    <button onclick="manualCloseSOS()" class="sos-countdown-close">Close</button>
  `;
  document.body.appendChild(b);

  let rem = 30;
  sosAutoClose.countdownInterval = setInterval(() => {
    rem--;
    const el = document.getElementById('sos-countdown-sec');
    if (el) el.textContent = rem;
    if (rem <= 0) {
      clearInterval(sosAutoClose.countdownInterval);
      b.remove();
    }
  }, 1000);
}


// ─────────────────────────────────────────────────────────────────────────────
// triggerSOS PATCH — auto-close add karo
// ─────────────────────────────────────────────────────────────────────────────

function _patchTriggerSOS() {
  if (window._originalTriggerSOS) return;   // already patched
  if (typeof window.triggerSOS !== 'function') return;

  window._originalTriggerSOS = window.triggerSOS;

  window.triggerSOS = async function (...args) {
    await window._originalTriggerSOS.apply(this, args);
    setTimeout(() => {
      const hasContacts = typeof state !== 'undefined' &&
                          Array.isArray(state.contacts) &&
                          state.contacts.length > 0;
      if (hasContacts) enableAutoCloseSOS();
    }, 1500);
  };

  console.log('✅ triggerSOS patched with auto-close');
}


// ─────────────────────────────────────────────────────────────────────────────
// INIT — APP KHOLNE PAR TURANT SHURU
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Jab app.js ready ho jaye:
 * 1. triggerSOS patch karo
 * 2. Secret code backend se load karo
 * 3. Voice listener shuru karo
 */
async function _initVoiceSystem() {
  // triggerSOS available hone tak wait karo
  let attempts = 0;
  while (typeof window.triggerSOS !== 'function' && attempts < 50) {
    await new Promise(r => setTimeout(r, 200));
    attempts++;
  }

  _patchTriggerSOS();
  await loadVoiceSecretCode();
  startVoiceCommandListener();
}

// DOM ready hote hi shuru karo
document.addEventListener('DOMContentLoaded', () => {
  console.log('🎤 Voice system initialising...');
  _initVoiceSystem();
});
