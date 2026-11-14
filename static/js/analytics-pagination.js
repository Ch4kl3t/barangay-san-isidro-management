/* Independent API pages; totals and chart summaries always describe all matches. */
const analyticsPages={residents:1,households:1};
const analyticsFilterIds=['filterEvent','filterGender','filterStatus','filterMonth','filterYear','filterHouseholdSize','filterHouseholdOccupancy','filterHouseholdYear','filterHouseholdBasis','filterHouseholdSort'];
function restoreAnalyticsPages(){
 const params=new URLSearchParams(location.search);
 for(const key of Object.keys(analyticsPages)){const value=Number(params.get(key+'_page'));analyticsPages[key]=Number.isSafeInteger(value)&&value>0?value:1;}
 const group=params.get('household_group');
 activeHHTab=document.getElementById('filterHouseholdBasis')?.value||'members';
 householdCard=['total','average','largest','single'].includes(group)?group:'total';
}
function saveAnalyticsPages(replace=false){
 const url=new URL(location.href);
 for(const id of analyticsFilterIds){const value=document.getElementById(id)?.value||'',base=id==='filterEvent'?'registered':id==='filterHouseholdBasis'?'members':id==='filterHouseholdSort'?'asc':'';if(value&&value!==base)url.searchParams.set(id,value);else url.searchParams.delete(id);}
 for(const [key,page] of Object.entries(analyticsPages)){if(page>1)url.searchParams.set(key+'_page',page);else url.searchParams.delete(key+'_page');}
 for(const [key,value,base] of [['household_group',householdCard,'total']]){if(value!==base)url.searchParams.set(key,value);else url.searchParams.delete(key);}
 if(url.href!==location.href)history[replace?'replaceState':'pushState'](null,'',url);
}
function updateAnalyticsPages(pagination){
 for(const key of Object.keys(analyticsPages)){
  const state=pagination[key],nav=document.getElementById(key+'Pagination');
  analyticsPages[key]=state.page;
  nav.querySelector('[role=status]').textContent=`Page ${state.page} of ${state.pages} · ${state.total} matching records`;
  nav.querySelector('[data-direction="-1"]').disabled=state.page<=1;
  nav.querySelector('[data-direction="1"]').disabled=state.page>=state.pages;
 }
 saveAnalyticsPages(true);
}
function installAnalyticsPages(){
 for(const key of Object.keys(analyticsPages))document.getElementById(key+'Pagination').addEventListener('click',event=>{
  const button=event.target.closest('button[data-direction]');if(!button||button.disabled)return;
  analyticsPages[key]+=Number(button.dataset.direction);saveAnalyticsPages();loadDashboard();
 });
}
