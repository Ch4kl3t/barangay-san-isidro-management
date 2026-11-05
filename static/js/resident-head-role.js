/* Explicit role decisions in Add/Edit Resident; server state remains authoritative. */
(() => {
 const form=document.querySelector('.resident-editor form'),data=document.getElementById('householdHeadOptions');
 if(!form||!data)return;
 const homes=JSON.parse(data.textContent),headField=form.elements.namedItem('head_assignment');
 const household=form.elements.namedItem('household_id');
 const role=()=>form.querySelector('input[name="head_role"]:checked')?.value||'member';
 const relation=form.elements.namedItem('relationship_to_head'),status=form.elements.namedItem('status');
 form.querySelectorAll('input[name="head_role"]').forEach(input=>input.addEventListener('change',()=>{if(input.checked&&input.value==='head'&&relation)relation.value='';}));
 status?.addEventListener('change',()=>{
  const current=homes[household?.value||'']||{},residentId=location.pathname.match(/^\/edit_member\/(\d+)$/)?.[1];
  const headChoice=form.querySelector('input[name="head_role"][value="head"]'),currentHead=String(current.resident_id||'')===String(residentId||'');
  if(status.value==='Deceased'&&!currentHead){headChoice.disabled=true;form.querySelector('input[name="head_role"][value="member"]').checked=true;}
  else headChoice.disabled=false;
  let note=document.getElementById('headEligibilityNote');
  if(!note){note=document.createElement('p');note.id='headEligibilityNote';note.className='helper-text';note.setAttribute('role','status');form.querySelector('.resident-role-options').after(note);}
  note.textContent=status.value==='Deceased'?(currentHead?'A deceased resident cannot be newly designated. Choose Household member to clear this current head, or keep the resident active.':'Head designation is unavailable because this resident is deceased. Only an active household member can be designated.') :'';
  note.hidden=!note.textContent;
 });
 household?.addEventListener('change',()=>{
  const head=homes[household.value]||{};
  if(headField)headField.value=head.assignment||'none';
  const hint=document.getElementById('householdHeadHint');
  if(hint)hint.textContent='Current head: '+(head.name||'Not designated')+(head.resident_id?' (Resident #'+head.resident_id+')':'')+'.';
 });
 form.addEventListener('submit',event=>{
  const choice=role(),head=homes[household?.value||'']||{},residentId=location.pathname.match(/^\/edit_member\/(\d+)$/)?.[1];
  const changing=choice==='head'?String(head.resident_id||'')!==String(residentId||''):String(head.resident_id||'')===String(residentId||'');
  if(!changing||form.dataset.headRoleApproved==='yes')return;
  event.preventDefault();
  const name=['firstname','middlename','surname'].map(key=>form.elements.namedItem(key)?.value.trim()).filter(Boolean).join(' ');
  const existing=!!head.resident_id,current=head.name||'No current household head';
  const message=choice==='head'?`You are about to designate ${name||'this resident'} as the household head.${existing?` The current household head, ${current} (Resident #${head.resident_id}), will become a household member.`:''} Do you want to continue?`:`${current} (Resident #${head.resident_id}) will no longer be designated as the household head. The household will have no designated head. Do you want to continue?`;
  const box=document.createElement('dialog');box.className='office-feedback-dialog';
  const title=document.createElement('h2');title.textContent=choice==='head'?(existing?'Change household head?':'Designate household head?'):'Clear household head?';
  const body=document.createElement('p');body.textContent=message;
  const actions=document.createElement('div');actions.className='dialog-actions';
  const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel';
  const confirm=document.createElement('button');confirm.type='button';confirm.className='dialog-primary';confirm.textContent=choice==='head'&&existing?'Confirm Change':choice==='head'?'Confirm Designation':'Confirm Change';
  actions.append(cancel,confirm);box.append(title,body,actions);document.body.append(box);
  const opener=document.activeElement,close=()=>{box.remove();opener?.focus({preventScroll:true});};
  cancel.onclick=()=>box.close();confirm.onclick=()=>{box.close();form.dataset.headRoleApproved='yes';form.requestSubmit();};
  box.addEventListener('close',close,{once:true});box.showModal();cancel.focus();
 });
})();
