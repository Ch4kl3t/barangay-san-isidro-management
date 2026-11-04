/* Contextual presentation only. The unchanged server validates signed bounds on every request. */
window.ContextPrintWorkspace={mount(root,config){
 const get=id=>root.querySelector('#'+id),form=get('reportFilters'),print=get('reportPrint'),word=get('reportWord');
 const kind=config.initial.kind||'residents',category=kind==='households'&&config.initial.mode==='members'?'residents':kind;
 const title=config.locked.resident_id?'Resident Record':kind==='households'&&config.initial.mode==='members'?'Household Member List':kind==='households'?'Household Directory':'Resident Directory';
 let sequence=0,controller,closed=false,invalidDirectory=false;
 get('contextDocument').textContent=title;
 const header=root.closest('#printOptionsPanel')?.querySelector('#printOptionsTitle');if(header)header.textContent='Print '+title;
 const filtered=Object.keys(config.locked).some(k=>!['kind','mode','scope','resident_id','household_id'].includes(k));
 get('contextCriteria').textContent=filtered?'Current search and filters are included across all matching pages.':'Includes all matching records across pages.';
 const disable=()=>{for(const link of [print,word]){link.removeAttribute('href');link.setAttribute('aria-disabled','true');}};
 function columns(){
  const wanted=(config.initial.columns||'').split(',');get('reportColumns').replaceChildren();
  for(const [key,label] of config.columns[category]){const input=document.createElement('input'),wrap=document.createElement('label');input.type='checkbox';input.value=key;input.checked=(wanted[0]?wanted:config.defaults[category]).includes(key)||config.required[category].includes(key);input.disabled=config.required[category].includes(key);wrap.append(input,document.createTextNode(' '+label));get('reportColumns').append(wrap);}
 }
 function stale(){sequence++;controller?.abort();disable();get('reportPreview').classList.add('preview-stale');get('reportSummary').textContent='Preview needs updating.';get('reportMessage').textContent='Columns changed. Preview again before printing or downloading.';}
 form.addEventListener('change',stale);
 get('reportReset').addEventListener('click',()=>{columns();stale();});
 for(const link of [print,word])link.addEventListener('click',event=>{if(link.getAttribute('aria-disabled')==='true')event.preventDefault();});
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(closed||invalidDirectory)return;
  controller?.abort();controller=new AbortController();const current=++sequence;
  const params=new URLSearchParams(config.locked);params.delete('kind');params.set('context',config.initial.context);
  params.set('columns',[...get('reportColumns').querySelectorAll('input:checked')].map(input=>input.value).join(','));
  disable();get('reportPreview').setAttribute('aria-busy','true');get('reportMessage').textContent='Checking matching records…';
  try{
   const response=await fetch('/api/preview/'+kind+'?'+params,{signal:controller.signal}),data=await response.json();
   if(closed||current!==sequence)return;
   if(!response.ok)throw Error(data.error||'Unable to preview this document. Close and reopen Print Options or retry.');
   const head=get('reportPreview').tHead,body=get('reportPreview').tBodies[0];head.replaceChildren();body.replaceChildren();
   const heading=document.createElement('tr');for(const column of data.columns){const th=document.createElement('th');th.scope='col';th.textContent=column.label;heading.append(th);}head.append(heading);
   for(const row of data.items){const tr=document.createElement('tr');for(const column of data.columns){const td=document.createElement('td');td.textContent=row[column.key]??'Not recorded';tr.append(td);}body.append(tr);}
   get('reportPreview').classList.remove('preview-stale');get('contextCount').textContent=data.total+' matching '+(data.total===1?'record':'records');
   if(config.locked.resident_id&&data.items.length)get('contextIncludes').textContent=data.items[0].full_name||config.context_label;
   get('reportSummary').textContent=data.total===0?'No records match the current page selection.':data.sample?`Preview: ${data.shown} of ${data.total} records. Print and Word include all ${data.total}.`:`All ${data.total} matching records are shown. Print and Word use this same selection.`;
   get('reportMessage').textContent=data.total?'Preview validated. Ready to print or download.':'Nothing to print. Close this panel to review the directory search or filters.';
   if(data.total){print.href='/reports/print/'+kind+'?'+params+'&autoprint=1';word.href=({residents:'/print_all_members',households:'/print_households_report',audit:'/print_audit_logs_report'})[kind]+'?'+params;for(const link of [print,word])link.setAttribute('aria-disabled','false');}
  }catch(error){if(error.name==='AbortError'||closed||current!==sequence)return;disable();get('contextCount').textContent='Count unavailable';get('reportSummary').textContent='Document preview unavailable.';get('reportMessage').textContent=['TypeError','SyntaxError'].includes(error.name)?'Preview could not load. Check the local connection and choose Preview to retry, or close and reopen this panel.':error.message;get('reportPreview').tHead.replaceChildren();get('reportPreview').tBodies[0].replaceChildren();}
  finally{if(!closed&&current===sequence)get('reportPreview').setAttribute('aria-busy','false');}
 });
 const invalidate=()=>{invalidDirectory=true;stale();get('reportMessage').textContent='Directory selection changed. Reopen Print Options after the results update.';};
 root.addEventListener('report-invalidate',invalidate,{once:true});
 root.addEventListener('report-close',()=>{closed=true;sequence++;controller?.abort();disable();root.removeEventListener('report-invalidate',invalidate);},{once:true});
 columns();disable();form.requestSubmit();
}};
