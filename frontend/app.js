const API = 'http://localhost:8000';

async function calculatePremium() {
  const payload = {
    age: Number(document.getElementById('age').value),
    term: Number(document.getElementById('term').value),
    sum_assured: Number(document.getElementById('sumAssured').value),
    interest_rate: Number(document.getElementById('interest').value),
    product_type: document.getElementById('productType').value,
  };
  const res = await fetch(`${API}/premium/calculate`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  document.getElementById('premiumResult').textContent = JSON.stringify(data, null, 2);
}

async function uploadOcr() {
  const file = document.getElementById('ocrFile').files[0];
  if (!file) {
    alert('파일을 선택하세요.');
    return;
  }
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API}/ocr/upload`, { method: 'POST', body: form });
  const data = await res.json();
  document.getElementById('ocrResult').textContent = JSON.stringify(data, null, 2);
}

async function loadFormulas() {
  const res = await fetch(`${API}/formulas`);
  const data = await res.json();
  const target = document.getElementById('formulaList');
  target.innerHTML = '';
  data.forEach(f => {
    const div = document.createElement('div');
    div.className = 'formula';
    div.innerHTML = `<b>${f.formula_code || ''}</b> - ${f.formula_name || ''}<br/>\\[${f.latex || ''}\\]<small>function: ${f.python_function || ''}, status: ${f.status}</small>`;
    target.appendChild(div);
  });
  if (window.MathJax) MathJax.typesetPromise();
}

async function runBatch() {
  const res = await fetch(`${API}/batch/run-sample`, { method: 'POST' });
  const data = await res.json();
  document.getElementById('batchResult').textContent = JSON.stringify(data, null, 2);
}

loadFormulas().catch(console.error);
