/* Progressive GET filtering: server authorization, URLs and history remain authoritative. */
(() => {
 for(const form of document.querySelectorAll('form[data-auto-filters]')){
  let timer,composing=false;
  const status=document.createElement('p');status.className='report-note';status.role='status';form.append(status);
  const submit=()=>{
   clearTimeout(timer);if(composing)return;const commitSearch=form.dataset.commitSearch==='true';delete form.dataset.commitSearch;
   const from=form.elements.namedItem('date_from'),to=form.elements.namedItem('date_to');
   if(from&&to&&((!!from.value!==!!to.value)||(from.value&&from.value>to.value))){status.textContent='Enter a complete valid date range before applying filters.';return;}
   if(!form.checkValidity()){status.textContent='Complete the highlighted filter values.';form.reportValidity();return;}
   const params=new URLSearchParams(new FormData(form));const explicit=form.querySelector('[data-explicit-search]');if(explicit&&!commitSearch)params.set(explicit.name,explicit.dataset.committedValue||'');params.delete('page');for(const [key,value] of [...params])if(!value)params.delete(key);
   const next=location.pathname+(params.size?'?'+params:'');
   if(next===location.pathname+location.search)return;
   status.textContent='Loading matching records…';form.setAttribute('aria-busy','true');location.assign(next);
  };
  form.addEventListener('submit',event=>{event.preventDefault();submit();});
  form.addEventListener('change',event=>{if(event.target.matches('select,input[type=checkbox],input[type=date],input[type=datetime-local]'))submit();});
  form.addEventListener('input',event=>{if(event.target.matches('[data-explicit-search]'))return;if(event.target.matches('input[type=search],input[type=text],input:not([type])')){clearTimeout(timer);if(!composing)timer=setTimeout(submit,450);}});
  form.addEventListener('compositionstart',()=>{composing=true;clearTimeout(timer);});form.addEventListener('compositionend',event=>{composing=false;if(!event.target.matches('[data-explicit-search]'))timer=setTimeout(submit,450);});
  form.querySelector('[type=submit]')?.setAttribute('hidden','');
  window.addEventListener('beforeunload',()=>clearTimeout(timer));
  document.addEventListener('click',event=>{if(event.target.closest('a[href]'))clearTimeout(timer);});
 }
})();
