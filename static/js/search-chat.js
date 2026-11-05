// Command Palette — Ctrl+K enhanced search + quick actions
//
// Acts as a fuzzy launcher for:
//   1. Quick commands (prefixed with > or typed directly) — open panels,
//      toggle features, switch themes, run actions
//   2. Chat/message search — existing search across conversations
//   3. Cross-entity search — documents, notes, tasks (future)

import uiModule from './ui.js';
import sessionModule from './sessions.js';
import * as Modals from './modalManager.js';

let API_BASE = '';
let debounceTimer = null;
let selectedIndex = -1;
let results = [];
let currentMode = 'search'; // 'search' | 'commands'

function el(id) { return document.getElementById(id); }

// ── Built-in commands ─────────────────────────────────────────────────
const COMMANDS = [
  { id: 'new-chat',        label: 'New Chat',           icon: '💬',    shortcut: 'Ctrl+Alt+N',
    action: () => { window.sessionModule?.newSession?.(); return true; }},
  { id: 'toggle-sidebar',  label: 'Toggle Sidebar',     icon: '📑',    shortcut: 'Ctrl+Alt+B',
    action: () => { document.querySelector('#sidebar-toggle')?.click?.(); return true; }},
  { id: 'open-sessions',   label: 'Open Chats Library', icon: '📋',    shortcut: '',
    action: () => { _openPanel('doc-panel'); return true; }},
  { id: 'open-memory',     label: 'Open Memory',        icon: '🧠',    shortcut: '',
    action: () => { _openPanel('memory-modal'); return true; }},
  { id: 'open-documents',  label: 'Open Documents',     icon: '📄',    shortcut: '',
    action: () => { _openPanel('documents-modal'); return true; }},
  { id: 'open-email',      label: 'Open Email',         icon: '✉️',    shortcut: '',
    action: () => { _openPanel('email-lib-modal'); return true; }},
  { id: 'open-calendar',   label: 'Open Calendar',      icon: '📅',    shortcut: 'Ctrl+Alt+C',
    action: () => { _openPanel('calendar-modal'); return true; }},
  { id: 'open-notes',      label: 'Open Notes',         icon: '📝',    shortcut: '',
    action: () => { _openPanel('notes-modal'); return true; }},
  { id: 'open-tasks',      label: 'Open Tasks',         icon: '✅',    shortcut: '',
    action: () => { _openPanel('tasks-modal'); return true; }},
  { id: 'open-gallery',    label: 'Open Gallery',       icon: '🖼️',    shortcut: '',
    action: () => { _openPanel('gallery-modal'); return true; }},
  { id: 'open-cookbook',   label: 'Open Cookbook',      icon: '🔧',    shortcut: '',
    action: () => { _openPanel('cookbook-modal'); return true; }},
  { id: 'open-settings',   label: 'Open Settings',      icon: '⚙️',    shortcut: 'Ctrl+,',
    action: () => { _openPanel('settings-modal'); return true; }},
  { id: 'open-research',   label: 'Open Deep Research', icon: '🔬',    shortcut: '',
    action: () => { _openPanel('research-overlay'); return true; }},
  { id: 'theme-dark',      label: 'Theme: Dark',        icon: '🌙',    shortcut: '',
    action: () => { window.themeModule?.applyTheme?.('dark'); return true; }},
  { id: 'theme-light',     label: 'Theme: Light',       icon: '☀️',    shortcut: '',
    action: () => { window.themeModule?.applyTheme?.('light'); return true; }},
  { id: 'theme-cyberpunk', label: 'Theme: Cyberpunk',   icon: '🌃',    shortcut: '',
    action: () => { window.themeModule?.applyTheme?.('cyberpunk'); return true; }},
  { id: 'theme-midnight',  label: 'Theme: Midnight',    icon: '🌌',    shortcut: '',
    action: () => { window.themeModule?.applyTheme?.('midnight'); return true; }},
  { id: 'theme-terminal',  label: 'Theme: Terminal',    icon: '💻',    shortcut: '',
    action: () => { window.themeModule?.applyTheme?.('terminal'); return true; }},
  { id: 'toggle-agent',    label: 'Toggle Agent Mode',  icon: '🤖',    shortcut: '',
    action: () => { _toggleAgent(); return true; }},
  { id: 'toggle-incognito',label: 'Toggle Incognito',   icon: '👁️',    shortcut: 'Ctrl+Alt+I',
    action: () => { _toggleIncognito(); return true; }},
];

// Map command IDs to feature flags — commands for disabled features are hidden.
const _CMD_FEATURE_MAP = {
  'open-email':     'email',
  'open-gallery':   'gallery',
  'open-cookbook':  'cookbook',
  'open-research':  'research',
  'open-compare':   'compare',
};

function _getEnabledCommands() {
  const flags = window._vhtnaFeatureFlags || {};
  return COMMANDS.filter(cmd => {
    const feat = _CMD_FEATURE_MAP[cmd.id];
    return !feat || flags[feat] !== false;
  });
}

