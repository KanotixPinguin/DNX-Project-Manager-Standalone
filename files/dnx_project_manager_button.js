/* DNX_PROJECT_MANAGER_BUTTON_START */
(function(){
  "use strict";
  if(window.__dnxPmButton) return; window.__dnxPmButton = true;
  var BTN_ID = "dnx-project-manager-button", POS_KEY = "dnx.pm.btn.pos.v1";
  function getUrl(){ return window.DNX_PM_URL ? String(window.DNX_PM_URL) : (location.protocol + "//" + location.hostname + ":8094/"); }
  function loadPos(){ try{ var p = JSON.parse(localStorage.getItem(POS_KEY) || "null"); return (p && isFinite(p.left) && isFinite(p.top)) ? p : null; }catch(e){ return null; } }
  function savePos(p){ try{ if(p) localStorage.setItem(POS_KEY, JSON.stringify(p)); else localStorage.removeItem(POS_KEY); }catch(e){} }
  function build(){
    if(document.getElementById(BTN_ID)) return;
    var b = document.createElement("button"); b.id = BTN_ID; b.type = "button"; b.textContent = "📦 Projekte / Downloads";
    b.title = "Klick = Projekt-Manager öffnen · Ziehen = Button frei verschieben · Doppelklick = Zurücksetzen";
    b.style.cssText = "position:fixed;right:18px;bottom:52px;z-index:1000610;height:32px;padding:0 14px;border-radius:999px;border:1px solid #77eaff;background:#12394a;color:#fff;font:700 12.5px/30px 'Segoe UI',sans-serif;cursor:grab;user-select:none;touch-action:none;box-shadow:0 4px 16px rgba(0,0,0,.45);";
    document.body.appendChild(b);
    var p = loadPos();
    if(p){ b.style.right="auto"; b.style.bottom="auto"; b.style.left=Math.max(4,Math.min(window.innerWidth-180,Math.round(p.left)))+"px"; b.style.top=Math.max(4,Math.min(window.innerHeight-36,Math.round(p.top)))+"px"; }
    var dg=false,mv=false,sx=0,sy=0,ol=0,ot=0;
    b.addEventListener("pointerdown", function(e){ if(e.button!==undefined&&e.button!==0) return; dg=true;mv=false;var r=b.getBoundingClientRect();sx=e.clientX;sy=e.clientY;ol=r.left;ot=r.top;b.style.cursor="grabbing";try{b.setPointerCapture(e.pointerId);}catch(err){} });
    b.addEventListener("pointermove", function(e){ if(!dg) return; var dx=e.clientX-sx,dy=e.clientY-sy; if(!mv&&Math.abs(dx)+Math.abs(dy)<=5) return; mv=true; b.style.right="auto"; b.style.bottom="auto"; b.style.left=Math.max(4,Math.min(window.innerWidth-b.offsetWidth-4,Math.round(ol+dx)))+"px"; b.style.top=Math.max(4,Math.min(window.innerHeight-b.offsetHeight-4,Math.round(ot+dy)))+"px"; });
    function up(e){ if(!dg) return; dg=false; b.style.cursor="grab"; try{if(b.releasePointerCapture)b.releasePointerCapture(e.pointerId);}catch(err){} if(mv){ var r=b.getBoundingClientRect(); savePos({left:Math.round(r.left),top:Math.round(r.top)}); b.dataset.dnxSuppress="1"; setTimeout(function(){delete b.dataset.dnxSuppress;},220); } }
    b.addEventListener("pointerup", up); b.addEventListener("pointercancel", up);
    b.addEventListener("dblclick", function(e){ e.preventDefault(); e.stopPropagation(); savePos(null); b.style.left=""; b.style.top=""; b.style.right="18px"; b.style.bottom="52px"; });
    b.addEventListener("click", function(){ if(b.dataset.dnxSuppress) return; window.open(getUrl(), "_blank", "noopener"); });
  }
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", build, {once:true}); else build();
})();
/* DNX_PROJECT_MANAGER_BUTTON_END */
