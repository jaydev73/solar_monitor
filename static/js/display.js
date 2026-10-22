(function(){
  var MAX_PV=1000, MAX_AC=2000, POLL=5000, STALE=15000, HOLD=120000;
  var q=new URLSearchParams(location.search), key=q.get('key')||'', dbg=q.get('debug')==='1';
  var stage=document.getElementById('stage'), body=document.body;
  var last=0, data=null, cur=null, pend=null, tz, scale=1;
  var $=function(k){return document.querySelectorAll('[data-k="'+k+'"]')};
  function set(k,t){$(k).forEach(function(e){e.textContent=t})}
  function sgn(n,d){var s=Math.abs(n).toFixed(d);return (n>=0.05?'+':n<=-0.05?'\u2212':'')+s}
  function strip(s){return String(s||'').replace(/[^\x20-\x7E]/g,'').trim()}

  function fit(){var W=Math.max(960,Math.round(480*innerWidth/innerHeight));   // widen for 2.2:1 phone screens
    scale=Math.min(innerWidth/W,innerHeight/480);stage.style.width=W+'px';
    stage.style.transform='scale('+scale+') translate('+(-W/2)+'px,-240px)';
    stage.style.transformOrigin='0 0';stage.style.left='50%';stage.style.top='50%'}
  addEventListener('resize',fit);fit();

  var ICON={
    sun:'<circle cx="32" cy="28" r="12" fill="#ffb020"/>',
    moon:'<path d="M34 6a22 22 0 1 0 22 34a18 18 0 0 1-22-34z" fill="#dfe8ff"/>',
    cloud:'<path d="M14 48a10 10 0 0 1 1-20a15 15 0 0 1 29 3a9 9 0 0 1 0 17z" fill="#dbe7fb"/>',
    rain:'<path d="M14 36a10 10 0 0 1 1-20a15 15 0 0 1 29 3a9 9 0 0 1 0 17z" fill="#b9c8e6"/><path d="M20 44l-3 8M32 44l-3 8M44 44l-3 8" stroke="#38bdf8" stroke-width="3" stroke-linecap="round"/>',
    snow:'<path d="M14 36a10 10 0 0 1 1-20a15 15 0 0 1 29 3a9 9 0 0 1 0 17z" fill="#c9d6ee"/><g fill="#fff"><circle cx="20" cy="46" r="3"/><circle cx="32" cy="50" r="3"/><circle cx="44" cy="46" r="3"/></g>',
    storm:'<path d="M14 34a10 10 0 0 1 1-20a15 15 0 0 1 29 3a9 9 0 0 1 0 17z" fill="#9fb0cf"/><path d="M34 34l-8 12h7l-3 9l11-14h-8z" fill="#ffb020"/>',
    fog:'<path d="M14 32a10 10 0 0 1 1-20a15 15 0 0 1 29 3a9 9 0 0 1 0 17z" fill="#b9c8e6"/><path d="M12 42h40M18 50h34" stroke="#a9bddb" stroke-width="3" stroke-linecap="round"/>'};
  function wxIcon(c,day){var m=day?'sun':'moon',h;
    if(c===0)h=ICON[m];
    else if(c<=2)h=(day?'<circle cx="22" cy="20" r="9" fill="#ffb020"/>':'<path d="M26 6a14 14 0 1 0 14 22a11 11 0 0 1-14-22z" fill="#dfe8ff"/>')+ICON.cloud;
    else if(c===3)h=ICON.cloud;else if(c<=48)h=ICON.fog;
    else if(c<=67||(c>=80&&c<=82))h=ICON.rain;else if(c<=77||c===85||c===86)h=ICON.snow;else h=ICON.storm;
    document.getElementById('wxicon').innerHTML=h}

  function clock(){var d=new Date(),o={timeZone:tz};
    try{var p=new Intl.DateTimeFormat('en-US',{timeZone:tz,hour:'numeric',minute:'2-digit',hour12:true}).formatToParts(d),t={};
      p.forEach(function(x){t[x.type]=x.value});
      document.getElementById('clk').textContent=t.hour+':'+t.minute;document.getElementById('ampm').textContent=t.dayPeriod||'';
      document.getElementById('date').textContent=new Intl.DateTimeFormat('en-US',{timeZone:tz,weekday:'long',month:'short',day:'numeric'}).format(d)}
    catch(e){tz=undefined}
    var ago=last?Math.round((Date.now()-last)/1000):null;
    document.getElementById('upd').textContent=ago===null?'':'Updated '+ago+' s ago';
    var stale=!last||Date.now()-last>STALE;document.getElementById('stale').hidden=!stale;
    if(dbg){var x=document.getElementById('dbg');x.hidden=false;
      x.textContent='view '+innerWidth+'x'+innerHeight+'  scale '+scale.toFixed(2)+'  state '+cur+'\nage '+ago+'s  tz '+tz+'\n'+navigator.userAgent.slice(0,60)}}

  function flow(id,w,max){var e=document.getElementById(id);
    if(w<3){e.classList.add('off');return}
    e.classList.remove('off');e.style.setProperty('--d',(2.8-2.1*Math.min(w/max,1)).toFixed(2)+'s')}

  function want(d){var pv=d.pv.w||0,day=d.weather.is_day===1;
    if(!d.online.weather){var h=new Date().getHours();day=h>=7&&h<19}
    if(pv>=15)return'day';if(day)return'low';return pv<5?'night':'low'}
  function applyState(s){cur=s;body.className='st-'+s}

  function render(d){
    var w=d.weather,pv=d.pv,m=d.mppt,b=d.battery,i=d.inverter,f=d.fan;
    tz=d.tz||tz;
    var st=want(d),now=Date.now();
    if(cur===null)applyState(st);
    else if(st===cur)pend=null;
    else{if(!pend||pend.s!==st)pend={s:st,t:now};if(now-pend.t>=HOLD){applyState(st);pend=null}}
    set('temp',Math.round(w.temp_f));set('cond',w.condition);
    set('hl',w.hi!=null?'H '+Math.round(w.hi)+'\u00b0 \u00b7 L '+Math.round(w.lo)+'\u00b0':'');
    wxIcon(w.wmo_code,w.is_day===1);
    set('pv_w',Math.round(pv.w));set('pv_va',pv.v.toFixed(1)+' V \u00b7 '+pv.a.toFixed(1)+' A');
    set('mppt_w',Math.round(m.out_w));set('mppt_state',strip(m.state)||'Standby');
    set('fan_txt','Fan '+(f.on?'on'+(f.mode==='auto'?' \u00b7 auto':''):'off')+' \u00b7 '+Math.round(m.temp_c)+' \u00b0C');
    set('soc',Math.round(b.soc));set('bat_va',b.v.toFixed(1)+' V \u00b7 '+sgn(b.a,1)+' A');
    set('ac_w',Math.round(i.ac_w));set('ac_pct',Math.round(i.ac_w/MAX_AC*100)+'% of rating');
    var bars=document.querySelectorAll('#bars rect'),soc=b.soc;
    document.getElementById('bars').style.setProperty('--bc',soc<20?'#ff6b6b':soc<50?'#ffb020':'#3ddc97');
    bars.forEach(function(r,n){r.classList.toggle('on',soc>=(n+1)*25-12)});
    document.getElementById('mbox').setAttribute('stroke',m.out_w>=3?'#3ddc97':'#4f7a6c');
    flow('f1',pv.w,MAX_PV);flow('f2',m.out_w,MAX_PV);flow('f3',i.dc_w,MAX_AC);flow('f4',i.ac_w,MAX_AC);
    var s=strip(m.state),t;
    if(cur==='day')t='Harvesting \u00b7 '+(s||'Charging');
    else if(cur==='low')t='Low light'+(s?' \u00b7 '+s:'');
    else t=i.ac_w>=5?'Idle \u00b7 Night \u00b7 Battery supplying loads':'Idle \u00b7 Night';
    document.getElementById('status').textContent=t}

  function poll(){
    var c=new AbortController(),to=setTimeout(function(){c.abort()},4000);
    fetch('/api/display',{cache:'no-store',signal:c.signal,headers:key?{'X-Display-Key':key}:{}})
      .then(function(r){if(!r.ok)throw 0;return r.json()})
      .then(function(d){clearTimeout(to);data=d;last=Date.now();render(d)})
      .catch(function(){clearTimeout(to)});
  }
  poll();setInterval(poll,POLL);clock();setInterval(clock,1000);
})();
