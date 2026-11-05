/* Shared report controls. Outputs always use the last successfully previewed filters. */
window.ReportWorkspace={mount(root=document){
  const config=JSON.parse(root.querySelector('.report-configuration')?.textContent||'null');
  const form=root.querySelector('#reportFilters');
  if(!form || !config)return;
  const byId=id=>root.querySelector('#'+id), kind=byId('reportKind'),mode=byId('reportMode');
  const print=byId('reportPrint'),word=byId('reportWord');
  let sequence=0,controller,selection=null,suggestionSequence=0,suggestionAbort,suggestionTimer,highlight=-1,options=[];
  let previewTimer,directoryInvalidated=false,lastEditedState='';
  const configurationState=()=>JSON.stringify([...form.querySelectorAll('input,select')].map(field=>[field.id||field.value,field.value,field.type==='checkbox'?field.checked:null]));
  function validateHouseholdChoice(){const input=byId('reportHouseholdSearch'),select=byId('reportHousehold');if(input&&!input.disabled)input.setCustomValidity(input.value.trim()&&!select.value?'Choose a household from the suggestions, or clear the field.':'');}
  function automaticPreview(){clearTimeout(previewTimer);if(!byId('contextDocument'))previewTimer=setTimeout(()=>{validateHouseholdChoice();validateResidentChoice();const from=byId('dateFrom'),to=byId('dateTo');if(byId('periodMode').value==='custom'&&(!from.value||!to.value||from.value>to.value)){byId('reportMessage').textContent='Enter a complete valid date range to preview.';return;}if(form.checkValidity())form.requestSubmit();},450);}
  const locked=config.locked||{};
  function disableOutputs(){for(const a of [print,word]){a.removeAttribute('href');a.setAttribute('aria-disabled','true');}}
  function category(){return kind.value==='households' && mode.value==='members'?'members':kind.value==='residents'&&byId('reportScope').value==='resident'?'individual':kind.value;}
  const effectiveCategory=()=>['members','individual'].includes(category())?'residents':category();
  function validateResidentChoice(){const input=byId('residentSearch');input.setCustomValidity(category()==='individual'&&!locked.resident_id&&!byId('residentId').value?'Choose an exact resident from the suggestions.':'');}
  function columns(){
    const effective=effectiveCategory(), box=byId('reportColumns');box.replaceChildren();
    const initialKind=config.initial.kind||'residents',initialEffective=initialKind==='households'&&config.initial.mode==='members'?'residents':initialKind;
    const wanted=(effective===initialEffective?config.initial.columns||'':'').split(',');
    for(const [key,label] of config.columns[effective]){
      const l=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=key;
      input.checked=(wanted[0]?wanted:config.defaults[effective]).includes(key)||config.required[effective].includes(key);
      input.dataset.sensitive=['mental_health_status','current_health_status'].includes(key)?'true':'false';
      input.disabled=config.required[effective].includes(key);l.append(input,document.createTextNode(' '+label));box.append(l);
    }
    const selected=[...box.querySelectorAll('input:checked')].map(input=>input.value),same=keys=>keys.length===selected.length&&keys.every(key=>selected.includes(key));
    byId('columnPreset').value=same(config.defaults[effective])?'default':same(config.required[effective])?'essential':effective==='residents'&&same(['full_name','id','age','occupation'])?'work':'custom';byId('columnPreset').querySelector('[data-resident-preset]').disabled=effective!=='residents';columnCount();
  }
  function columnCount(){const box=byId('reportColumns');byId('columnSelectionCount').textContent='· '+box.querySelectorAll('input:checked').length+' columns';}
  function setColumns(preset){const effective=effectiveCategory();for(const input of byId('reportColumns').querySelectorAll('input')){if(input.disabled)continue;input.checked=preset==='all'&&input.dataset.sensitive!=='true'||preset==='default'&&config.defaults[effective].includes(input.value)||preset==='work'&&['full_name','id','age','occupation'].includes(input.value);}byId('columnPreset').value=['default','essential','work'].includes(preset)?preset:'custom';columnCount();stale();}
  byId('columnPreset').addEventListener('change',()=>setColumns(byId('columnPreset').value));
  byId('allOptionalColumns').onclick=()=>setColumns('all');byId('clearOptionalColumns').onclick=()=>setColumns('essential');byId('defaultColumns').onclick=()=>{byId('columnPreset').value='default';setColumns('default');};
  function visibility(rebuild=false){
    const cat=category();
    for(const el of form.querySelectorAll('[data-for]')){
      el.hidden=!el.dataset.for.split(' ').includes(cat);
      for(const field of el.querySelectorAll('input,select')){field.disabled=el.hidden;if(el.hidden&&!locked[field.name]&&field.name){field.value=field.tagName==='SELECT'?field.options[0]?.value||'':'';}}
    }
    for(const el of form.querySelectorAll('[data-period]')){
      el.hidden=cat==='individual'||cat==='audit'||el.dataset.period!==byId('periodMode').value;
      for(const field of el.querySelectorAll('input,select')){field.disabled=el.hidden;if(el.hidden&&!locked[field.name]&&field.name){field.value=field.tagName==='SELECT'?field.options[0]?.value||'':'';}}
    }
    const auditPeriod=byId('auditPeriod')?.value||config.initial.audit_period||'all';
    if(byId('auditMonth')){byId('auditMonth').disabled=cat!=='audit'||auditPeriod!=='specific_month';byId('auditMonth').closest('div').hidden=byId('auditMonth').disabled;}
    if(byId('auditYear')){byId('auditYear').disabled=cat!=='audit'||auditPeriod!=='specific_year';byId('auditYear').closest('div').hidden=byId('auditYear').disabled;}
    const individual=cat==='individual';
    byId('individualScope').hidden=!individual||!!locked.resident_id;byId('residentId').disabled=!individual;byId('residentSearch').disabled=!individual||!!locked.resident_id;byId('residentSearch').required=individual&&!locked.resident_id;
    const chosen=config.selected_resident,summary=byId('selectedResidentSummary');summary.hidden=!individual;summary.textContent=individual?(locked.resident_id&&chosen?'Selected: '+chosen.full_name+' / Resident #'+chosen.id+' / House '+(chosen.house_number||'Not recorded'):byId('residentId').value?'Selected: '+byId('residentSearch').value:'Choose one exact resident. Typed text alone cannot generate an individual report.') :'';
    byId('reportSearchLabel').textContent=cat==='audit'?'Audit search':cat==='households'?'Household search':'Search residents';byId('reportSearch').placeholder=cat==='audit'?'Actor, event or record':cat==='households'?'Name, house no. or address':'Name or ID';
    byId('reportHousehold').required=cat==='members'||(cat==='households'&&mode.value==='profile')||(cat==='residents'&&byId('reportScope').value==='household');
    const householdHelp=byId('householdReportHelp');if(householdHelp)householdHelp.textContent=byId('reportHousehold').value?'Selected household records will appear in the chosen household document.':'Type a household name or house number to find its residents.';
    for(const id of ['dateFrom','dateTo'])byId(id).type=cat==='audit'?'datetime-local':'date';
    if(byId('periodHelp'))byId('periodHelp').textContent=cat==='audit'?'Audit events in Philippine time.':cat==='households'?'Household registration dates.':byId('dateBasis').value==='death'?'Reported death dates.':'Resident registration dates.';
    byId('scopeHint').textContent='Preview shows up to 100; outputs include every match.';
    if(rebuild)columns();
    for(const name of Object.keys(locked)){
      const control=form.elements.namedItem(name);if(control&&name!=='search'){control.disabled=true;if(['kind','mode','scope','household_id','resident_id'].includes(name))control.closest('.report-fields>div').hidden=true;}
    }
    byId('reportBoundScope').textContent=config.locked?.resident_id?'Fixed individual record. No other resident can be substituted.':config.locked?.household_id?'This report is limited to '+(byId('reportHousehold').value?byId('reportHousehold').selectedOptions[0]?.textContent:'the selected household (unavailable)')+'.' :cat==='individual'?'One selected resident; other resident filters do not apply.':'All matching records across pages.';
    if(byId('reportWorkspaceTitle'))byId('reportWorkspaceTitle').textContent=cat==='members'?'Household Member Report Builder':cat==='households'?'Household Report Builder':cat==='audit'?'Audit Report Builder':cat==='individual'?'Individual Resident Report Builder':'Resident Report Builder';
    if(Object.keys(locked).some(k=>!['kind','mode','scope','resident_id','household_id'].includes(k)))byId('reportBoundScope').textContent+='; applied directory criteria are fixed. Open the full Print Center to broaden them.';
    if(['month','year','date_from','date_to'].some(k=>locked[k]))byId('periodMode').disabled=true;
    if(byId('contextDocument')){
      byId('contextDocument').textContent=locked.resident_id?'Individual Resident Profile':cat==='members'?'Household Member List':cat==='households'&&mode.value==='profile'?'Household Profile':cat==='households'?'Household Directory':'Resident Directory';
      const filtered=Object.keys(locked).some(k=>!['kind','mode','scope','resident_id','household_id'].includes(k));
      byId('contextIncludes').textContent=(locked.resident_id?'Only the resident currently being viewed.':locked.household_id?'Only records from the household currently being viewed.':filtered?'Records matching the directory search and filters.':'All eligible records in this directory.')+(filtered&&locked.household_id?' Current directory filters also apply.':'');
    }
  }
  function initialize(){
    form.reset();selection=null;closeSuggestions();byId('reportSelection').textContent='';
    kind.value=config.initial.kind||'residents';mode.value=config.initial.mode||'summary';
    // Set date/datetime input types before assigning saved filter values.
    visibility();
    for(const [key,value] of Object.entries(config.initial))if(form.elements.namedItem(key))form.elements.namedItem(key).value=value;
    byId('periodMode').value=config.initial.date_from||config.initial.date_to?'custom':config.initial.month||config.initial.year?'month':'all';
    if(byId('reportMonth').value==='year')byId('reportMonth').value='';
    visibility(true);disableOutputs();window.enhanceRecordSelects?.(form);
    byId('residentSearch').value=config.selected_resident?config.selected_resident.full_name+' / Resident #'+config.selected_resident.id+' / House '+(config.selected_resident.house_number||'Not recorded'):'';validateResidentChoice();
    // Reset restores selects synchronously; synchronize their accessible inputs
    // before requestSubmit performs native constraint validation. No bubbling.
    for(const select of form.querySelectorAll('select[data-searchable]'))select.dispatchEvent(new Event('change'));
    filterChips();lastEditedState=configurationState();
    loadYearSuggestions();
  }
  async function loadYearSuggestions(){
    const cat=category(),queryKind=cat==='audit'?'audit':cat==='households'&&mode.value!=='members'?'households':'residents';
    const params=new URLSearchParams({kind:queryKind});if(queryKind==='residents')params.set('date_basis',byId('dateBasis').value||'registered');
    try{const response=await fetch('/api/report-years?'+params);if(!response.ok)return;const data=await response.json();const list=byId(queryKind==='audit'?'auditYearSuggestions':'reportYearSuggestions');if(!list)return;list.replaceChildren(...data.years.map(year=>new Option(year,year)));}catch(_){/* Native four-digit validation remains available offline. */}
  }
  function filterChips(){const box=byId('appliedFilterChips');if(!box)return;box.replaceChildren();for(const field of form.querySelectorAll('[name]')){if(!field.value||field.disabled&&!locked[field.name]||['kind','mode','scope'].includes(field.name)||field.name==='date_basis'&&field.value==='registered')continue;const label=form.querySelector('label[for="'+(field.dataset.enhanced?field.id+'Search':field.id)+'"]')?.textContent||field.name.replaceAll('_',' ');const fixed=Object.hasOwn(locked,field.name);const chip=document.createElement(fixed?'span':'button');if(!fixed)chip.type='button';chip.textContent=(fixed?'Fixed: ':'')+label+': '+(field.tagName==='SELECT'?field.selectedOptions[0]?.textContent:field.value)+(fixed?'':' (remove)');if(!fixed)chip.onclick=()=>{field.value=field.name==='date_basis'?'registered':'';field.dispatchEvent(new Event('input',{bubbles:true}));field.dispatchEvent(new Event('change',{bubbles:true}));};box.append(chip);}}
  function stale(force=false){const state=configurationState();if(!force&&state===lastEditedState)return false;lastEditedState=state;filterChips();columnCount();byId('matchingRecordCount').textContent='Refresh preview';sequence++;controller?.abort();disableOutputs();byId('reportPreview').classList.add('preview-stale');byId('reportMessage').textContent='Options changed. Preview again to refresh results and enable outputs.';return true;}
  function clearPreview(){byId('reportPreview').tHead.replaceChildren();byId('reportPreview').tBodies[0].replaceChildren();byId('reportSummary').textContent='Preview this selection to see its matching count.';}
  form.addEventListener('change',event=>{if(event.target===byId('residentId'))selection=null;if(byId('reportColumns').contains(event.target))byId('columnPreset').value='custom';const changed=stale();if(!changed)return;if([kind,mode,byId('reportScope'),byId('reportHousehold')].includes(event.target)){selection=null;byId('reportSelection').textContent='';if(!locked.resident_id){byId('residentId').value='';byId('residentSearch').value='';}if([kind,mode,byId('reportScope')].includes(event.target)){closeSuggestions();byId('residentSearch').dispatchEvent(new Event('blur'));}if(event.target===kind){if(!locked.scope)byId('reportScope').value='all_matching';if(!locked.household_id)byId('reportHousehold').value='';}clearPreview();}visibility([kind,mode].includes(event.target));if([kind,mode,byId('dateBasis')].includes(event.target))loadYearSuggestions();lastEditedState=configurationState();automaticPreview();});
  form.addEventListener('input',event=>{if(event.target.matches('select,input[type=checkbox],input[type=radio]'))return;if(stale())automaticPreview();});
  byId('reportReset').addEventListener('click',()=>{stale();initialize();if(form.checkValidity())form.requestSubmit();});
  for(const a of [print,word])a.addEventListener('click',event=>{if(a.getAttribute('aria-disabled')==='true'||a.dataset.activating){event.preventDefault();return;}a.dataset.activating='yes';a.setAttribute('aria-busy','true');setTimeout(()=>{delete a.dataset.activating;a.removeAttribute('aria-busy');},1000);});
  form.addEventListener('submit',async event=>{
    event.preventDefault();clearTimeout(previewTimer);if(directoryInvalidated){byId('reportMessage').textContent='Directory search changed. Reopen Print Options after the results update.';return;}visibility();validateHouseholdChoice();validateResidentChoice();if(category()!=='individual'&&byId('periodMode').value==='custom'&&(!byId('dateFrom').value||!byId('dateTo').value||byId('dateFrom').value>byId('dateTo').value)){stale();byId('reportMessage').textContent='Enter a complete valid date range to preview.';return;}if(!form.reportValidity())return;lastEditedState=configurationState();
    controller?.abort();controller=new AbortController();const current=++sequence;
    const params=new URLSearchParams(new FormData(form));params.delete('kind');
    for(const [key,value] of Object.entries(locked))if(!['kind','search'].includes(key))params.set(key,value);
    if(config.initial.context)params.set('context',config.initial.context);
    if(selection){params.delete('search');if(kind.value==='audit')params.set('search',selection.id);else if(selection.type==='residents'){params.set('resident_id',selection.id);if(kind.value==='residents'&&!locked.scope)params.set('scope','resident');}else params.set('household_id',selection.id);}
    params.set('columns',[...byId('reportColumns').querySelectorAll('input:checked')].map(i=>i.value).join(','));
    disableOutputs();byId('matchingRecordCount').textContent='Checking records?';byId('reportMessage').textContent='Loading matching records…';
    try{
      const response=await fetch('/api/preview/'+kind.value+'?'+params,{signal:controller.signal});
      const data=await response.json();if(current!==sequence)return;
      if(!response.ok)throw Error(data.error||'Unable to load report. Review filters and try again.');
      const head=byId('reportPreview').tHead,body=byId('reportPreview').tBodies[0];head.replaceChildren();body.replaceChildren();
      const cell=(tag,text)=>{const node=document.createElement(tag);node.textContent=text??'Not recorded';return node;};
      if(category()==='individual'&&data.total===1){const tr=document.createElement('tr');tr.append(cell('th','Information'),cell('th','Details'));head.append(tr);for(const item of data.profile_fields){const row=document.createElement('tr');row.append(cell('th',item.label),cell('td',item.value||'Not recorded'));body.append(row);}}
      else if(kind.value==='households'&&mode.value==='profile'&&data.total===1){const tr=document.createElement('tr');tr.append(cell('th','Household information'),cell('th','Details'));head.append(tr);for(const item of data.profile_fields){const row=document.createElement('tr');row.append(cell('th',item.label),cell('td',item.value||'Not recorded'));body.append(row);}const section=document.createElement('tr'),sectionCell=cell('th','Household members');sectionCell.colSpan=4;section.append(sectionCell);body.append(section);const membersHead=document.createElement('tr');for(const label of ['Resident ID','Full name','Status','Relationship to head'])membersHead.append(cell('th',label));body.append(membersHead);for(const member of data.profile_members||[]){const row=document.createElement('tr');for(const key of ['id','full_name','status','relationship_to_head'])row.append(cell('td',member[key]||'Not recorded'));body.append(row);}if(!(data.profile_members||[]).length){const row=document.createElement('tr'),empty=cell('td','No household members are recorded.');empty.colSpan=4;row.append(empty);body.append(row);}}
      else{const tr=document.createElement('tr');for(const c of data.columns){const th=document.createElement('th');th.scope='col';th.textContent=c.label;tr.append(th);}head.append(tr);for(const row of data.items){const tr=document.createElement('tr');for(const c of data.columns){const td=document.createElement('td');td.textContent=row[c.key]??'Not recorded';tr.append(td);}body.append(tr);}}
      if(category()==='individual'&&data.total===1){const resident=data.items[0];byId('selectedResidentSummary').textContent='Selected: '+resident.full_name+' / Resident #'+resident.id+(resident.household_number?' / House '+resident.household_number:'');}
      filterChips();byId('reportSummary').textContent=data.summary.replace(/Household ID: \d+/g,()=>"Household: "+(byId('reportHousehold').value?byId('reportHousehold').selectedOptions[0]?.textContent:'Selected household'));byId('matchingRecordCount').textContent=data.total+' matching records';byId('reportPreview').classList.remove('preview-stale');
      byId('reportMessage').textContent=data.total===0?'No matching records. Change the filters to generate an output.':data.sample?`Showing ${data.shown} of ${data.total}. Print and Word include all ${data.total} matches.`:`Showing all ${data.total} matching records.`;
      if(data.total){print.href='/reports/print/'+kind.value+'?'+params+'&autoprint=1';word.href=({residents:'/print_all_members',households:'/print_households_report',audit:'/print_audit_logs_report'})[kind.value]+'?'+params;for(const a of [print,word])a.setAttribute('aria-disabled','false');}
    }catch(error){if(error.name==='AbortError'||current!==sequence)return;byId('matchingRecordCount').textContent='Preview unavailable';byId('reportSummary').textContent='Report unavailable';byId('reportMessage').textContent=error.message;byId('reportPreview').tHead.replaceChildren();byId('reportPreview').tBodies[0].replaceChildren();}
  });
  const search=byId('reportSearch'),list=byId('reportSuggestions');
  function closeSuggestions(){suggestionSequence++;suggestionAbort?.abort();clearTimeout(suggestionTimer);list.hidden=true;search.setAttribute('aria-expanded','false');search.removeAttribute('aria-activedescendant');highlight=-1;options=[];}
  function choose(index){const item=options[index];if(!item)return;selection=item;if(item.type==='residents'){byId('residentId').value=item.id;byId('residentSearch').value=item.label;if(kind.value==='residents'&&!locked.scope)byId('reportScope').value='resident';}else if(item.type==='households'&&!locked.household_id)byId('reportHousehold').value=item.id;visibility();search.value=item.label;byId('reportSelection').textContent='Exact selection: '+item.label;closeSuggestions();stale();clearPreview();}
  search.addEventListener('input',()=>{
    if(selection?.type==='households'&&!locked.household_id)byId('reportHousehold').value='';
    if(selection?.type==='residents'&&!locked.scope)byId('reportScope').value=config.initial.scope||'all_matching';
    selection=null;visibility();byId('reportSelection').textContent='Typed text searches all matching records; choose a suggestion for one exact selection.';
    if(!locked.resident_id){byId('residentId').value='';byId('residentSearch').value='';}
    closeSuggestions();const term=search.value.trim();if(!term)return;
    const serial=++suggestionSequence;suggestionTimer=setTimeout(async()=>{
      suggestionAbort=new AbortController();list.replaceChildren();list.hidden=false;list.textContent='Loading suggestions?';search.setAttribute('aria-expanded','true');
      const params=new URLSearchParams({kind:kind.value,q:term});for(const key of ['mode','scope','household_id','resident_id']){const value=locked[key]||form.elements.namedItem(key)?.value;if(value)params.set(key,value);}if(config.initial.context)params.set('context',config.initial.context);
      try{const response=await fetch('/api/report-suggestions?'+params,{signal:suggestionAbort.signal});if(!response.ok)throw Error();const data=await response.json();if(serial!==suggestionSequence)return;options=data.items;list.replaceChildren();
        if(!options.length){list.textContent='No suggestions. Preview to search the typed text.';return;}
        options.forEach((item,i)=>{const el=document.createElement('div');el.id='report-suggestion-'+i;el.role='option';el.setAttribute('aria-selected','false');el.textContent=item.label;el.addEventListener('mousedown',e=>{e.preventDefault();choose(i);});list.append(el);});
      }catch(error){if(error.name!=='AbortError'&&serial===suggestionSequence)list.textContent='Suggestions unavailable. You can still preview matching text.';}
    },250);
  });
  search.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!list.hidden){event.preventDefault();event.stopPropagation();closeSuggestions();return;}
    if(['ArrowDown','ArrowUp'].includes(event.key)&&!list.hidden&&options.length){event.preventDefault();highlight=(highlight+(event.key==='ArrowDown'?1:-1)+options.length)%options.length;[...list.children].forEach((el,i)=>el.setAttribute('aria-selected',i===highlight?'true':'false'));search.setAttribute('aria-activedescendant','report-suggestion-'+highlight);list.children[highlight]?.scrollIntoView({block:'nearest'});}
    if(event.key==='Enter'&&!list.hidden&&highlight>=0){event.preventDefault();choose(highlight);}
    if(event.key==='Tab')closeSuggestions();
  });
  search.addEventListener('blur',()=>setTimeout(closeSuggestions,120));
  const invalidateDirectory=()=>{directoryInvalidated=true;stale(true);byId('reportMessage').textContent='Directory search changed. Reopen Print Options after the results update.';};
  root.addEventListener('report-close',()=>{sequence++;suggestionSequence++;controller?.abort();suggestionAbort?.abort();clearTimeout(suggestionTimer);clearTimeout(previewTimer);disableOutputs();closeSuggestions();root.removeEventListener('report-invalidate',invalidateDirectory);},{once:true});
  root.addEventListener('report-invalidate',invalidateDirectory,{once:true});
  initialize();if(form.checkValidity())form.requestSubmit();
}};
document.addEventListener('DOMContentLoaded',()=>{if(document.querySelector('.report-configuration'))window.ReportWorkspace.mount(document);});
