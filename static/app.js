const messages = [];
const form = document.getElementById('form');
const input = document.getElementById('prompt');
const send = document.getElementById('send');
const area = document.getElementById('messages');
let busy = false;
function append(role, content) {
  const welcome = area.querySelector('.welcome'); if (welcome) welcome.remove();
  const div = document.createElement('div'); div.className = 'message ' + role;
  // Render plain text safely; preserve newlines through CSS. No untrusted HTML insertion.
  div.textContent = content; area.appendChild(div); area.scrollTop = area.scrollHeight;
  return div;
}
form.addEventListener('submit', async e => {
  e.preventDefault(); if (busy || !input.value.trim()) return;
  const text = input.value.trim(); input.value = '';
  messages.push({role:'user', content:text}); append('user', text);
  busy = true; send.disabled = true; const pending = append('assistant', 'Thinking…');
  try {
    const response = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({messages:messages.slice(-20)})});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed');
    pending.textContent = data.reply; messages.push({role:'assistant',content:data.reply});
  } catch (err) {pending.className = 'message error'; pending.textContent = 'Could not get a reply: ' + err.message;}
  finally {busy = false; send.disabled = false; input.focus(); area.scrollTop = area.scrollHeight;}
});
input.addEventListener('keydown', e => {if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {e.preventDefault(); form.requestSubmit();}});
document.getElementById('clear').addEventListener('click', () => {if(busy)return; messages.length=0;area.replaceChildren(); const welcome=document.createElement('div');welcome.className='welcome';welcome.textContent='Chat cleared. Refreshing also clears this session.';area.appendChild(welcome);});
