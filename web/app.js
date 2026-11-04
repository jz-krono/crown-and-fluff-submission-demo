const $ = (id) => document.getElementById(id);
let selected = null;
let previousEventCount = -1;
function escapeHTML(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
async function request(path, options={}) {
  const res = await fetch(path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
async function post(path, data={}) { return request(path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); }
function notice(text) { $('notice').textContent = text; }
function when(at) { return new Date(at).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}); }
async function start(kind, consent=false) {
  try {
    notice(kind === 'live' ? 'Starting real Meta calls. Follow the events in the Recorder…' : 'Opening local scenario…');
    const result = await post('/api/runs', {kind, consent});
    selected = result.id; previousEventCount = -1;
    await refresh(true);
  } catch (e) { notice(e.message); }
}
function row(run) {
  return `<button class="run-row ${selected===run.id?'selected':''}" data-id="${escapeHTML(run.id)}"><span class="run-id">${escapeHTML(run.id)}</span><span class="run-meta">${escapeHTML(when(run.received_at))} · ${escapeHTML(run.status)}</span><span class="pill ${run.mode==='SAMPLE REPLAY'?'sample':''}">${escapeHTML(run.mode)}</span></button>`;
}
async function refresh(scroll=false) {
  try {
    const runs = await request('/api/runs');
    if (!selected && runs.length) selected = runs[0].id;
    let lastDay = '', html = '';
    for (const run of runs) {
      const day = new Date(run.received_at).toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric',year:'numeric'});
      if (day !== lastDay) { html += `<div class="group">${escapeHTML(day)}</div>`; lastDay = day; }
      html += row(run);
    }
    $('queue-list').innerHTML = html || '<div class="empty">No local runs yet.</div>';
    for (const button of document.querySelectorAll('.run-row')) button.onclick = () => {selected=button.dataset.id;previousEventCount=-1;refresh(true);};
    if (selected) await show(selected, scroll);
  } catch (e) { notice(e.message); }
}
async function show(id, scroll) {
  const run = await request('/api/runs/' + encodeURIComponent(id));
  if (!run || id !== selected) return;
  if (run.events.length === previousEventCount && !scroll) return;
  previousEventCount = run.events.length;
  const workers = ['Operations','Studio','Finance','Customer Care','Marketing'];
  const outbox = run.events.find(e=>e.kind==='sample.email.outbox.created');
  const order = run.events.find(e=>e.kind==='sample.order.created');
  const count = order?.detail.cardCount || 1;
  const hasCase = run.events.some(e=>e.kind==='sample.case.needs_operator');
  const affectedCard = run.events.find(e=>e.kind==='sample.case.needs_operator')?.detail.cardId || 'CARD-1';
  const refunded = run.events.some(e=>e.kind==='sample.refund.recorded');
  let html = `<div class="detail-top"><span class="pill ${run.mode.startsWith('SAMPLE')?'sample':''}">${escapeHTML(run.mode)}</span><span class="pill">${escapeHTML(run.status)}</span><h3>${escapeHTML(run.id)}</h3><p>Received ${escapeHTML(when(run.received_at))} · ${count} sample ${count===1?'card':'cards'} · $${(run.amount_cents/100).toFixed(2)} simulated ${run.paid?'payment':'quote'} · sharing ${run.consent?'on':'off'}</p></div>`;
  html += '<div class="worker-strip">'+workers.map(w=>`<span>${escapeHTML(w)} ${run.events.some(e=>e.actor===w)?'✓':'·'}</span>`).join('')+'<span>Independent verifier '+(run.events.some(e=>e.actor==='Independent verifier')?'✓':'·')+'</span></div>';
  html += `<div class="detail-actions"><button id="duplicate" ${run.paid?'':'disabled'}>Replay paid event</button><button id="case" ${['delivered locally','sample replay','sample refunded'].includes(run.status)?'':'disabled'}>Create sample problem report</button><button id="refund" ${hasCase&&!refunded?'':'disabled'}>Confirm local operator refund</button></div>`;
  if (run.error) html += `<p role="alert">Run stopped: ${escapeHTML(run.error)}</p>`;
  html += `<div class="images"><figure><img src="/api/source" alt="Submitted Sphynx cat"><figcaption>Original example photo · SHA ${escapeHTML(run.photo_sha.slice(0,12))}…</figcaption></figure><figure>${run.image_file?`<img src="/api/runs/${encodeURIComponent(id)}/image" alt="Muse Image output">`:'<div class="empty">The image appears after a live Muse Image call.</div>'}<figcaption>${run.image_file?'Generated WebP · inspectable bytes':'No image in sample replay or pending-payment case'}</figcaption></figure></div>`;
  if (outbox) html += `<div class="mail-preview"><p class="eyebrow">Local email outbox · never sent</p><h4>${escapeHTML(outbox.detail.subject)}</h4><p>To: Sample customer · The generated WebP is attached to an inspectable MIME email.</p><a href="/api/runs/${encodeURIComponent(id)}/email.eml" download="sample-card.eml">Download sample email (.eml) ↗</a></div>`;
  html += '<div class="timeline"><h4>Touchpoints · '+run.events.length+'</h4>';
  for (const e of run.events) {
    const type=e.kind.includes('verifier')?'verifier':(e.kind.includes('email')||e.kind.includes('payment.verified')||e.kind.includes('post.')||e.kind.includes('refund.'))?'effect':'';
    html += `<article class="event ${type}"><span class="meta">${escapeHTML(when(e.at))} · #${e.id}</span><strong>${escapeHTML(e.kind)}</strong><span class="actor">${escapeHTML(e.actor)}</span><details><summary>Inspect receipt</summary><pre>${escapeHTML(JSON.stringify(e.detail,null,2))}</pre></details></article>`;
  }
  html += '</div>';
  $('detail').innerHTML = html;
  $('duplicate').onclick=()=>act(id,'duplicate-payment');
  $('case').onclick=()=>act(id,'case');
  $('refund').onclick=()=>{ if (window.confirm(`Record one LOCAL simulated refund for ${affectedCard}? This does not call Stripe.`)) act(id,'refund',{confirmed:true}); };
  if (scroll && matchMedia('(max-width:780px)').matches) $('detail').scrollIntoView({behavior:'smooth',block:'start'});
}
async function act(id, action, data={}) { try {const result=await post(`/api/runs/${encodeURIComponent(id)}/${action}`,data);notice(result.newEffect===false?'Duplicate request reused the original effect.':'Local action recorded.');previousEventCount=-1;await refresh();}catch(e){notice(e.message);} }
async function init() {
  $('run-live').onclick=()=>start('live',false);$('run-consent').onclick=()=>start('live',true);$('run-sample').onclick=()=>start('sample');$('run-pending').onclick=()=>start('pending');$('run-pack3').onclick=()=>start('pack3');$('run-pack5').onclick=()=>start('pack5');$('refresh').onclick=()=>refresh();
  try {const config=await request('/api/config');$('key-state').textContent=config.keyConfigured?'Muse key configured locally':'Add a key for live Meta calls';
    const evidence=await request('/api/evidence');$('evidence-stats').innerHTML=Object.entries(evidence.metrics).map(([label,value])=>`<div><strong>${escapeHTML(value)}</strong><span>${escapeHTML(label)}</span></div>`).join('');
    await refresh();setInterval(()=>refresh(),1800);
  } catch(e) {notice(e.message);}
}
init();
