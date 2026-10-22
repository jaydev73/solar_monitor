(function(){
  var $=function(i){return document.getElementById(i)}, msg=$('msg');
  function chip(id,text,cls){var e=$(id);e.textContent=text;e.className='chip'+(cls?' '+cls:'')}
  function status(){fetch('/api/phone/status',{cache:'no-store'}).then(function(r){return r.json()}).then(function(s){
    if(!s.configured){chip('c-online','Not configured','bad');return}
    if(!s.online){chip('c-online','Phone offline','bad');chip('c-screen','Screen: –');chip('c-batt','Battery: –');return}
    chip('c-online','Phone online','ok');
    chip('c-screen','Screen: '+(s.screen_on===true?'on':s.screen_on===false?'off':'unknown'));
    chip('c-batt','Battery: '+(s.battery!=null?s.battery+'%':'unknown')+(s.plugged?' · charging':''))
  }).catch(function(){chip('c-online','Server unreachable','bad')})}
  function send(act,body,btn){btn.disabled=true;msg.textContent='Sending…';
    fetch('/api/phone/'+act,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})})
      .then(function(r){return r.json()}).then(function(j){msg.textContent=j.ok?'Done.':(j.message||'The phone did not respond.');setTimeout(status,800)})
      .catch(function(){msg.textContent='Request failed.'}).then(function(){btn.disabled=false})}
  document.querySelectorAll('button[data-act]').forEach(function(b){b.onclick=function(){send(b.dataset.act,{},b)}});
  $('say-btn').onclick=function(){var t=$('say-text').value.trim();if(t)send('say',{text:t},$('say-btn'))};
  status();setInterval(status,5000);
})();
