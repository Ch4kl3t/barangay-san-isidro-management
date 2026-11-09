/* Accessible feedback and explicit head decisions; server validation is authoritative. */
(() => {
 const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
 function dialog(title,message,confirmed=null,sessionExpired=false,confirmLabel='Confirm'){
  if(document.querySelector('.office-feedback-dialog[open]'))return;
  const opener=document.activeElement,box=document.createElement('dialog');box.className='office-feedback-dialog';
  const heading=node('h2',title),body=node('p',message),actions=node('div','');
  heading.id='officeFeedbackTitle';body.id='officeFeedbackBody';actions.className='dialog-actions';
  box.setAttribute('aria-labelledby',heading.id);box.setAttribute('aria-describedby',body.id);
  const cancel=node('button',confirmed?'Cancel':'Close');cancel.type='button';cancel.onclick=()=>box.close();actions.append(cancel);
  if(confirmed){const accept=node('button',confirmLabel);accept.type='button';accept.className='dialog-primary';accept.onclick=()=>{box.close();confirmed();};actions.append(accept);}
  if(sessionExpired){const login=node('a','Sign In');login.href='/login';login.className='dialog-primary';actions.append(login);}
  box.append(heading,body,actions);document.body.append(box);
  box.addEventListener('close',()=>{box.remove();opener?.focus({preventScroll:true});},{once:true});
  box.showModal();cancel.focus();
 }
 const confirmedForms=new WeakSet();
 document.addEventListener('submit',event=>{
  const form=event.target;
  if(form.matches('[data-head-form]'))return;
  if(confirmedForms.has(form)){confirmedForms.delete(form);return;}
  if(form.dataset.headRoleApproved==='yes'){return;}
  const designate=form.elements.namedItem('designate_head');
  if(!form.dataset.confirmMessage&&!designate?.checked)return;
  if(!form.checkValidity())return;
  event.preventDefault();event.stopImmediatePropagation();const submitter=event.submitter;
  let title=form.matches('.resident-editor form')?'Save Resident Profile Changes?':'Confirm household-head decision',message=form.dataset.confirmMessage||'Previous decisions and relationships remain in history. Record relationships to the new head explicitly.';
  if(designate?.checked){
   const field=name=>form.elements.namedItem(name),home=field('household_id');
   const name=['firstname','middlename','surname'].map(key=>field(key)?.value||'').filter(Boolean).join(' ');
   const identifier=new URL(form.action,location.href).pathname.match(/^\/edit_member\/(\d+)$/)?.[1];
   title='Confirm Household Head Designation';
   message=`Household: ${home?.selectedOptions?.[0]?.textContent.trim()||'Household #'+(home?.value||'Not selected')}\nResident: ${name}\nResident ID: ${identifier||'Assigned when the resident is saved'}\nReason: ${field('head_reason')?.value||''}\n\nThis action will update the designated household head. Previous designations will remain in the history.`;
  }
  dialog(title,message,()=>{confirmedForms.add(form);form.requestSubmit(submitter||undefined);},false,designate?.checked?'Confirm Designation':'Confirm');
 },true);
 for(const form of document.querySelectorAll('.form-card form')){
  form.querySelectorAll('.form-group').forEach((group,i)=>{const label=group.querySelector('label'),field=group.querySelector('input:not([type=hidden]),select,textarea');if(!label||!field)return;if(!field.id)field.id='form-field-'+i;if(!label.htmlFor)label.htmlFor=field.id;});
 }
 for(const table of document.querySelectorAll('.households-directory .registry-table')){
  const labels=[...table.tHead.rows[0].cells].map(cell=>cell.textContent.trim());
  for(const row of table.tBodies[0].rows)if(row.cells.length===labels.length)[...row.cells].forEach((cell,i)=>cell.dataset.label=labels[i]);
 }
 const originalFetch=window.fetch.bind(window);
 window.fetch=async(input,init)=>{
  const response=await originalFetch(input,init);
  const url=new URL(typeof input==='string'?input:input.url,location.href);
  if(url.origin===location.origin&&response.status===401)dialog('Session expired','Sign in again before continuing. An interrupted save is not confirmed; check the record before retrying.',null,true);
  return response;
 };
})();
