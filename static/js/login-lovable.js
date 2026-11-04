/* Presentation only: the existing native Flask POST and busy-state handler own login. */
(() => {
 if(!document.body.classList.contains('login-experience'))return;
 const password=document.getElementById('password'),toggle=document.getElementById('togglePassword');
 if(password&&toggle){
  toggle.hidden=false;
  toggle.addEventListener('click',()=>{
   const visible=password.type==='password';password.type=visible?'text':'password';
   toggle.setAttribute('aria-label',visible?'Hide password':'Show password');toggle.setAttribute('aria-pressed',String(visible));
   toggle.querySelector('[data-eye=show]').hidden=visible;toggle.querySelector('[data-eye=hide]').hidden=!visible;
  });
  // A returned browser history page should not leave a formerly revealed secret visible.
  window.addEventListener('pageshow',()=>{password.type='password';toggle.setAttribute('aria-label','Show password');toggle.setAttribute('aria-pressed','false');toggle.querySelector('[data-eye=show]').hidden=false;toggle.querySelector('[data-eye=hide]').hidden=true;});
 }
 const theme=document.querySelector('.login-theme');
 if(theme&&window.officeAppearance){
  theme.hidden=false;
  const sync=()=>{const dark=document.documentElement.dataset.theme==='dark';theme.querySelectorAll('[data-theme-choice]').forEach(button=>button.setAttribute('aria-pressed',String((button.dataset.themeChoice==='dark')===dark)));};
  theme.querySelectorAll('[data-theme-choice]').forEach(button=>button.addEventListener('click',()=>window.officeAppearance.set(button.dataset.themeChoice)));
  document.addEventListener('appearancechange',sync);sync();
 }
})();
