/* Refresh the installed offline integration, including dynamically inserted dialogs. */
(() => {
 const refresh=()=>{if(typeof loadIcons==='function')loadIcons();document.querySelectorAll('[data-lucide] svg').forEach(svg=>{svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');});};
 refresh();new MutationObserver(records=>{if(records.some(r=>Array.from(r.addedNodes).some(n=>n.nodeType===1&&(n.matches?.('[data-lucide]')||n.querySelector?.('[data-lucide]')))))refresh();}).observe(document.body,{childList:true,subtree:true});
})();
