// Terminal-style prompt recall scoped to the current chat session.

const cache = new Map();
let position = null;
let draft = '';
let applying = false;

function currentSession() {
  return window.sessionModule?.getCurrentSessionId?.() || null;
}

async function promptsFor(sessionId) {
  if (!sessionId) return [];
  if (cache.has(sessionId)) return cache.get(sessionId);
  const response = await fetch(`/api/history/${encodeURIComponent(sessionId)}`);
  if (!response.ok) return [];
  const data = await response.json();
  const prompts = (data.history || [])
    .filter(item => item.role === 'user' && typeof item.content === 'string')
    .map(item => item.content.trim())
    .filter(text => text && text !== 'Continue where you left off' && !text.startsWith('[Instruction:'));
  cache.set(sessionId, prompts);
  return prompts;
}

function onFirstLine(textarea) {
  return textarea.selectionStart <= textarea.value.indexOf('\n') || !textarea.value.includes('\n');
}

function onLastLine(textarea) {
  const lastBreak = textarea.value.lastIndexOf('\n');
  return textarea.selectionEnd > lastBreak;
}

export function initPromptHistory() {
  const textarea = document.getElementById('message');
  if (!textarea || textarea.dataset.promptHistoryReady) return;
  textarea.dataset.promptHistoryReady = '1';

  textarea.addEventListener('input', () => {
    if (!applying) position = null;
  });

  textarea.addEventListener('keydown', async event => {
    if (!['ArrowUp', 'ArrowDown'].includes(event.key) || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (window._ghostAutocomplete?.isActive?.()) return;
    if (event.key === 'ArrowUp' && !onFirstLine(textarea)) return;
    if (event.key === 'ArrowDown' && !onLastLine(textarea)) return;
    const sid = currentSession();
    if (!sid) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const prompts = await promptsFor(sid);
    if (!prompts.length) return;
    if (position === null) {
      draft = textarea.value;
      position = prompts.length;
    }
    position += event.key === 'ArrowUp' ? -1 : 1;
    position = Math.max(0, Math.min(prompts.length, position));
    applying = true;
    textarea.value = position === prompts.length ? draft : prompts[position];
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    applying = false;
  }, true);

  document.getElementById('chat-form')?.addEventListener('submit', () => {
    const sid = currentSession();
    const value = textarea.value.trim();
    if (!sid || !value) return;
    const prompts = cache.get(sid);
    if (prompts) prompts.push(value);
    position = null;
    draft = '';
  }, true);
  window.addEventListener('network-change:session-selected', () => {
    position = null;
    draft = '';
  });
}

export default { init: initPromptHistory };
