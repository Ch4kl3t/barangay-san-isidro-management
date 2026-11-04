/* Accessible feedback and explicit head decisions; server validation is authoritative. */
(() => {
 const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
 function dialog(title,message,confirmed=null,sessionExpired=false){
  if(document.querySelector('.office-feedback-dialog[open]'))return;
  const opener=document.activeElement,box=document.createElement('dialog');box.className='office-feedback-dialog';
  const heading=node('h2',title),body=node('p',message),actions=node('div','');
  heading.id='officeFeedbackTitle';body.id='officeFeedbackBody';actions.className='dialog-actions';
  box.setAttribute('aria-labelledby',heading.id);box.setAttribute('aria-describedby',body.id);
  const cancel=node('button',confirmed?'Cancel':'Close');cancel.type='button';cancel.onclick=()=>box.close();actions.append(cancel);
  if(confirmed){const accept=node('button','Confirm');accept.type='button';accept.className='dialog-primary';accept.onclick=()=>{box.close();confirmed();};actions.append(accept);}
  if(sessionExpired){const login=node('a','Sign In');login.href='/login';login.className='dialog-primary';actions.append(login);}
  box.append(heading,body,actions);document.body.append(box);
  box.addEventListener('close',()=>{box.remove();opener?.focus({preventScroll:true});},{once:true});
  box.showModal();cancel.focus();
 }
 window.officeFeedback=(title,message)=>dialog(title,message);
 const feedback=[...document.querySelectorAll('.office-feedback-region .office-feedback')];
 if(feedback.length)dialog(feedback.some(el=>el.classList.contains('error'))?'Action could not be completed':'Application feedback',feedback.map(el=>el.querySelector('span')?.textContent||el.textContent).join('\n'));
 const confirmedForms=new WeakSet();
 document.addEventListener('submit',event=>{
  const form=event.target;
  if(confirmedForms.has(form)){confirmedForms.delete(form);return;}
  const designate=form.elements.namedItem('designate_head');
  if(!form.dataset.confirmMessage&&!designate?.checked)return;
  if(!form.checkValidity())return;
  event.preventDefault();event.stopImmediatePropagation();const submitter=event.submitter;
  dialog('Confirm household-head decision',form.dataset.confirmMessage||'Designate this resident as household head? Previous decisions and relationships remain in history. Record relationships to the new head explicitly.',()=>{confirmedForms.add(form);form.requestSubmit(submitter||undefined);});
 },true);
 for(const form of document.querySelectorAll('.form-card form')){
  form.querySelectorAll('.form-group').forEach((group,i)=>{const label=group.querySelector('label'),field=group.querySelector('input:not([type=hidden]),select,textarea');if(!label||!field)return;if(!field.id)field.id='form-field-'+i;if(!label.htmlFor)label.htmlFor=field.id;});
 }
 for(const table of document.querySelectorAll('.households-directory .registry-table')){
  const labels=[...table.tHead.rows[0].cells].map(cell=>cell.textContent.trim());
  for(const row of table.tBodies[0].rows)if(row.cells.length===labels.length)[...row.cells].forEach((cell,i)=>cell.dataset.label=labels[i]);
 }
 const roles=document.getElementById('householdHeadOptions');
 if(roles){
  const options=JSON.parse(roles.textContent),form=roles.closest('form'),home=form.elements.namedItem('household_id'),assignment=form.elements.namedItem('head_assignment'),relation=form.elements.namedItem('relationship_to_head'),designate=form.elements.namedItem('designate_head'),reason=form.elements.namedItem('head_reason');
  const requiredReason=()=>{reason.required=designate.checked;};designate.addEventListener('change',requiredReason);requiredReason();
  home?.addEventListener('change',()=>{const head=options[home.value]||{};assignment.value=head.assignment||'none';relation.value='';designate.checked=false;requiredReason();document.getElementById('householdHeadHint').textContent='Current head: '+(head.name||'Not designated')+'. Household changed; enter relationships explicitly.';});
 }
 const originalFetch=window.fetch.bind(window);
 window.fetch=async(input,init)=>{
  const response=await originalFetch(input,init);
  const url=new URL(typeof input==='string'?input:input.url,location.href);
  if(url.origin===location.origin&&response.status===401)dialog('Session expired','Sign in again before continuing. An interrupted save is not confirmed; check the record before retrying.',null,true);
  return response;
 };
})();
