function renderStockChart(allRows) {
  const svg = document.getElementById('stock-plot'), ns = 'http://www.w3.org/2000/svg';
  let mode = 'line', period = '60', selected = -1, rows = [], points = [];
  const W=1000,H=460,L=12,R=88,T=25,P=300,V=385,B=420;
  const red='#f04452',blue='#3182f6',fmt=n=>Math.round(n).toLocaleString('ko-KR');
  const finite=v=>v!==null&&v!==''&&Number.isFinite(Number(v));
  function el(tag,attrs={},text='',parent=svg){const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));e.textContent=text;parent.append(e);return e;}
  function ohlc(r){return ['open','high','low','close'].every(k=>finite(r[k]))&&r.low>0&&r.low<=Math.min(r.open,r.close)&&r.high>=Math.max(r.open,r.close);}
  function readout(i){const r=rows[i];document.getElementById('chart-readout').textContent=`${r.date}  ·  ${ohlc(r)?`시 ${fmt(r.open)}  고 ${fmt(r.high)}  저 ${fmt(r.low)}  `:''}종 ${fmt(r.close)}원  ·  거래량 ${fmt(r.volume)}주`;}
  function draw(){
    rows=allRows.filter(r=>finite(r.close)&&r.close>0);if(period!=='all')rows=rows.slice(-Number(period));svg.replaceChildren();svg.setAttribute('viewBox',`0 0 ${W} ${H}`);if(!rows.length)return;
    const last=rows[rows.length-1],first=rows[0],diff=last.close-first.close,pct=diff/first.close*100,color=diff>=0?red:blue;
    document.getElementById('quote-price').textContent=fmt(last.close)+'원';
    const change=document.getElementById('quote-change');change.textContent=`선택 기간 첫 종가 대비 ${diff>=0?'+':''}${fmt(diff)}원 (${pct>=0?'+':''}${pct.toFixed(2)}%)`;change.style.color=color;
    document.getElementById('chart-caption').textContent=`${first.date} ~ ${last.date} · ${rows.length}개 거래 관측치 · 마지막 종가 기준`;
    const values=rows.flatMap(r=>mode==='candle'&&ohlc(r)?[Number(r.low),Number(r.high)]:[Number(r.close)]),lo=Math.min(...values),hi=Math.max(...values),pad=Math.max((hi-lo)*.12,hi*.005),min=lo-pad,max=hi+pad;
    const step=(W-L-R)/rows.length,x=i=>L+step*(i+.5),y=v=>T+(max-v)/(max-min)*(P-T),volMax=Math.max(1,...rows.map(r=>Number(r.volume)||0));
    for(let i=0;i<5;i++){const yy=T+(P-T)*i/4;el('line',{x1:L,x2:W-R,y1:yy,y2:yy,stroke:'#f0f2f5'});el('text',{x:W-R+12,y:yy+4},fmt(max-(max-min)*i/4));}
    if(mode==='line'){
      const coords=rows.map((r,i)=>`${x(i)},${y(r.close)}`);el('polygon',{points:`${x(0)},${P} ${coords.join(' ')} ${x(rows.length-1)},${P}`,fill:color,opacity:'.055'});el('polyline',{points:coords.join(' '),fill:'none',stroke:color,'stroke-width':2.5,'stroke-linejoin':'round','stroke-linecap':'round'});
    } else rows.forEach((r,i)=>{if(!ohlc(r))return;const c=r.close>=r.open?red:blue;el('line',{x1:x(i),x2:x(i),y1:y(r.high),y2:y(r.low),stroke:c,'stroke-width':1.2});el('rect',{x:x(i)-step*.3,y:Math.min(y(r.open),y(r.close)),width:Math.max(1,step*.6),height:Math.max(1,Math.abs(y(r.open)-y(r.close))),fill:c});});
    if(mode==='candle'&&rows.some(r=>!ohlc(r)))document.getElementById('chart-caption').textContent+=' · OHLC가 없는 날짜의 캔들은 생략';
    el('text',{x:L,y:P+28},'거래량');el('text',{x:W-R+12,y:V-10},fmt(volMax));
    rows.forEach((r,i)=>{const previous=i?rows[i-1].close:r.close,c=r.close>=(finite(r.open)?r.open:previous)?red:blue,height=(Number(r.volume)||0)/volMax*62;el('rect',{x:x(i)-step*.3,y:B-height,width:Math.max(1,step*.6),height,fill:c,opacity:'.45'});});
    [...new Set([0,Math.floor((rows.length-1)/3),Math.floor((rows.length-1)*2/3),rows.length-1])].forEach(i=>el('text',{x:x(i),y:H-12,'text-anchor':i===0?'start':i===rows.length-1?'end':'middle'},rows[i].date.slice(5)));
    points=rows.map((r,i)=>[x(i),y(r.close)]);selected=rows.length-1;readout(selected);
  }
  function inspect(i){selected=Math.max(0,Math.min(rows.length-1,i));svg.querySelectorAll('.crosshair').forEach(e=>e.remove());const group=el('g',{class:'crosshair','pointer-events':'none'});el('line',{x1:points[selected][0],x2:points[selected][0],y1:T,y2:B,stroke:'#9aa5b1','stroke-dasharray':'4 4'},'',group);el('circle',{cx:points[selected][0],cy:points[selected][1],r:4,fill:'#191f28',stroke:'white','stroke-width':2},'',group);readout(selected);}
  svg.addEventListener('pointermove',e=>{if(!rows.length)return;const rect=svg.getBoundingClientRect(),xx=(e.clientX-rect.left)/rect.width*W;inspect(Math.floor((xx-L)/(W-L-R)*rows.length));});
  svg.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)&&rows.length){e.preventDefault();inspect(selected+(e.key==='ArrowLeft'?-1:1));}});
  document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.mode;document.querySelectorAll('[data-mode]').forEach(t=>t.setAttribute('aria-pressed',String(t===b)));draw();}));
  document.querySelectorAll('[data-days]').forEach(b=>b.addEventListener('click',()=>{period=b.dataset.days;document.querySelectorAll('[data-days]').forEach(t=>t.setAttribute('aria-pressed',String(t===b)));draw();}));draw();
}
