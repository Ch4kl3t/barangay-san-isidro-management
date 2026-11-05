/* Progressive enhancement of the existing POST form; server rules remain authoritative. */
(() => {
 const card=document.getElementById('householdHeadCard');
 if(!card||typeof HTMLDialogElement==='undefined'||typeof HTMLDialogElement.prototype.showModal!=='function')return;
 const fallback=card.querySelector('#headAssignment'),content=card.querySelector('[data-head-editor]'),form=card.querySelector('[data-head-form]');
 if(!fallback||!content||!form)return;
 const launch=document.createElement('button');launch.type='button';launch.className='head-action head-action-primary';
 launch.textContent=fallback.querySelector('[data-head-launch]').textContent;
 const box=document.createElement('dialog');box.className='office-feedback-dialog head-management-dialog';
 box.setAttribute('aria-labelledby','headDialogTitle');box.setAttribute('aria-describedby','headDialogDescription');
 box.append(content);document.body.append(box);fallback.hidden=true;card.querySelector('[data-head-actions]').append(launch);
 const edit=content.querySelector('[data-head-edit-view]'),review=content.querySelector('[data-head-review]'),title=content.querySelector('#headDialogTitle'),description=content.querySelector('#headDialogDescription');
 const resident=form.elements.namedItem('head_resident_id'),reason=form.elements.namedItem('head_reason'),confirm=content.querySelector('[data-head-confirm]');
 const initialTitle=title.textContent,initialDescription=description.textContent;
 let approved=false,submitting=false,reviewed=null;
 form.querySelector('[data-head-review-button]').textContent=form.dataset.headExisting==='yes'?'Review Change':'Review Designation';
 function editing(){edit.hidden=false;review.hidden=true;title.textContent=initialTitle;description.textContent=initialDescription;}
 launch.onclick=()=>{editing();box.showModal();resident.focus();};
 for(const button of content.querySelectorAll('[data-head-cancel]')){button.hidden=false;button.onclick=()=>{if(!submitting)box.close();};}
 content.querySelector('[data-head-back]').onclick=()=>{editing();resident.focus();};
 box.addEventListener('cancel',event=>{if(submitting)event.preventDefault();});
 box.addEventListener('close',()=>{editing();launch.focus({preventScroll:true});});
 window.addEventListener('pageshow',event=>{if(event.persisted){submitting=false;approved=false;confirm.disabled=false;if(box.open)box.close();}});
 form.addEventListener('submit',event=>{
  if(approved){approved=false;submitting=true;confirm.disabled=true;return;}
  event.preventDefault();if(!form.reportValidity())return;
  const clear=!resident.value,reassign=form.dataset.headExisting==='yes';
  const selected=resident.selectedOptions[0];
  const values={household:form.dataset.headHousehold,name:clear?'No designated head':selected.dataset.residentName||selected.textContent,id:clear?'None':resident.value,reason:reason.value};
  reviewed={id:resident.value,reason:reason.value};
  for(const [key,value] of Object.entries(values))content.querySelector('[data-review-'+key+']').textContent=value;
  title.textContent=clear?'Confirm Clearing Household Head':reassign?'Confirm Household Head Reassignment':'Confirm Household Head Designation';
  description.textContent='Review the decision before saving.';
  content.querySelector('[data-review-explanation]').textContent=clear?'This action will leave the household without a designated head. Previous designations will remain in the history.':'This action will update the designated household head. Previous designations will remain in the history.';
  confirm.textContent=clear?'Confirm Clear':reassign?'Confirm Reassignment':'Confirm Designation';
  edit.hidden=true;review.hidden=false;content.querySelector('[data-head-back]').focus();
 });
 confirm.onclick=()=>{
  if(submitting)return;
  if(!reviewed||reviewed.id!==resident.value||reviewed.reason!==reason.value){editing();description.textContent='The decision changed. Review the updated selection and reason.';resident.focus();return;}
  editing();if(!form.reportValidity())return;
  approved=true;form.requestSubmit();
 };
})();
