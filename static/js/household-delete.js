/* Shared Directory/Details confirmation; server locks and membership checks are authoritative. */
(() => {
 const dialog=document.getElementById('householdDeleteDialog'),form=document.getElementById('deleteHouseholdForm');
 if(!dialog||!form)return;
 let opener=null;
 document.addEventListener('click',event=>{
  const button=event.target.closest('[data-delete-household]');
  if(!button||button.disabled||dialog.open)return;
  event.preventDefault();
  const target=new URL(button.dataset.deleteUrl,location.href);
  if(target.origin!==location.origin||!/^\/delete_household\/[1-9]\d*$/.test(target.pathname))return;
  opener=button;form.action=target.href;
  document.getElementById('householdDeleteMessage').textContent='Permanently delete the '+(button.dataset.householdName||'selected')+' household? It has no resident records. This cannot be undone.';
  dialog.showModal();dialog.querySelector('[data-cancel-household-delete]').focus();
 });
 dialog.querySelector('[data-cancel-household-delete]').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('close',()=>opener?.focus({preventScroll:true}));
 form.addEventListener('submit',event=>{
  if(!dialog.open||form.dataset.submitting==='yes'){event.preventDefault();return;}
  form.dataset.submitting='yes';const submit=form.querySelector('[type=submit]');
  submit.disabled=true;submit.textContent='Deleting…';
 });
 window.addEventListener('pageshow',()=>{delete form.dataset.submitting;const submit=form.querySelector('[type=submit]');submit.disabled=false;submit.textContent='Delete Household';if(dialog.open)dialog.close();});
})();
