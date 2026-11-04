(() => {
 const modal=document.getElementById('auditModal');if(!modal)return;
 let opener;
 const text=(id,value)=>document.getElementById(id).textContent=value??'Not recorded';
 function close(){modal.classList.remove('open');modal.setAttribute('aria-hidden','true');opener?.focus();}
 document.getElementById('closeModal').onclick=close;
 modal.onclick=e=>{if(e.target===modal)close();};
 document.addEventListener('keydown',e=>{
   if(!modal.classList.contains('open'))return;
   if(e.key==='Escape'){e.preventDefault();close();}
   if(e.key==='Tab'){
     const fields=[...modal.querySelectorAll('button,summary,a[href],[tabindex="0"]')].filter(el=>el.getClientRects().length),first=fields[0],last=fields.at(-1);
     if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
   }
 });
 for(const button of document.querySelectorAll('.details-btn'))button.addEventListener('click',()=>{
   opener=button;const d=button.dataset,details=JSON.parse(d.detail||'{}');
   const titles={ADD:d.target+' created',UPDATE:d.target+' updated',DELETE:d.target+' deleted',LOGIN:'Staff sign-in',LOGIN_DENIED:'Sign-in denied',LOGOUT:'Staff signed out',REPORT_GENERATE:'Report generated',PASSWORD_CHANGE:'Password changed',PASSWORD_RESET_SUCCESS:'Password reset completed'};
   text('modalTitle',titles[d.action]||d.action.replaceAll('_',' '));text('modalLogId','Event '+d.logId);
   text('modalOutcome',d.outcome);const outcome=document.getElementById('modalOutcome');
   outcome.dataset.tone=d.outcome.toUpperCase().startsWith('DENIED')?'denied':d.outcome==='SUCCESS'?'success':d.outcome==='FAILED'?'failed':'neutral';
   text('modalUser',`${d.user} · ${d.role}`);text('modalAction',d.action.replaceAll('_',' '));text('modalTarget',`${d.target} #${d.targetId}`);text('modalTime',d.time);text('modalDescription',d.description);
   const body=document.getElementById('modalEventDetails');body.replaceChildren();
   const add=(tag,value)=>{const el=document.createElement(tag);el.textContent=value;body.append(el);};
   if(d.action==='UPDATE'){
     add('h3','Changed fields');
     if(!details.changes?.length)add('p','No ordinary field changes recorded. Health updates, where present, are recorded as metadata only.');
     if(details.changes?.length){
       const scroll=document.createElement('div');scroll.className='audit-change-scroll';const table=document.createElement('table');table.className='audit-changes';
       const head=table.createTHead().insertRow();for(const label of ['Field','Before','After']){const th=document.createElement('th');th.scope='col';th.textContent=label;head.append(th);}
       const rows=table.createTBody();for(const change of details.changes){const row=rows.insertRow();for(const value of [change.field,display(change.before),display(change.after)])row.insertCell().textContent=value;}
       scroll.append(table);body.append(scroll);
     }
   }else if(['ADD','DELETE'].includes(d.action)){
     add('h3',d.action==='ADD'?'Created record':'Deleted record');
     const snapshot=d.action==='ADD'?details.new:details.old;
     for(const key of ['firstname','middlename','surname','house_number','address','household_id','status'])if(snapshot?.[key]!=null)add('p',`${key.replaceAll('_',' ')}: ${display(snapshot[key])}`);
   }else add('p','This event records an account, authentication or report action. No unrelated before/after fields are shown.');
   text('modalTechnical',JSON.stringify(details,null,2));modal.querySelector('.audit-technical').open=false;
   modal.classList.add('open');modal.setAttribute('aria-hidden','false');document.getElementById('closeModal').focus();
 });
 function display(value){return value==null||value===''?'Not recorded':typeof value==='object'?JSON.stringify(value):String(value);}
 const requested=location.hash.match(/^#event-(\d+)$/);
 if(requested)document.querySelector('.details-btn[data-log-id="#'+requested[1]+'"]')?.click();
})();
