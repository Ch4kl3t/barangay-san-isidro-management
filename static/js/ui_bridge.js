/* Functional compatibility only. No style overrides, chart replacement or layout changes. */
window.uiEscape = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
window.uiRegex = value => String(value).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
(() => {
 const original=window.fetch.bind(window);
 window.fetch=(input,init={})=>{
  const url=new URL(typeof input==='string'?input:input.url,location.href),headers=new Headers(init.headers||(input instanceof Request?input.headers:undefined));
  if(url.origin===location.origin)headers.set('X-CSRF-Token',document.querySelector('meta[name="csrf-token"]')?.content||'');
  return original(input,{...init,headers});
 };
 document.addEventListener('click',event=>{
  const anchor=event.target.closest('a[href]');if(!anchor)return;
  const target=new URL(anchor.href,location.href);
  if(target.origin!==location.origin||!/^\/(logout|delete_member\/\d+|delete_household\/\d+)$/.test(target.pathname))return;
  event.preventDefault();event.stopImmediatePropagation();
  const form=document.createElement('form');form.method='POST';form.action=target.href;
  const token=document.createElement('input');token.type='hidden';token.name='csrf_token';token.value=document.querySelector('meta[name="csrf-token"]')?.content||'';
  form.append(token);document.body.append(form);HTMLFormElement.prototype.submit.call(form);
 },true);
 document.addEventListener('DOMContentLoaded',()=>{
  const birth=document.querySelector('input[name="birthdate"]'),age=document.querySelector('input[name="age"]');
  function updateAge(){
   if(!birth||!age)return;
   const parts=birth.value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
   if(!parts||!birth.validity.valid){age.value='';return;}
   const [year,month,day]=parts.slice(1).map(Number),born=new Date(Date.UTC(year,month-1,day));
   const dateParts=new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Manila',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
   const current=Object.fromEntries(dateParts.map(p=>[p.type,p.value]));
   const reference=[Number(current.year),Number(current.month),Number(current.day)];
   if(born.getUTCFullYear()!==year||born.getUTCMonth()!==month-1||born.getUTCDate()!==day||born.getTime()>Date.UTC(reference[0],reference[1]-1,reference[2])){age.value='';return;}
   age.value=reference[0]-year-((reference[1]<month||(reference[1]===month&&reference[2]<day))?1:0);
  }
  birth?.addEventListener('input',updateAge);birth?.addEventListener('change',updateAge);updateAge();
 });
})();

/* Native POST busy state and keyboard behavior for the retained custom modals. */
(() => {
 const reset=()=>document.querySelectorAll('form[data-busy]').forEach(form=>{delete form.dataset.busy;form.querySelectorAll('[data-submit-busy]').forEach(b=>{b.disabled=false;b.removeAttribute('aria-disabled');delete b.dataset.submitBusy;});const confirm=document.getElementById('confirm');if(confirm)confirm.disabled=false;});
 window.addEventListener('pageshow',reset);
 document.addEventListener('submit',event=>{const form=event.target;if(form.method.toLowerCase()!=='post')return;if(form.dataset.busy){event.preventDefault();return;}queueMicrotask(()=>{if(event.defaultPrevented)return;form.dataset.busy='yes';form.querySelectorAll('button[type=submit],input[type=submit]').forEach(b=>{b.dataset.submitBusy='yes';b.disabled=true;b.setAttribute('aria-disabled','true');});if(form.closest('.resident-editor')){const confirm=document.getElementById('confirm');if(confirm)confirm.disabled=true;}});});
 let lastControl=null,active=null;
 document.addEventListener('click',e=>{lastControl=e.target.closest('button,a')||lastControl;},true);
 const modals=[...document.querySelectorAll('.modal-overlay')];
 for(const modal of modals){const heading=modal.querySelector('h2,h3');if(heading){if(!heading.id)heading.id=modal.id+'Title';modal.setAttribute('aria-labelledby',heading.id);}modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.tabIndex=-1;
  new MutationObserver(()=>{const visible=getComputedStyle(modal).display!=='none';if(visible&&active?.modal!==modal){active={modal,opener:lastControl||document.activeElement};const first=modal.querySelector('button:not([disabled]),a[href]');(first||modal).focus();}else if(!visible&&active?.modal===modal){const opener=active.opener;active=null;opener?.focus({preventScroll:true});}}).observe(modal,{attributes:true,attributeFilter:['style','class']});
 }
 document.addEventListener('keydown',event=>{if(!active)return;const modal=active.modal;if(event.key==='Escape'){event.preventDefault();modal.style.display='none';return;}if(event.key==='Tab'){const fields=[...modal.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),[tabindex="0"]')].filter(e=>e.getClientRects().length);if(!fields.length){event.preventDefault();modal.focus();return;}const first=fields[0],last=fields[fields.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}});
})();
