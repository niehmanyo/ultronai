const messages = [];
const form = document.getElementById('form');
const input = document.getElementById('prompt');
const send = document.getElementById('send');
const stop = document.getElementById('stop');
const area = document.getElementById('messages');
let busy = false, controller = null;
function append(role, content) {
  const welcome = area.querySelector('.welcome'); if (welcome) welcome.remove();
  const div = document.createElement('div'); div.className = 'message ' + role;
  div.textContent = content; area.appendChild(div); area.scrollTop = area.scrollHeight;
  return div;
}
function consumeFrames(buffer, onEvent) {
  const chunks = buffer.split(/\r?\n\r?\n/);
  const tail = chunks.pop();
  for (const block of chunks) {
    let type = 'message', data = '';
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) type = line.slice(6).trim();
      if (line.startsWith('data:')) data += line.slice(5).trimStart();
    }
    if (data) onEvent(type, JSON.parse(data));
  }
  return tail;
}
form.addEventListener('submit', async e => {
  e.preventDefault();
  if (busy || !input.value.trim()) return;
  const text = input.value.trim(); input.value = '';
  messages.push({role:'user', content:text}); append('user', text);
  busy = true; send.disabled = true; stop.hidden = false; controller = new AbortController();
  const pending = append('assistant', 'Thinking…');
  let textSoFar = '', streamDone = false;
  try {
    const response = await fetch('/api/chat/stream', {
      method:'POST', headers:{'Content-Type':'application/json', 'Accept':'text/event-stream'},
      body:JSON.stringify({messages:messages.slice(-20)}), signal:controller.signal
    });
    if (!response.ok) {
      let detail = 'Request failed';
      try { const err = await response.json(); detail = typeof err.detail === 'string' ? err.detail : detail; } catch (_) {}
      throw new Error(detail);
    }
    if (!response.body) throw new Error('Streaming not supported by this browser');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    const handleEvent = (type, payload) => {
      if (type === 'delta') {
        textSoFar += payload.text;
        pending.textContent = textSoFar;
        area.scrollTop = area.scrollHeight;
      } else if (type === 'done') streamDone = true;
      else if (type === 'error') throw new Error(payload.message || 'AI service error');
    };
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      buffer = consumeFrames(buffer + decoder.decode(value, {stream:true}), handleEvent);
    }
    buffer = consumeFrames(buffer + decoder.decode(), handleEvent);
    if (!streamDone) throw new Error('Connection ended before completion');
    if (!textSoFar) throw new Error('AI returned an empty response');
    messages.push({role:'assistant', content:textSoFar});
  } catch(err) {
    const cancelled = err.name === 'AbortError';
    if (textSoFar) {
      pending.textContent = textSoFar + (cancelled ? '\n[Stopped]' : '\n[Incomplete response]');
      pending.classList.add('incomplete');
    } else {
      pending.className = 'message error';
      pending.textContent = cancelled ? 'Generation stopped.' : 'Could not get a reply: ' + err.message;
    }
    // Do not send unfinished assistant turns back as trusted chat history.
    // Remove the last user turn too, so a retry starts a consistent conversation.
    if (messages.at(-1)?.role === 'user') messages.pop();
    input.value = text;
  } finally {
    busy = false; send.disabled = false; stop.hidden = true; controller = null;
    input.focus(); area.scrollTop = area.scrollHeight;
  }
});
stop.addEventListener('click', () => { if (controller) controller.abort(); });
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }});
document.getElementById('clear').addEventListener('click', () => {
  if (busy) return;
  messages.length = 0; area.replaceChildren();
  const welcome = document.createElement('div'); welcome.className = 'welcome';
  welcome.textContent = 'Chat cleared. Refreshing also clears this session.'; area.appendChild(welcome);
});

// The greeting uses a bundled WAV. Never spend OpenAI API credits on page loads.
// Browsers often refuse unprompted audio; keep a visible user-gesture fallback.
const greeting = document.getElementById('greeting-audio');
const voiceToggle = document.getElementById('voice-toggle');
const voiceButton = document.getElementById('welcome-audio');
const VOICE_PREF = 'ultron_welcome_voice_enabled';
let voiceEnabled = true;
try { voiceEnabled = localStorage.getItem(VOICE_PREF) !== 'false'; } catch (_) {}
function syncVoiceControls() {
  voiceToggle.textContent = voiceEnabled ? 'Voice: On' : 'Voice: Off';
  voiceToggle.setAttribute('aria-pressed', String(voiceEnabled));
  voiceButton.hidden = !voiceEnabled;
}
async function playWelcome() {
  if (!voiceEnabled) return;
  voiceButton.textContent = '▶ Play greeting';
  try {
    greeting.pause(); greeting.currentTime = 0;
    await greeting.play();
    voiceButton.textContent = '↻ Replay greeting';
  } catch (_) {
    voiceButton.textContent = '▶ Tap to hear Hello Stark';
    voiceButton.hidden = false;
  }
}
greeting.addEventListener('error', () => {
  voiceButton.textContent = 'Audio unavailable';
  voiceButton.title = 'Unable to load greeting audio';
});
voiceToggle.addEventListener('click', () => {
  voiceEnabled = !voiceEnabled;
  try { localStorage.setItem(VOICE_PREF, String(voiceEnabled)); } catch (_) {}
  if (!voiceEnabled) greeting.pause();
  syncVoiceControls();
  if (voiceEnabled) playWelcome();
});
voiceButton.addEventListener('click', playWelcome);
syncVoiceControls();
window.addEventListener('load', () => { if (voiceEnabled) playWelcome(); });
