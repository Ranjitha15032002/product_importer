// // app/static/app.js
// document.getElementById('upload-form').addEventListener('submit', async (e) => {
//   e.preventDefault();
//   const f = document.getElementById('csvfile').files[0];
//   if (!f) { alert('Select file'); return; }
//   const fd = new FormData(); fd.append('file', f);
//   const res = await fetch('/api/upload', { method: 'POST', body: fd });
//   const json = await res.json();
//   const taskId = json.task_id;
//   const prog = document.getElementById('progress');
//   prog.innerText = 'Started: ' + JSON.stringify(json) + '\n';

//   const es = new EventSource(`/api/events?task_id=${taskId}`);
//   es.onmessage = (ev) => {
//     prog.innerText += ev.data + '\n';
//     if (ev.data.indexOf('complete') !== -1 || ev.data.indexOf('error') !== -1) {
//       es.close();
//       // optionally refresh product list
//       loadProducts();
//     }
//   };
//   es.onerror = (e) => {
//     prog.innerText += 'EventSource error\n';
//     es.close();
//   };
// });

// async function loadProducts() {
//   const res = await fetch('/api/products?limit=50');
//   const j = await res.json();
//   const out = document.getElementById('products');
//   out.innerText = 'Total: ' + j.total + '\n' + JSON.stringify(j.items, null, 2);
// }
// document.getElementById('refresh').addEventListener('click', loadProducts);

// document.getElementById('deleteAll').addEventListener('click', async () => {
//   if (!confirm('Are you sure? This cannot be undone.')) return;
//   const res = await fetch('/api/products/bulk-delete?confirm=true', { method: 'POST' });
//   const j = await res.json();
//   alert(JSON.stringify(j));
//   loadProducts();
// });
