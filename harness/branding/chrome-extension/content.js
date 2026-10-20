(()=>{'use strict';
if(!['127.0.0.1','localhost'].includes(location.hostname)||location.port!=='3080')return;
const url=chrome.runtime.getURL('ultron-logo.svg');
const titlePattern=/DeepSeek Harness/gi;
function updateTitle(){
  const t=document.title||'';
  const n=t.replace(titlePattern,'Ultron');
  if(n!==t)document.title=n;
  const h=document.querySelector('link[rel~="icon"]');
  if(h&&h.href!==url)h.href=url;
  if(!h){const l=document.createElement('link');l.rel='icon';l.type='image/svg+xml';l.href=url;document.head?.append(l);}
}
function brand(){
  if(!document.body)return;
  let replaced=false;
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  let n;
  while(n=walker.nextNode()){
    const value=n.textContent?.trim();
    if(!value||!['DeepSeek Harness','DEEPSEEK','DeepSeek'].includes(value))continue;
    const el=n.parentElement;
    if(!el||el.closest('[id^="ultron-brand"]'))continue;
    const b=el.getBoundingClientRect();
    if(b.top<0||b.top>190||b.left>390)continue;
    n.textContent=n.textContent.replace(value,'ULTRON');
    const host=el.parentElement;
    if(host&&!host.querySelector('[data-ultron-emblem]')){
      const logo=document.createElement('img');
      logo.src=url;logo.alt='Ultron emblem';logo.dataset.ultronEmblem='true';logo.style.cssText='width:26px;height:26px;object-fit:contain;vertical-align:middle;margin-right:8px';
      el.prepend(logo);
    }
    replaced=true;
  }
  // Visual fallback if upstream redesign changes the brand DOM.
  const fallback=document.getElementById('ultron-brand-floating');
  if(!replaced&&!document.querySelector('[data-ultron-emblem]')&&!fallback){
    const chip=document.createElement('div');chip.id='ultron-brand-floating';
    const img=document.createElement('img');img.src=url;img.alt='';
    const text=document.createElement('span');text.textContent='ULTRON';
    chip.append(img,text);document.body.append(chip);
  }
  if((replaced||document.querySelector('[data-ultron-emblem]'))&&fallback)fallback.remove();
}
let queued=false;
function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;updateTitle();brand()})}
new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true,characterData:true});
schedule();window.addEventListener('load',schedule);
})();