function _openPanel(modalId) {
  closeSearch();
  if (Modals.isRegistered(modalId)) {
    Modals.toggle(modalId);
    // If toggling from closed → open, toggle returns true.
    // If already open, force-restore it.
    if (Modals.isMinimized(modalId)) {
      Modals.toggle(modalId);
    } else {
      const modal = document.getElementById(modalId);
      if (modal && modal.classList.contains('hidden')) {
        Modals.toggle(modalId);
      }
    }
  } else {
    // Not registered yet — click its rail button
    const btn = document.querySelector(`[data-modal="${modalId}"], #tool-${modalId.replace('-modal', '')}-btn`);
    if (btn) { btn.click(); }
  }
}

function _toggleAgent() {
  closeSearch();
  const btn = document.querySelector('[data-action="toggle-agent"], #agent-toggle-btn');
  if (btn) { btn.click(); return; }
  // Fallback: POST the toggle via API
  fetch('/api/settings/agent-mode', { method: 'POST', credentials: 'same-origin' }).catch(() => {});
}

function _toggleIncognito() {
  closeSearch();
  const btn = document.querySelector('[data-action="toggle-incognito"]');
  if (btn) { btn.click(); }
}

// ── Public API ─────────────────────────────────────────────────────────

export function openSearch() {
  const overlay = el('search-overlay');
  if (!overlay) return;
  overlay.classList.remove('hidden');
  const input = el('search-input');
  if (input) {
    input.value = '';
    input.placeholder = 'Search chats, documents, notes… or type > for commands';
    input.focus();
  }
  selectedIndex = -1;
  results = [];
  currentMode = 'search';
  _renderCommands('');
}

export function closeSearch() {
  const overlay = el('search-overlay');
  if (!overlay) return;
  overlay.classList.add('hidden');
  el('search-results').innerHTML = '';
  selectedIndex = -1;
  results = [];
  currentMode = 'search';
}

export function isOpen() {
  const overlay = el('search-overlay');
  return overlay && !overlay.classList.contains('hidden');
}

// ── Internal ───────────────────────────────────────────────────────────

var escapeHtml = uiModule.esc;

function highlightMatch(text, query) {
  if (!query) return escapeHtml(text);
  const escaped = escapeHtml(text);
  try {
    const regex = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
    return escaped.replace(regex, '<mark class="search-highlight">$1</mark>');
  } catch (_) {
    return escaped;
  }
}

