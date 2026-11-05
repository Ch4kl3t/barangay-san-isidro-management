/* Scoped enhancements: native modal focus/inert behavior, recipient alerts, table focus. */

(() => {

 const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
 // The shared bell/navigation is removed; the optional existing inbox still works.
 for(const button of document.querySelectorAll('[data-notification-read]')){
   button.onclick=async()=>{
     button.disabled=true;
     try{const response=await fetch('/api/notifications/'+button.dataset.notificationRead+'/read',{method:'POST'});
       if(!response.ok)throw Error();location.reload();
     }catch(_){button.disabled=false;window.officeFeedback?.('Unable to update','The notification could not be marked as read. Try again.');}
   };
 }

 // Move the actual table into a focus dialog; restore it without losing handlers/state.

 for(const card of document.querySelectorAll('.admin-resident-table .table-card,.analytics-wrapper .table-card')){

   const table=card.querySelector('table');if(!table)continue;

   if(card.closest('.analytics-wrapper')&&!card.closest('[data-no-table-expand]')){
   const button=node('button','Expand table');button.type='button';button.className='table-focus-button';card.prepend(button);

   button.onclick=()=>{let focus=document.getElementById('officeTableDialog');if(!focus){focus=document.createElement('dialog');focus.id='officeTableDialog';focus.className='office-dialog table-focus-dialog';focus.setAttribute('aria-label','Expanded records table');document.body.append(focus);}

     const tableScroll=window.scrollY;focus.classList.toggle('admin-resident-table',Boolean(card.closest('.admin-resident-table')));button.hidden=true;const marker=document.createComment('table position');card.before(marker);const close=node('button','Close expanded table');close.type='button';close.onclick=()=>focus.close();focus.replaceChildren(close,card);focus.showModal();

     focus.addEventListener('close',()=>{marker.replaceWith(card);button.hidden=false;window.scrollTo(0,tableScroll);button.focus({preventScroll:true});},{once:true});

   };

   }
   if(card.closest('.admin-resident-table')){

     const labels=[...table.tHead.rows[0].cells].map(c=>c.textContent.trim());

     for(const row of [...table.tBodies[0].rows]){

       if(row.cells.length!==labels.length)continue;[...row.cells].forEach((cell,i)=>cell.dataset.label=labels[i]);const more=node('button','Details');more.type='button';more.className='mobile-row-details';more.setAttribute('aria-expanded','false');row.cells[row.cells.length-1].append(more);

       const detail=document.createElement('tr');detail.className='row-details';detail.hidden=true;const cell=detail.insertCell();cell.colSpan=labels.length;const dl=document.createElement('dl');for(let i=0;i<labels.length-1;i++){dl.append(node('dt',labels[i]),node('dd',row.cells[i].textContent.trim()));}cell.append(dl);row.after(detail);more.onclick=()=>{detail.hidden=!detail.hidden;more.setAttribute('aria-expanded',String(!detail.hidden));};

     }

   }

 }

})();


// Dismiss server-rendered feedback without alerts or HTML injection.
document.addEventListener('click',event=>{const button=event.target.closest('[data-dismiss-feedback]');if(button){const message=button.closest('.office-feedback');const next=message.nextElementSibling?.querySelector('button')||document.querySelector('#main-content h1');if(next){if(!next.hasAttribute('tabindex'))next.setAttribute('tabindex','-1');next.focus();}message.remove();}});
