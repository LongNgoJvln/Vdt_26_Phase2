// Per-session unified tool selector: disabled -> auto -> pinned.

let _tools = [];
let _panel = null;
let _button = null;
let _chips = null;

function sessionId() {
  return window.sessionModule?.getCurrentSessionId?.() || null;
}

function modeLabel(mode) {
  return mode === 'disabled' ? 'Off' : mode === 'pinned' ? 'Pinned' : 'Auto';
}

function nextMode(mode) {
  return mode === 'disabled' ? 'auto' : mode === 'auto' ? 'pinned' : 'disabled';
}

async function loadTools() {
  const sid = sessionId();
  const query = sid ? `?session_id=${encodeURIComponent(sid)}` : '';
  const response = await fetch(`/api/tool-registry${query}`);
  if (!response.ok) throw new Error(`Tool registry: HTTP ${response.status}`);
  const data = await response.json();
  _tools = data.tools || [];
  render();
}

async function saveMode(tool, mode) {
  const response = await fetch('/api/tool-registry/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId(), tools: { [tool.id]: mode } }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  tool.mode = mode;
  render();
}

function renderChips() {
  if (!_chips) return;
  _chips.replaceChildren();
  for (const tool of _tools.filter(item => item.mode === 'pinned')) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'tool-palette-chip';
    chip.textContent = tool.name;
    chip.title = `${tool.provider} — đang Pinned; bấm để mở danh sách tools`;
    chip.addEventListener('click', () => openPanel());
    _chips.appendChild(chip);
  }
}

function render() {
  if (!_panel || !_button) return;
  const pinned = _tools.filter(item => item.mode === 'pinned').length;
  const disabled = _tools.filter(item => item.mode === 'disabled').length;
  _button.querySelector('[data-tool-count]').textContent = `${_tools.length - disabled}/${_tools.length}`;
  _button.classList.toggle('has-pinned', pinned > 0);

  const list = _panel.querySelector('.tool-palette-list');
  const query = (_panel.querySelector('input')?.value || '').trim().toLowerCase();
  list.replaceChildren();
  const shown = _tools.filter(tool => !query || `${tool.name} ${tool.description} ${tool.provider}`.toLowerCase().includes(query));
  for (const tool of shown) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = `tool-palette-row mode-${tool.mode}`;
    row.disabled = !!tool.locked;
    const text = document.createElement('span');
    text.className = 'tool-palette-copy';
    const title = document.createElement('strong');
    title.textContent = tool.name;
    const provider = document.createElement('small');
    provider.textContent = `${tool.source === 'mcp' ? 'MCP' : 'Built-in'} · ${tool.provider}`;
    const desc = document.createElement('span');
    desc.textContent = tool.description || 'Không có mô tả';
    text.append(title, provider, desc);
    const state = document.createElement('span');
    state.className = 'tool-palette-state';
    state.textContent = tool.locked ? 'Bị Off ở server' : modeLabel(tool.mode);
    row.append(text, state);
    if (!tool.locked) {
      row.addEventListener('click', async () => {
        row.disabled = true;
        try { await saveMode(tool, nextMode(tool.mode)); }
        catch (error) { window.uiModule?.showError?.(error.message); }
        finally { row.disabled = false; }
      });
    }
    list.appendChild(row);
  }
  if (!shown.length) {
    const empty = document.createElement('div');
    empty.className = 'tool-palette-empty';
    empty.textContent = 'Không tìm thấy tool phù hợp.';
    list.appendChild(empty);
  }
  renderChips();
}

async function openPanel() {
  _panel.classList.remove('hidden');
  try { await loadTools(); }
  catch (error) { window.uiModule?.showError?.(`Không tải được tools: ${error.message}`); }
}

export function initToolPalette() {
  const host = document.getElementById('pinned-tools-bar');
  if (!host || host.dataset.toolPaletteReady) return;
  host.dataset.toolPaletteReady = '1';

  _button = document.createElement('button');
  _button.type = 'button';
  _button.className = 'tool-palette-button';
  _button.innerHTML = '<span>Tools</span><small data-tool-count>…</small>';
  _button.title = 'Chọn tool: Off / Auto / Pinned cho session này';
  _chips = document.createElement('div');
  _chips.className = 'tool-palette-chips';
  host.append(_button, _chips);

  _panel = document.createElement('div');
  _panel.className = 'tool-palette-panel hidden';
  _panel.innerHTML = `
    <div class="tool-palette-head"><strong>Tool list for this session</strong><button type="button" aria-label="Đóng">×</button></div>
    <p>Off: must not be called· Auto: Chosen by similarity · Pinned: Always being sent with prompt.</p>
    <input type="search" placeholder="Tìm built-in hoặc MCP tool…" aria-label="Tìm tool">
    <div class="tool-palette-list"></div>`;
  document.body.appendChild(_panel);

  _button.addEventListener('click', () => _panel.classList.contains('hidden') ? openPanel() : _panel.classList.add('hidden'));
  _panel.querySelector('.tool-palette-head button').addEventListener('click', () => _panel.classList.add('hidden'));
  _panel.querySelector('input').addEventListener('input', render);
  document.addEventListener('click', event => {
    if (!_panel.classList.contains('hidden') && !_panel.contains(event.target) && !_button.contains(event.target)) {
      _panel.classList.add('hidden');
    }
  });
  window.addEventListener('network-change:session-selected', () => loadTools().catch(() => {}));
  loadTools().catch(() => {});
}

export default { init: initToolPalette, refresh: loadTools };
