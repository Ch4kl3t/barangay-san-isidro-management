/* Record registration only: native POST remains available; issued server intents prevent replay writes. */
(() => {
 function mount(){
  const dialog=document.getElementById('recordRegistrationSuccess');
  if(dialog&&!dialog.dataset.mounted){
   dialog.dataset.mounted='yes';
   // Place the fixed overlay outside any transformed page container, and keep
   // keyboard/pointer access within it until the confirmation is dismissed.
   document.body.append(dialog);
   const previousOverflow=document.body.style.overflow;
   document.body.style.overflow='hidden';
   const background=[...document.body.children].filter(element=>element!==dialog&&!element.inert);
   background.forEach(element=>{element.inert=true;});
   const focusable=[...dialog.querySelectorAll('a[href],button:not([disabled])')];
   const close=()=>{dialog.hidden=true;dialog.style.display='none';background.forEach(element=>{element.inert=false;});document.body.style.overflow=previousOverflow;const heading=document.querySelector('main h1');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}};
   dialog.querySelector('[data-registration-close]').addEventListener('click',close);
   dialog.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();close();return;}
    if(event.key==='Tab'&&focusable.length){const first=focusable[0],last=focusable[focusable.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}
   });
   dialog.querySelector('[data-registration-primary]').focus();
  }
  const form=document.querySelector('form[data-record-registration]');
  if(!form||form.dataset.registrationEnhanced||!window.fetch||!window.FormData)return;
  form.dataset.registrationEnhanced='yes';
  const kind=form.dataset.recordRegistration,plural=kind==='household'?'Households':'Residents';
  const buttons=[...form.querySelectorAll('button[type=submit],input[type=submit]')];
  const notice=document.createElement('p');notice.className='registration-submit-status';notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');form.querySelector('.form-actions').before(notice);
  let busy=false;
  const reset=()=>{busy=false;form.removeAttribute('aria-busy');buttons.forEach(button=>{button.disabled=false;button.removeAttribute('aria-disabled');});notice.textContent='';};
  window.addEventListener('pageshow',reset);
  function error(message,recovery=false){
   reset();document.getElementById('errorText').textContent=message;
   const recoveryLink=document.getElementById('registrationRecoveryLink');if(recoveryLink)recoveryLink.hidden=!recovery;
   document.getElementById('errorModal').style.display='flex';
  }
  form.addEventListener('submit',async event=>{
   if(new FormData(form).get('action')==='new_household')return;
   event.preventDefault();if(busy)return;
   const body=new FormData(form);busy=true;form.setAttribute('aria-busy','true');buttons.forEach(button=>{button.disabled=true;button.setAttribute('aria-disabled','true');});notice.textContent=`Saving ${kind} record...`;
   const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
   try{
    const response=await fetch(form.action,{method:'POST',body,headers:{Accept:'application/json'},credentials:'same-origin',signal:controller.signal});
    if(!response.headers.get('Content-Type')?.includes('application/json')){error(response.status===400?'The form expired or was rejected. Reload it before saving again.':`The server returned an unexpected confirmation. Check View ${plural} before retrying.`,true);return;}
    const result=await response.json();
    if(!response.ok||result.ok!==true){
     if(response.status===422&&typeof result.message==='string'){
      const warning=document.getElementById('registrationDuplicate');
      if(kind==='resident'&&result.duplicate&&warning&&!warning.querySelector('input')){const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.name='confirm_duplicate';check.value='yes';label.append(check,document.createTextNode(' I reviewed the possible duplicate and confirm this is a different person.'));warning.append(label);warning.className='helper-text duplicate-warning';warning.setAttribute('role','alert');}
      else if(kind==='resident'&&!result.duplicate&&warning)warning.replaceChildren();
      if(warning)warning.hidden=!result.duplicate;error(result.message);return;
     }
     error(`The save could not be confirmed. Check View ${plural} before retrying.`,true);return;
    }
    const destination=new URL(result.redirect,location.href),allowed=kind==='household'?/^\/view_household\/\d+$/:/^\/resident\/\d+$/;
    if(destination.origin!==location.origin||!allowed.test(destination.pathname)){error(`The save could not be confirmed. Check View ${plural} before retrying.`,true);return;}
    location.assign(destination.href);
   }catch(failure){error(failure.name==='AbortError'?`Confirmation timed out. The save may have completed. Check View ${plural} before retrying.`:`Connection interrupted. The save may have completed. Check View ${plural} before retrying.`,true);}
   finally{clearTimeout(timeout);}
  });
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
