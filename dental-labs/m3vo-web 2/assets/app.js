/* M3VO site interactions */
(function(){
  "use strict";

  /* ---- desktop mega-menu (hover + click, keyboard accessible) ---- */
  var items = document.querySelectorAll('.nav-item.has-mega');
  items.forEach(function(item){
    var trigger = item.querySelector('.nav-link');
    var close = function(){ item.classList.remove('open'); trigger.setAttribute('aria-expanded','false'); };
    var open  = function(){ items.forEach(function(o){ if(o!==item){o.classList.remove('open'); var t=o.querySelector('.nav-link'); if(t) t.setAttribute('aria-expanded','false');} }); item.classList.add('open'); trigger.setAttribute('aria-expanded','true'); };
    item.addEventListener('mouseenter', open);
    item.addEventListener('mouseleave', close);
    trigger.addEventListener('click', function(e){ e.preventDefault(); item.classList.contains('open') ? close() : open(); });
    trigger.addEventListener('keydown', function(e){ if(e.key==='Escape'){ close(); trigger.focus(); } });
  });
  document.addEventListener('click', function(e){
    if(!e.target.closest('.nav-item.has-mega')){ items.forEach(function(o){ o.classList.remove('open'); var t=o.querySelector('.nav-link'); if(t) t.setAttribute('aria-expanded','false'); }); }
  });

  /* ---- mobile panel ---- */
  var burger = document.querySelector('.hamburger');
  var panel  = document.querySelector('.mobile-panel');
  if(burger && panel){
    burger.addEventListener('click', function(){
      var isOpen = panel.classList.toggle('open');
      burger.setAttribute('aria-expanded', isOpen ? 'true':'false');
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });
    panel.querySelectorAll('.m-head').forEach(function(h){
      h.addEventListener('click', function(){ h.parentElement.classList.toggle('open'); });
    });
    panel.querySelectorAll('a').forEach(function(a){
      a.addEventListener('click', function(){ panel.classList.remove('open'); document.body.style.overflow=''; burger.setAttribute('aria-expanded','false'); });
    });
  }

  /* ---- hero flow connector draw-in on load ---- */
  if(!window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    window.addEventListener('load', function(){
      var conns = document.querySelectorAll('.hero .flow-conn');
      conns.forEach(function(c,i){ setTimeout(function(){ c.classList.add('animate'); }, 260 + i*230); });
    });
  }

  /* ---- contact form -> Cloudflare Pages Function ---- */
  var form = document.getElementById('m3vo-contact');
  if(form){
    form.addEventListener('submit', function(e){
      e.preventDefault();
      var ok = document.getElementById('form-ok');
      var err = document.getElementById('form-err');
      var btn = form.querySelector('button[type="submit"]');
      var orig = btn ? btn.textContent : '';
      if(err){ err.style.display='none'; }
      if(btn){ btn.disabled=true; btn.textContent='Sending…'; }
      fetch('/api/contact', { method:'POST', body:new FormData(form), headers:{'accept':'application/json'} })
        .then(function(res){ return res.json().catch(function(){return {};}).then(function(d){ return {res:res,d:d}; }); })
        .then(function(o){
          if(o.res.ok && o.d && o.d.ok){
            form.style.display='none';
            if(ok){ ok.classList.add('show'); ok.scrollIntoView({behavior:'smooth', block:'center'}); }
          } else {
            throw new Error((o.d && o.d.error) || ('Something went wrong ('+o.res.status+').'));
          }
        })
        .catch(function(ex){
          if(btn){ btn.disabled=false; btn.textContent=orig; }
          if(err){ err.textContent = ex.message + ' You can also email hello@m3vo.com directly.'; err.style.display='block'; }
        });
    });
  }

  /* ---- current year ---- */
  var y = document.getElementById('yr'); if(y) y.textContent = new Date().getFullYear();
})();
