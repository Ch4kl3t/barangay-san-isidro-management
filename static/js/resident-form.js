document.addEventListener('DOMContentLoaded',()=>{
 const form=document.querySelector('.resident-editor form');if(!form)return;
 const note=document.createElement('p');note.className='helper-text';note.textContent='Fields marked * are required. Optional health information is visible only to authorized administrators.';form.prepend(note);
 const status=form.querySelector('[name=status]'),date=form.querySelector('[name=death_date]');
 const sync=()=>{if(date){date.closest('.death-date-field').hidden=status?.value!=='Deceased'&&!date.value;}};
 status?.addEventListener('change',sync);date?.addEventListener('change',sync);sync(); // Keep a conflicting saved date visible for explicit correction.
 form.querySelectorAll('input,select,textarea').forEach((field,index)=>{
  if(field.type==='hidden'||field.type==='checkbox')return;
  if(!field.id)field.id='resident-field-'+index;
  const label=field.closest('.form-group')?.querySelector('label');if(label){label.htmlFor=field.dataset.enhanced?field.id+'Search':field.id;if(field.required&&!label.dataset.requiredMarked){label.append(document.createTextNode(' *'));label.dataset.requiredMarked='yes';}}
 });
});
