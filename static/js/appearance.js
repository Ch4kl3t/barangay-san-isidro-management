/* Runs before page paint. Appearance is a browser preference, never account data. */
(() => {
 if(window.officeAppearance)return; // Keep one theme owner if a shared fragment loads twice.
 const key='barangay-appearance',allowed=['light','dark','system'],media=matchMedia('(prefers-color-scheme: dark)');
 let chartRegistered=false;
 let preference='light';try{const saved=localStorage.getItem(key);if(allowed.includes(saved))preference=saved;}catch(error){}
 const effective=()=>preference==='system'?(media.matches?'dark':'light'):preference;
 function apply(){
  document.documentElement.dataset.theme=effective();document.documentElement.style.colorScheme=effective();
  document.querySelectorAll('input[name=appearance]').forEach(input=>{input.checked=input.value===preference;});
  if(window.Chart)for(const chart of Object.values(Chart.instances))chart.update('none');
  document.dispatchEvent(new CustomEvent('appearancechange',{detail:{preference,theme:effective()}}));
 }
 window.officeAppearance={get preference(){return preference;},set(value){if(!allowed.includes(value))return;preference=value;let stored=true;try{localStorage.setItem(key,value);}catch(error){stored=false;}apply();const status=document.getElementById('appearanceStatus');if(status)status.textContent=stored?'Appearance saved.':'Appearance applied for this page; browser storage is unavailable.';}};
 apply();media.addEventListener('change',()=>{if(preference==='system')apply();});
 window.addEventListener('storage',event=>{if(event.key===key){preference=allowed.includes(event.newValue)?event.newValue:'light';apply();}});
 document.addEventListener('DOMContentLoaded',()=>{apply();document.querySelectorAll('input[name=appearance]').forEach(input=>input.addEventListener('change',()=>officeAppearance.set(input.value)));installChartTheme();});
 // Chart.js keeps its data, types and animation. Dark surfaces receive readable
 // labels and equivalent brighter series colors; light restores original colors.
 function installChartTheme(){
  if(!window.Chart||chartRegistered)return;
  chartRegistered=true;
  const original=new WeakMap(),series=new WeakMap();
  const bright=color=>typeof color==='string'?({'#1b3a57':'#a8cff0','#2e86c1':'#68b8ee','#c0392b':'#ff9f94','#e67e22':'#ffbf79'}[color.toLowerCase()]||color):color;
  Chart.register({id:'officeAppearance',beforeUpdate(chart){
   if(!original.has(chart))original.set(chart,{legend:chart.options.plugins?.legend?.labels?.color,scales:Object.fromEntries(Object.entries(chart.options.scales||{}).map(([key,scale])=>[key,{ticks:scale.ticks?.color,grid:scale.grid?.color,title:scale.title?.color}]))});
   const saved=original.get(chart),dark=effective()==='dark';
   for(const dataset of chart.data.datasets){
    if(!series.has(dataset))series.set(dataset,Object.fromEntries(['borderColor','backgroundColor','pointBackgroundColor'].map(key=>[key,dataset[key]])));
    for(const [key,color] of Object.entries(series.get(dataset)))dataset[key]=dark?(Array.isArray(color)?color.map(bright):bright(color)):color;
   }
   if(chart.options.plugins?.legend?.labels)chart.options.plugins.legend.labels.color=dark?'#dce7f5':saved.legend;
   for(const [key,scale] of Object.entries(chart.options.scales||{})){const prior=saved.scales[key]||{};if(scale.ticks)scale.ticks.color=dark?'#c3d3e5':prior.ticks;if(scale.grid)scale.grid.color=dark?'#31465f':prior.grid;if(scale.title)scale.title.color=dark?'#dce7f5':prior.title;}
  },afterUpdate(chart){if(chart.canvas.id==='mainLineChart')setTimeout(()=>{const legend=document.getElementById('legendLine');if(legend)legend.style.background=chart.data.datasets[0]?.borderColor||'';},0);}});
 }
 document.addEventListener('load',event=>{if(event.target.tagName==='SCRIPT')installChartTheme();},true);
 window.addEventListener('load',installChartTheme);
})();
