/* Bounded, categorized record search. Only DOM text and server-owned record URLs. */
(() => {
 const input=document.getElementById('searchBox'),panel=document.getElementById('suggestions');
 if(!input||!panel||!document.querySelector('.home-wrapper'))return;
 let timer,sequence=0,index=-1,links=[];
 input.setAttribute('aria-controls','suggestions');input.setAttribute('aria-expanded','false');
 input.setAttribute('aria-label','Search residents and households');
 const status=document.createElement('p');status.className='global-search-status';status.role='status';status.setAttribute('aria-live','polite');input.closest('.search-panel').append(status);
 function close(){panel.hidden=true;panel.style.display='none';input.setAttribute('aria-expanded','false');index=-1;}
 function show(){panel.hidden=false;panel.style.display='block';input.setAttribute('aria-expanded','true');}
 function paint(rows){
  panel.replaceChildren();links=[];index=-1;
  for(const type of ['Resident','Household']){
   const matches=rows.filter(row=>row.type===type);if(!matches.length)continue;
   const heading=document.createElement('h3');heading.className='global-search-category';heading.textContent=type==='Resident'?'Residents':'Households';panel.append(heading);
   for(const row of matches){
    const url=new URL(row.url,location.href);
    if(url.origin!==location.origin||!/^\/(resident|view_household)\/\d+$/.test(url.pathname))continue;
    const link=document.createElement('a');link.className='search-item global-search-result';link.href=url.pathname;
    const name=document.createElement('strong'),detail=document.createElement('small');name.textContent=row.name;detail.textContent=`${type} #${row.id} · ${row.details}`;
    link.append(name,detail);panel.append(link);links.push(link);
   }
  }
  if(!links.length){const empty=document.createElement('p');empty.className='global-search-empty';empty.textContent='No matching residents or households.';panel.append(empty);}
  status.textContent=links.length?`${links.length} results shown. Use arrow keys to choose a record.`:'No results. Try fewer name words, a record ID, house number or address.';show();
 }
 input.addEventListener('input',()=>{
  clearTimeout(timer);const current=++sequence,query=input.value.trim();links=[];close();
  if(!query){panel.replaceChildren();status.textContent='';return;}
  status.textContent='Searching…';timer=setTimeout(async()=>{
   try{const response=await fetch('/api/search_residents?q='+encodeURIComponent(query));if(!response.ok)throw Error();const rows=await response.json();if(current!==sequence)return;if(!Array.isArray(rows))throw Error();paint(rows);}
   catch(error){if(current!==sequence)return;panel.replaceChildren();status.textContent='Search unavailable. Check the connection and retry.';close();}
  },250);
 });
 input.addEventListener('keydown',event=>{
  if(event.key==='Escape'){event.preventDefault();sequence++;clearTimeout(timer);close();return;}
  if(['ArrowDown','ArrowUp'].includes(event.key)&&links.length){event.preventDefault();show();index=(index+(event.key==='ArrowDown'?1:-1)+links.length)%links.length;links.forEach((link,i)=>link.classList.toggle('search-selected',i===index));links[index].scrollIntoView({block:'nearest'});}
  if(event.key==='Enter'&&index>=0&&!panel.hidden){event.preventDefault();location.assign(links[index].href);}
 });
 document.addEventListener('click',event=>{if(!event.target.closest('.home-wrapper .search-panel'))close();});close();
})();
