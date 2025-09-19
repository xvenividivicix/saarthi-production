// JS to interact with API
const API = '/v1';
let token = null;
let selected = [];

async function login() {
  const form = new FormData();
  form.append('client_id','demo-client-id');
  form.append('client_secret','demo-client-secret');
  form.append('scope','read:codes write:bundles');
  const res = await fetch(`${API}/auth/token`, { method:'POST', body:form });
  const data = await res.json();
  token = data.access_token;
}

function renderSuggestions(items){
  const out = document.getElementById('out');
  if(!items || items.length===0){ out.innerHTML = '<p>No suggestions.</p>'; return; }
  let html = '<table><thead><tr><th>Select</th><th>Code</th><th>Title</th><th>Score</th></tr></thead><tbody>';
  items.forEach((s,i)=>{
    html += `<tr>
      <td><input type="checkbox" onchange="toggleSel('${s.code}','${s.display.replace(/"/g,'&quot;')}')"></td>
      <td>${s.code}</td><td>${s.display}</td><td>${(s.score||0).toFixed(3)}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  out.innerHTML = html;
}

function toggleSel(code, display){
  const idx = selected.findIndex(x=>x.code===code);
  if(idx>=0) selected.splice(idx,1);
  else selected.push({code, display, system:'http://id.who.int/icd/release/11'});
}

async function autocode(){
  if(!token) await login();
  const text = document.getElementById('freeText').value;
  const res = await fetch(`${API}/coding/autocode`, {
    method:'POST',
    headers: {'Content-Type':'application/json','Authorization':`Bearer ${token}`},
    body: JSON.stringify({ text, topK: 10 })
  });
  const data = await res.json();
  renderSuggestions(data.suggestions);
}

async function exportFHIR(){
  if(!token) await login();
  const req = {
    patient: { id: "pat1", name: "Demo Patient", gender:"male", birthDate:"1985-01-01"},
    conditions: selected.map(s=>({text:s.display, code:s.code, display:s.display})),
    procedures: []
  };
  const res = await fetch(`${API}/fhir/export/bundle`, {
    method:'POST', headers:{'Content-Type':'application/json','Authorization':`Bearer ${token}`},
    body: JSON.stringify(req)
  });
  const bundle = await res.json();
  document.getElementById('fhirOut').textContent = JSON.stringify(bundle, null, 2);
  // also download
  const blob = new Blob([JSON.stringify(bundle,null,2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'saarthi-bundle.json';
  a.click();
}

async function reimport(){
  if(!token) await login();
  const f = document.getElementById('bundleFile').files[0];
  if(!f){ alert('Choose a bundle JSON'); return; }
  const text = await f.text();
  const res = await fetch(`${API}/fhir/import/bundle`, {
    method:'POST', headers:{'Content-Type':'application/json','Authorization':`Bearer ${token}`},
    body: text
  });
  const data = await res.json();
  document.getElementById('importOut').textContent = JSON.stringify(data, null, 2);
}
