/* Visual tooltip lives outside tables; the original description stays available to AT. */
(() => {
 const wrappers=[...document.querySelectorAll('.household-delete-blocked')];
 if(!wrappers.length)return;
 const tip=document.createElement('div');
 tip.className='household-delete-tooltip';tip.hidden=true;tip.setAttribute('aria-hidden','true');
 const topLayer=typeof tip.showPopover==='function';
 if(topLayer)tip.setAttribute('popover','manual');
 document.body.append(tip);
 let active=null;
 function place(){
  if(!active)return;
  const viewport=window.visualViewport,margin=8;
  const left=viewport?.offsetLeft||0,top=viewport?.offsetTop||0;
  const width=viewport?.width||document.documentElement.clientWidth;
  const height=viewport?.height||window.innerHeight;
  tip.style.maxWidth=Math.max(1,width-margin*2)+'px';
  const anchor=active.getBoundingClientRect(),box=tip.getBoundingClientRect();
  const x=Math.max(left+margin,Math.min(anchor.right-box.width,left+width-box.width-margin));
  const below=anchor.bottom+margin;
  const preferred=below+box.height<=top+height-margin?below:anchor.top-box.height-margin;
  const y=Math.max(top+margin,Math.min(preferred,top+height-box.height-margin));
  tip.style.left=x+'px';tip.style.top=y+'px';
 }
 function hide(){
  if(topLayer&&!tip.hidden)tip.hidePopover();
  tip.hidden=true;active=null;
 }
 function show(wrapper){
  const description=document.getElementById(wrapper.getAttribute('aria-describedby'));
  if(!description)return;
  active=wrapper;tip.textContent=description.textContent;tip.hidden=false;
  if(topLayer&&!tip.matches(':popover-open'))tip.showPopover();
  place();
 }
 wrappers.forEach(wrapper=>{
  wrapper.addEventListener('mouseenter',()=>show(wrapper));
  wrapper.addEventListener('mouseleave',()=>{if(!wrapper.matches(':focus-within'))hide();});
  wrapper.addEventListener('focusin',()=>show(wrapper));
  wrapper.addEventListener('focusout',()=>{if(!wrapper.matches(':hover'))hide();});
  wrapper.addEventListener('pointerdown',()=>show(wrapper));
 });
 document.addEventListener('keydown',event=>{if(event.key==='Escape')hide();});
 // Dismiss before another control or confirmation dialog takes over interaction.
 const dismissOutside=event=>{if(active&&!active.contains(event.target))hide();};
 document.addEventListener('pointerdown',dismissOutside,true);
 document.addEventListener('focusin',dismissOutside,true);
 window.addEventListener('scroll',hide,true);
 window.addEventListener('resize',hide);
 window.visualViewport?.addEventListener('resize',hide);
 window.visualViewport?.addEventListener('scroll',hide);
 window.addEventListener('pageshow',hide);
 window.addEventListener('pagehide',hide);
})();
