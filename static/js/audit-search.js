/* Existing authorized actor suggestions; explicit general audit-search commitment. */
(() => {
 const form=document.querySelector('.audit-server-filters'),input=form?.querySelector('[data-explicit-search]');if(!input)return;
 const period=form.querySelector('[name="audit_period"]'),syncPeriod=()=>{for(const label of form.querySelectorAll('[data-audit-specific]')){const active=label.dataset.auditSpecific===(period.value==='specific_month'?'month':period.value==='specific_year'?'year':'');label.hidden=!active;label.querySelector('input').disabled=!active;}};
 period.addEventListener('change',syncPeriod);syncPeriod();
 fetch('/api/report-years?kind=audit').then(response=>response.ok?response.json():null).then(data=>{const list=document.getElementById('auditLogYearSuggestions');if(list&&data)list.replaceChildren(...data.years.map(year=>new Option(year,year)));}).catch(()=>{});
 input.dataset.committedValue=input.value;input.autocomplete='off';input.setAttribute('aria-label','Search audit events');
 const list=document.createElement('div'),target=document.createElement('input'),status=document.createElement('p');
 list.id='audit-search-options';list.className='record-options';list.hidden=true;list.role='listbox';target.type='hidden';target.id='auditSearchChoice';status.id='auditSearchStatus';status.role='status';status.className='report-note';status.textContent='Choose an actor suggestion or press Enter to search all audit text.';
 const source=new URLSearchParams(location.search);for(const key of ['search','q','page'])source.delete(key);source.set('kind','audit');
 input.dataset.recordCombobox='';input.dataset.source='/api/report-suggestions?'+source;input.dataset.target=target.id;input.dataset.status=status.id;input.dataset.richOptions='actors';
 input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');input.setAttribute('aria-controls',list.id);
 const row=input.closest('.audit-search-row');row.classList.add('workflow-search');input.after(target,list,status);window.mountRecordComboboxes?.(row);
 function commit(){if(input.matches(':invalid'))return;form.dataset.commitSearch='true';form.requestSubmit();}
 target.addEventListener('change',()=>{if(target.value)commit();});
 input.addEventListener('input',()=>{delete form.dataset.commitSearch;});
 input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.defaultPrevented&&!event.isComposing){event.preventDefault();commit();}});
 const button=document.createElement('button');button.type='button';button.className='reset-btn audit-search-submit';button.textContent='Search';button.onclick=commit;row.append(button);
})();
