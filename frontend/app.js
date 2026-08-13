const response = document.querySelector('[data-response]');
const status = document.querySelector('[data-status]');
document.querySelector('[data-send]').addEventListener('click', () => { status.textContent = '200 OK · 184 ms'; response.innerHTML = '<pre class="json-response">{\n  "data": [\n    { "id": 1, "name": "Ada Lovelace" },\n    { "id": 2, "name": "Grace Hopper" }\n  ],\n  "total": 2\n}</pre>'; });
document.querySelectorAll('[data-new-request]').forEach((button) => button.addEventListener('click', () => { document.querySelector('#url').value = ''; document.querySelector('#url').focus(); status.textContent = 'Ready to send'; response.innerHTML = '<div class="empty-response"><span class="response-symbol">→</span><strong>New request</strong><span>Enter a URL or choose a request template.</span></div>'; }));
document.querySelector('[data-command]').addEventListener('click', () => document.querySelector('#url').focus());
