/* Scoped enhancements: native modal focus/inert behavior, recipient alerts, table focus. */

(() => {

 let notificationSeq=0;

 const bell=document.getElementById('notificationBell'),panel=document.getElementById('notificationPanel');

 const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};

 async function refreshBell(){

   if(!bell)return;const current=++notificationSeq;

   try{const response=await fetch('/api/notifications?view=unread');if(!response.ok)return;const data=await response.json();if(current!==notificationSeq)return;const badge=document.getElementById('notificationBadge');badge.textContent=data.unread;const pageCount=document.getElementById('notificationUnreadCount');if(pageCount)pageCount.textContent=data.unread;badge.classList.toggle('hidden',!data.unread);bell.setAttribute('aria-label',`Notifications, ${data.unread} unread`);panel.replaceChildren(node('h3','Notifications'));

     if(!data.items.length)panel.append(node('p','You have no unread notifications.'));

     for(const item of data.items){const article=node('article',''),a=node('a',item.summary);a.href='/notifications/open/'+item.id;article.append(a,node('small',item.time));const button=node('button','Mark as read');button.type='button';button.onclick=()=>markRead(item.id,button);article.append(button);panel.append(article);}

     const all=node('a','View all notifications');all.href='/notifications';panel.append(all);

   }catch(error){if(!panel.hidden)panel.replaceChildren(node('p','Notifications unavailable. Try View all notifications.'));}

 }

 async function markRead(id,button){notificationSeq++;const response=await fetch('/api/notifications/'+id+'/read',{method:'POST'});if(response.ok){button.disabled=true;button.textContent='Read';if(button.closest('.notifications-page')){location.reload();return;}await refreshBell();if(!panel.hidden)panel.querySelector('a,button')?.focus();}}

 bell?.addEventListener('keydown',event=>{if(event.key===' '){event.preventDefault();bell.click();}});

 bell?.addEventListener('click',event=>{event.preventDefault();panel.hidden=!panel.hidden;bell.setAttribute('aria-expanded',String(!panel.hidden));if(!panel.hidden){const rect=bell.getBoundingClientRect();panel.style.top=(rect.bottom+8)+'px';panel.style.right=Math.max(12,Math.min(innerWidth-panel.offsetWidth-12,innerWidth-rect.right))+'px';refreshBell().then(()=>panel.querySelector('a,button')?.focus());}});

 document.addEventListener('click',event=>{if(panel&&!panel.contains(event.target)&&!bell?.contains(event.target)){panel.hidden=true;bell?.setAttribute('aria-expanded','false');}});

 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&panel&&!panel.hidden){panel.hidden=true;bell.setAttribute('aria-expanded','false');bell.focus();}});

 for(const button of document.querySelectorAll('[data-notification-read]'))button.onclick=()=>markRead(button.dataset.notificationRead,button);

 if(bell){refreshBell();setInterval(refreshBell,60000);}

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

       if(row.cells.length!==labels.length)continue;const more=node('button','Details');more.type='button';more.className='mobile-row-details';more.setAttribute('aria-expanded','false');row.cells[row.cells.length-1].append(more);

       const detail=document.createElement('tr');detail.className='row-details';detail.hidden=true;const cell=detail.insertCell();cell.colSpan=labels.length;const dl=document.createElement('dl');for(let i=0;i<labels.length-1;i++){dl.append(node('dt',labels[i]),node('dd',row.cells[i].textContent.trim()));}cell.append(dl);row.after(detail);more.onclick=()=>{detail.hidden=!detail.hidden;more.setAttribute('aria-expanded',String(!detail.hidden));};

     }

   }

 }

})();


// Dismiss server-rendered feedback without alerts or HTML injection.
document.addEventListener('click',event=>{const button=event.target.closest('[data-dismiss-feedback]');if(button){const message=button.closest('.office-feedback');const next=message.nextElementSibling?.querySelector('button')||document.querySelector('#main-content h1');if(next){if(!next.hasAttribute('tabindex'))next.setAttribute('tabindex','-1');next.focus();}message.remove();}});
