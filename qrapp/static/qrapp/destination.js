document.querySelector('#copy-content')?.addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(document.querySelector('dl').innerText); document.querySelector('#copy-status').textContent = 'Copied.'; }
  catch { document.querySelector('#copy-status').textContent = 'Copy is unavailable. Select the details above to copy manually.'; }
});
