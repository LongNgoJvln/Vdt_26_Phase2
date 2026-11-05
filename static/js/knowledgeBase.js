async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

export function initKnowledgeBase() {
  const summary = document.getElementById('nc-kb-summary');
  const message = document.getElementById('nc-kb-message');
  if (!summary || summary.dataset.ready) return;
  summary.dataset.ready = '1';

  const show = (text, error = false) => {
    message.textContent = text;
    message.style.color = error ? '#e55' : 'var(--accent, var(--red))';
  };
  const refresh = async () => {
    try {
      const data = await readJson(await fetch('/api/knowledge/sources'));
      summary.textContent = `Nguồn đóng gói: ${data.counts.knowledge || 0} knowledge · ${data.counts.instructions || 0} instructions`;
    } catch (error) {
      summary.textContent = `Không đọc được nguồn: ${error.message}`;
    }
  };
  const ingest = async category => {
    show(`Đang ingest ${category}…`);
    try {
      const data = await readJson(await fetch('/api/knowledge/ingest', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, replace: true }),
      }));
      show(`Hoàn tất: ${data.files_ok} file, ${data.chunks_upserted} chunks; lỗi: ${data.files_failed}`);
    } catch (error) { show(error.message, true); }
  };
  document.getElementById('nc-kb-ingest-all')?.addEventListener('click', () => ingest('all'));
  document.getElementById('nc-kb-ingest-knowledge')?.addEventListener('click', () => ingest('knowledge'));
  document.getElementById('nc-kb-ingest-instructions')?.addEventListener('click', () => ingest('instructions'));
  document.getElementById('nc-kb-upload')?.addEventListener('click', async () => {
    const input = document.getElementById('nc-kb-file');
    if (!input?.files?.length) return show('Hãy chọn một file .md, .txt hoặc .json.', true);
    const form = new FormData();
    form.append('role', document.getElementById('nc-kb-role').value);
    form.append('replace', 'true');
    form.append('file', input.files[0]);
    show('Đang lưu và ingest…');
    try {
      const data = await readJson(await fetch('/api/knowledge/upload', { method: 'POST', body: form }));
      show(`Đã lưu ${input.files[0].name}; ${data.chunks_upserted} chunks.`);
      input.value = '';
    } catch (error) { show(error.message, true); }
  });
  refresh();
}

export default { init: initKnowledgeBase };
