/* One feedback surface; no storage, polling, HTML evaluation or focus on arrival. */
(() => {
 if(window.officeToast)return;
 const active=new Map(),seenEvents=new Set(),states=new Set();
 const reduced=()=>window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
 const aliases={danger:'error',resident_registered:'success',household_registered:'success',household_head_success:'success',household_head_error:'error'};
 const normalize=type=>Object.hasOwn(aliases,type)?aliases[type]:['success','error','warning','info'].includes(type)?type:'info';
 let region=document.querySelector('[data-toast-region]');
 function container(){if(!region){region=document.createElement('section');region.className='toast-region';region.setAttribute('data-toast-region','');region.setAttribute('aria-label','Notifications');document.body.append(region);}return region;}
 function pause(state){if(state.timer){clearTimeout(state.timer);state.timer=null;state.remaining=Math.max(0,state.remaining-(Date.now()-state.started));}}
 function resume(state){if(!state.closed&&!state.hover&&!state.focus&&!document.hidden&&state.remaining!==null&&!state.timer){state.started=Date.now();state.timer=setTimeout(()=>dismiss(state),state.remaining);}}
 function dismiss(state,manual=false,immediate=false){
  if(state.closed)return;state.closed=true;pause(state);active.delete(state.key);
  const returnFocus=manual&&state.el.contains(document.activeElement);
  const remove=()=>{states.delete(state);state.el.remove();if(returnFocus){const target=container().querySelector('[data-toast-close]')||state.returnFocus;if(target?.isConnected)target.focus({preventScroll:true});}};
  if(immediate||reduced())remove();else{state.el.classList.add('toast-leave');state.exitTimer=setTimeout(remove,160);}
 }
 function mount(el,key){
  if(el.dataset.toastMounted)return el;
  const type=normalize(el.dataset.toastType),message=el.querySelector('.app-toast-message').textContent;
  key=key||type+'\u0000'+message;
  if(active.has(key)){el.remove();return active.get(key).el;}
  el.dataset.toastMounted='yes';
  const state={el,key,remaining:['success','info'].includes(type)?4800:null,timer:null,started:0,hover:false,focus:false,closed:false,returnFocus:document.activeElement};
  active.set(key,state);states.add(state);
  el.querySelector('[data-toast-close]').addEventListener('click',()=>dismiss(state,true));
  el.addEventListener('mouseenter',()=>{state.hover=true;pause(state);});el.addEventListener('mouseleave',()=>{state.hover=false;resume(state);});
  el.addEventListener('focusin',event=>{if(event.relatedTarget&&!el.contains(event.relatedTarget))state.returnFocus=event.relatedTarget;state.focus=true;pause(state);});el.addEventListener('focusout',event=>{if(!el.contains(event.relatedTarget)){state.focus=false;resume(state);}});
  if(!reduced()){el.classList.add('toast-enter');requestAnimationFrame(()=>el.classList.remove('toast-enter'));}
  resume(state);return el;
 }
 function show(message,options={}){
  if(typeof message!=='string'||!message.trim())return null;
  if(!options||typeof options!=='object')options={};
  const type=normalize(options.type),key=options.key||type+'\u0000'+message;
  if(options.key&&seenEvents.has(options.key))return active.get(key)?.el||null;
  if(active.has(key))return active.get(key).el;
  if(options.key)seenEvents.add(options.key);
  const el=document.createElement('div');el.className='app-toast app-toast--'+type;el.dataset.toastType=type;el.setAttribute('data-toast','');
  el.setAttribute('role',['error','warning'].includes(type)?'alert':'status');el.setAttribute('aria-live',['error','warning'].includes(type)?'assertive':'polite');el.setAttribute('aria-atomic','true');
  const icon=document.createElement('span');icon.className='app-toast-icon';icon.setAttribute('aria-hidden','true');
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.8');svg.setAttribute('stroke-linecap','round');
  const circle=document.createElementNS(svg.namespaceURI,'circle');circle.setAttribute('cx','12');circle.setAttribute('cy','12');circle.setAttribute('r','9');
  const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',{success:'m8 12 3 3 5-6',error:'m9 9 6 6m0-6-6 6',warning:'M12 7v6m0 4h.01',info:'M12 11v6m0-10h.01'}[type]);svg.append(circle,path);icon.append(svg);
  const body=document.createElement('span');body.className='app-toast-message';body.textContent=message;
  const close=document.createElement('button');close.type='button';close.className='app-toast-close';close.setAttribute('data-toast-close','');close.setAttribute('aria-label','Dismiss '+type+' notification');close.textContent='×';
  el.append(icon,body,close);container().append(el);return mount(el,key);
 }
 window.officeToast=show;
 // Compatibility for existing failure callers; confirmations keep their own dialogs.
 window.officeFeedback=(title,message)=>show(message||title,{type:'error'});
 for(const el of document.querySelectorAll('[data-toast]'))mount(el);
 document.addEventListener('visibilitychange',()=>{for(const state of states)document.hidden?pause(state):resume(state);});
 window.addEventListener('pageshow',event=>{if(event.persisted)for(const state of [...states]){pause(state);clearTimeout(state.exitTimer);state.closed=true;active.delete(state.key);states.delete(state);state.el.remove();}});
})();