function formatTimestamp(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 86400000) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  if (diff < 604800000) {
    return d.toLocaleDateString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Fuzzy match helper ─────────────────────────────────────────────────
function fuzzyMatch(text, query) {
  if (!query) return true;
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  // Simple subsequence match: "nt" matches "New Chat"
  let qi = 0;
  for (let ti = 0; ti < lowerText.length && qi < lowerQuery.length; ti++) {
    if (lowerText[ti] === lowerQuery[qi]) qi++;
  }
  return qi >= lowerQuery.length;
}

// ── Command mode ───────────────────────────────────────────────────────
function _renderCommands(query) {
  const container = el('search-results');
  if (!container) return;

  // Filter commands by feature flags AND fuzzy match
  const enabled = _getEnabledCommands();
  const filtered = enabled.filter(cmd => fuzzyMatch(cmd.label + ' ' + cmd.id, query));

  if (filtered.length === 0) {
    container.innerHTML = '<div class="search-empty">No matching commands</div>';
    results = [];
    selectedIndex = -1;
    return;
  }

  let html = '<div class="search-group-header">Commands</div>';
  filtered.forEach((cmd, i) => {
    const shortcutHtml = cmd.shortcut
      ? `<span class="cmd-shortcut">${escapeHtml(cmd.shortcut)}</span>`
      : '';
    html += `<div class="search-result-item cmd-item" data-cmd="${escapeHtml(cmd.id)}" data-index="${i}">
      <span class="cmd-icon">${cmd.icon}</span>
      <span class="cmd-label">${escapeHtml(cmd.label)}</span>
      ${shortcutHtml}
    </div>`;
  });

  container.innerHTML = html;
  results = filtered;
  selectedIndex = -1;
  selectedIndex = -1;

  // Click handlers
  container.querySelectorAll('.search-result-item.cmd-item').forEach(item => {
    item.addEventListener('click', () => {
      const cmdId = item.dataset.cmd;
      const cmd = COMMANDS.find(c => c.id === cmdId);
      if (cmd) { closeSearch(); cmd.action(); }
    });
  });
}

// ── Search mode (chat messages) ────────────────────────────────────────
function _renderChatResults(data, query) {
  results = data || [];
  selectedIndex = -1;
  const container = el('search-results');
  if (!container) return;

  if (!data || data.length === 0) {
    container.innerHTML = '<div class="search-empty">No results found</div>';
    return;
  }

  // Group by session
  const grouped = {};
  for (const r of data) {
    if (!grouped[r.session_id]) {
      grouped[r.session_id] = { name: r.session_name, items: [] };
    }
    grouped[r.session_id].items.push(r);
  }

  let html = '<div class="search-group-header">Chat Messages</div>';
  let idx = 0;
  for (const [sessionId, group] of Object.entries(grouped)) {
    for (const item of group.items) {
      const roleLabel = item.role === 'user' ? 'You' : 'AI';
      html += `<div class="search-result-item" data-index="${idx}" data-session="${escapeHtml(sessionId)}">
        <div class="search-result-role">${roleLabel}</div>
        <div class="search-result-snippet">${highlightMatch(item.content_snippet, query)}</div>
        <div class="search-result-time">${formatTimestamp(item.timestamp)}</div>
      </div>`;
      idx++;
    }
  }
  container.innerHTML = html;

  container.querySelectorAll('.search-result-item[data-session]').forEach(item => {
    item.addEventListener('click', () => {
      const sid = item.dataset.session;
      navigateToSession(sid);
    });
  });
}

function navigateToSession(sessionId) {
  closeSearch();
  if (sessionModule && sessionModule.selectSession) {
    sessionModule.selectSession(sessionId);
  }
}

function updateSelection() {
  const container = el('search-results');
  if (!container) return;
  const items = container.querySelectorAll('.search-result-item');
  items.forEach((item, i) => {
    item.classList.toggle('selected', i === selectedIndex);
  });
  if (selectedIndex >= 0 && items[selectedIndex]) {
    items[selectedIndex].scrollIntoView({ block: 'nearest' });
  }
}

function _executeSelected() {
  const container = el('search-results');
  if (!container) return;
  const items = container.querySelectorAll('.search-result-item');
  if (selectedIndex < 0 || selectedIndex >= items.length) return;

  const item = items[selectedIndex];
  // Command items
  const cmdId = item.dataset.cmd;
  if (cmdId) {
    const cmd = COMMANDS.find(c => c.id === cmdId);
    if (cmd) { closeSearch(); cmd.action(); }
    return;
  }
  // Session items
  const sid = item.dataset.session;
  if (sid) { navigateToSession(sid); }
}

function handleKeydown(e) {
  if (!isOpen()) return;

  const container = el('search-results');
  const items = container ? container.querySelectorAll('.search-result-item') : [];
  const count = items.length;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    selectedIndex = count > 0 ? Math.min(selectedIndex + 1, count - 1) : -1;
    updateSelection();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    selectedIndex = Math.max(selectedIndex - 1, 0);
    updateSelection();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    _executeSelected();
  } else if (e.key === 'Escape') {
    e.preventDefault();
    closeSearch();
  } else if (e.key === 'Tab' && !e.shiftKey) {
    // Tab to switch between command mode and search mode
    e.preventDefault();
    const input = el('search-input');
    if (input) {
      const val = input.value;
      if (currentMode === 'commands' || val.startsWith('>')) {
        currentMode = 'search';
        input.placeholder = 'Search chats, documents, notes…';
        input.value = val.replace(/^>\s*/, '');
        _triggerSearch(input.value.trim());
      } else {
        currentMode = 'commands';
        input.placeholder = 'Type a command name…';
        input.value = '>';
        _renderCommands('');
        input.setSelectionRange(1, 1);
      }
    }
  }
}

function _triggerSearch(query) {
  if (debounceTimer) clearTimeout(debounceTimer);
  if (!query) {
    _renderCommands('');
    return;
  }
  debounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&limit=20`);
      if (!res.ok) { _renderEmpty(); return; }
      const data = await res.json();
      _renderChatResults(data, query);
    } catch (err) {
      console.error('Search error:', err);
    }
  }, 300);
}

function _renderEmpty() {
  const container = el('search-results');
  if (container) container.innerHTML = '';
}

function handleInput(e) {
  const raw = e.target.value;
  let query = raw.trim();

  // If typed ">" switch to command mode
  if (raw === '>') {
    currentMode = 'commands';
    e.target.placeholder = 'Type a command name…';
    _renderCommands('');
    return;
  }
  // If backspace removed ">" switch back
  if (currentMode === 'commands' && !raw.startsWith('>')) {
    currentMode = 'search';
    e.target.placeholder = 'Search chats, documents, notes…';
  }

  // Strip leading ">" for commands mode
  if (currentMode === 'commands') {
    const cmdQuery = raw.replace(/^>\s*/, '');
    _renderCommands(cmdQuery);
    return;
  }

  // Search mode
  if (!query) {
    _renderCommands('');
    return;
  }
  _triggerSearch(query);
}

export function init(apiBase) {
  API_BASE = apiBase || '';

  const input = el('search-input');
  if (input) {
    input.addEventListener('input', handleInput);
    input.addEventListener('keydown', handleKeydown);
  }

  // Close on overlay click (not popup click)
  const overlay = el('search-overlay');
  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeSearch();
    });
  }
}

const commandPaletteModule = {
  init,
  openSearch,
  closeSearch,
  isOpen,
};

export default commandPaletteModule;
