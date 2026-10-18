/* ===================== SolarFlow =====================
   SolarFlow.update({
     pv1:{v,a,w?}, pv2:{v,a,w?},
     ctrl:{state, temp, w?},            // state: "Bulk" | "Absorption" | "Float" | "Idle" ...
     battery:{soc, v, a, temp},         // a: + charging, - discharging
     inverter:{ac_w, dc_w?}
   })
   SolarFlow.start({url:'/api/solar', interval:2000})   // poll your Flask endpoint
   SolarFlow.demo()                                     // simulated data for testing
================================================================ */
(function(){
  const root=document.getElementById('solar-flow'); if(!root) return;
  const cfg={maxPv:1000,maxInv:2000,maxLoad:150,url:null,interval:2000,staleMs:15000};
  const $=s=>root.querySelector(s), $$=s=>root.querySelectorAll(s);
  const T={},D={},els={}; let lastSeen=0,timer=null,demoTimer=null;
  const KEYS=['lw','pv1w','pv1v','pv1a','pv2w','pv2v','pv2a','cw','ctemp','bsoc','bv','ba','btemp','bw','idc','iac','ieff','lpct','pvt','seff'];
  KEYS.forEach(k=>{T[k]=0;D[k]=0;els[k]=[...$$('[data-k="'+k+'"]')]});
  const num=(x,f=0)=>(typeof x==='number'&&isFinite(x))?x:f;

  function fmt(el,v){
    const d=+el.dataset.d||0; let s=Math.abs(v)<.5*Math.pow(10,-d)?(0).toFixed(d):v.toFixed(d);
    if(el.dataset.sign&&v>=Math.pow(10,-d)) s='+'+s; el.textContent=s;
  }
  (function tick(){ // smooth number tweening
    for(const k of KEYS){ const diff=T[k]-D[k];
      if(Math.abs(diff)>.001){ D[k]+=diff*.12; if(Math.abs(T[k]-D[k])<.005)D[k]=T[k]; els[k].forEach(e=>fmt(e,D[k])); } }
    requestAnimationFrame(tick);
  })();

  function flow(id,w,max){
    const el=$('#sf-'+id), r=Math.min(Math.max(w/max,0),1);
    if(w<3){ el.classList.add('off'); return; }
    el.classList.remove('off');
    el.style.setProperty('--d',(2.8-2.1*r).toFixed(2)+'s');   // faster with more power
    el.style.strokeWidth=(3.5+3*r).toFixed(1);
  }
  function glow(id,color,r){
    $('#sf-n-'+id).style.filter=r>.02?'drop-shadow(0 0 '+(4+22*r).toFixed(0)+'px '+color+')':'none';
  }

  function update(d){
    d=d||{}; lastSeen=Date.now(); root.classList.remove('offline');
    const p1=d.pv||d.pv1||{},p2={},c=d.ctrl||{},b=d.battery||{},i=d.inverter||{},L=d.load||{};
    const pv1w=num(p1.w,num(p1.v)*num(p1.a)), pv2w=num(p2.w,num(p2.v)*num(p2.a)), pvt=pv1w+pv2w;
    const cw=num(c.w,pvt), bv=num(b.v), ba=num(b.a), bw=bv*ba;
    const iac=num(i.ac_w), idc=num(i.dc_w,iac/.9);
    Object.assign(T,{pv1w,pv1v:num(p1.v),pv1a:num(p1.a),pv2w,pv2v:num(p2.v),pv2a:num(p2.a),cw,
      ctemp:num(c.temp),bsoc:num(b.soc),bv,ba,btemp:num(b.temp),bw,idc,iac,lpct:iac/cfg.maxInv*100,
      lw:num(L.w),pvt,seff:pvt>5?Math.min(iac/pvt*100,100):0,ieff:idc>5?Math.min(iac/idc*100,100):0});
    $$('[data-k="cstate"]').forEach(e=>e.textContent=c.state||'—');

    flow('f1',pv1w,cfg.maxPv); flow('f3',cw,cfg.maxPv); flow('f6',L.on?Math.max(num(L.w),8):0,cfg.maxLoad);
    flow('f4',idc,cfg.maxInv); flow('f5',iac,cfg.maxInv);
    glow('pv1','#ffb020',pv1w/cfg.maxPv); glow('dc','#ff8a5b',L.on?Math.max(num(L.w)/cfg.maxLoad,.3):0);
    glow('mppt','#3ddc97',cw/cfg.maxPv); glow('inv','#7aa2ff',idc/cfg.maxInv); glow('load','#c4a1ff',iac/cfg.maxInv);
    glow('bat',ba>0?'#3ddc97':'#38bdf8',Math.abs(bw)/1000);
    $$('[data-sun]').forEach(s=>s.style.opacity=Math.min(pv1w/cfg.maxPv*1.4,1));

    const soc=Math.min(Math.max(num(b.soc),0),100), f=$('#sf-soc');
    f.setAttribute('width',(154*soc/100).toFixed(1));
    f.style.fill=soc<20?'var(--warn)':soc<50?'var(--sun)':'var(--mppt)';
    const bs=$('#sf-bstate');
    if(ba>0.3){bs.textContent='Charging';bs.style.fill='var(--mppt)'}
    else if(ba<-0.3){bs.textContent='Discharging';bs.style.fill='var(--sun)'}
    else{bs.textContent='Idle';bs.style.fill='var(--mut)'}
    const ls=$('#sf-lstate'), lsrc=$('#sf-lsrc');
    ls.textContent=L.on?'ON':'OFF'; ls.style.fill=L.on?'var(--dc)':'var(--mut)';
    lsrc.textContent=L.source||(L.on?'On':'Off');
    $('[data-status]').textContent='Live · '+new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  }

  setInterval(()=>{ if(lastSeen&&Date.now()-lastSeen>cfg.staleMs){root.classList.add('offline');$('[data-status]').textContent='No data'} },3000);

  function start(o){
    Object.assign(cfg,o||{}); clearInterval(timer);
    const pull=()=>fetch(cfg.url,{cache:'no-store'}).then(r=>r.json()).then(d=>update(cfg.adapt?cfg.adapt(d):d)).catch(()=>{});
    pull(); timer=setInterval(pull,cfg.interval);
  }
  function demo(){
    clearInterval(demoTimer); let soc=62;
    demoTimer=setInterval(()=>{
      const t=Date.now()/1000, sun=Math.max(0,Math.sin(t/9)*1.05),
        p1=sun*430,p2=sun*380*(.9+.1*Math.sin(t/3)),pv=p1+p2,
        load=Math.max(0,420+350*Math.sin(t/5)*Math.sin(t/7)),dc=load/.9,
        net=pv*.97-dc, a=net/13.2; soc=Math.min(100,Math.max(5,soc+net/2560/3600*100*40));
      update({pv:{v:sun>.02?36.5:0,a:pv/36.5},load:{on:sun>.5,w:sun>.5?18:0,source:sun>.5?'Auto · temp trigger':'Off'},
        ctrl:{state:pv<5?'Standby':soc>95?'Float':soc>85?'Absorption':'Bulk (MPPT)',temp:34+sun*9,w:pv*.97},
        battery:{soc,v:12.9+soc/100*.7,a,temp:27},inverter:{ac_w:load,dc_w:dc}});
    },1000);
  }
  window.SolarFlow={update,start,demo,config:cfg};
})();

/* ---- wired to your Flask /api/data (adapter maps your JSON to the component) ---- */
SolarFlow.start({
  url:'/api/data', interval:3000, maxPv:1000, maxInv:2000, maxLoad:150,   // maxPv = peak watts of BOTH panels
  adapt(d){
    const s=d.solar||{}, b=d.bms||{};
    const on=!!s.load_status, loadW=s.load_w||0, ctrlOut=s.w_bat||0;
    const dc=Math.max(0,ctrlOut-loadW-(b.w_total||0));       // estimate of inverter DC draw
    const label=!on?'Off':String(s.source||'').toUpperCase().includes('THERMAL')?'Auto · temp trigger':'Manual';
    return {
      pv:{v:s.v_pv,a:s.a_pv,w:s.w_pv},
      ctrl:{state:s.state,temp:s.device_t,w:ctrlOut},
      battery:{soc:b.soc_avg,v:b.v_combined,a:b.a_total,temp:s.battery_t},
      inverter:{dc_w:dc,ac_w:dc*0.9},
      load:{on,w:loadW,source:label}
    };
  }
});
