'use strict';
const $=id=>document.getElementById(id);
const display=msg=>{const div=document.createElement('div');div.className='message assistant';div.textContent=msg;$('messages').append(div);div.scrollIntoView({block:'nearest'});return div;};
let sessionId=null,running=false;
async function request(url,method='GET',body=null){const r=await fetch(url,{method,credentials:'same-origin',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Request failed');return j;}
async function status(){const d=await request('/api/dsh/status');$('login-section').hidden=d.authenticated;$('agent-section').hidden=!d.authenticated;$('logout').hidden=!d.authenticated;if(!d.configured)$('login-status').textContent='Private password and session secret must be configured.';}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();try{await request('/api/dsh/login','POST',{password:$('password').value});$('password').value='';$('login-status').textContent='';await status();}catch(err){$('login-status').textContent=err.message;}});
$('logout').addEventListener('click',async()=>{await request('/api/dsh/logout','POST',{});sessionId=null;await status();});
$('agent-form').addEventListener('submit',async e=>{
e.preventDefault();if(running)return;const prompt=$('agent-prompt').value.trim();if(!prompt)return;
running=true;$('agent-send').disabled=true;$('agent-prompt').value='';display('You: '+prompt);const pending=display('Agent is working…');
try{
const resp=await fetch('/api/dsh/run',{method:'POST',headers:{'Content-Type':'application/json','Accept':'text/event-stream'},credentials:'same-origin',body:JSON.stringify({prompt,session_id:sessionId})});
if(!resp.ok){let data={};try{data=await resp.json();}catch(_){}throw new Error(data.detail||'Agent request failed');}
const reader=resp.body.getReader(),decoder=new TextDecoder();let buffer='',completed=false;
function handle(block){
let kind='',data='';for(const line of block.split(/\r?\n/)){if(line.startsWith('event:'))kind=line.slice(6).trim();if(line.startsWith('data:'))data+=line.slice(5).trimStart();}
if(!data)return;const msg=JSON.parse(data);if(kind==='activity')pending.textContent='Agent: '+msg.event;
if(kind==='finished'){sessionId=msg.session_id;pending.textContent=msg.answer;completed=true;}
if(kind==='error')throw new Error(msg.message);
}
while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const parts=buffer.split(/\r?\n\r?\n/);buffer=parts.pop();for(const part of parts)handle(part);}
if(!completed)throw new Error('Connection closed before completion');
}catch(err){pending.textContent='Agent error: '+err.message;}
finally{running=false;$('agent-send').disabled=false;}
});
const audio=$('greeting-audio'),toggle=$('voice-toggle');let voice=localStorage.getItem('dsh_voice')!=='off';function sync(){toggle.textContent=voice?'Voice: On':'Voice: Off';$('welcome-audio').hidden=!voice;}
async function play(){try{audio.currentTime=0;await audio.play();}catch(_){$('welcome-audio').textContent='▶ Tap to hear greeting';}}
$('welcome-audio').addEventListener('click',play);
toggle.addEventListener('click',()=>{voice=!voice;localStorage.setItem('dsh_voice',voice?'on':'off');if(!voice)audio.pause();else play();sync();});
sync();status().catch(e=>{$('login-status').textContent=e.message;});if(voice)window.addEventListener('load',play);
