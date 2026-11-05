// static/js/storage.js
// Centralized localStorage access with key constants and JSON parse safety

// ── Key constants (vhtna-* prefix) ──
export const KEYS = {
  THEME: 'vhtna-theme',
  TOGGLES: 'vhtna-toggles',
  SIDEBAR_COLLAPSED: 'sidebar-collapsed',
  SIDEBAR_WIDTH: 'sidebar-width',
  SIDEBAR_SIDE: 'sidebar-side',
  CURRENT_SESSION: 'currentSessionId',
  COMPARE_SAVE: 'compare-save-results',
  COMPARE_CHAT: 'compare-continue-chat',
  COMPARE_BLIND: 'compare-blind',
  COMPARE_RANDOM: 'compare-randomize',
  MODELS_EXPANDED: 'vhtna-model-expanded',
  MODEL_ENDPOINTS: 'vhtna-model-endpoints',
  MODEL_SELECTED: 'vhtna-selected-model',
  SORT_ORDER: 'vhtna-sessions-sort',
  CHAT_SEARCH_SCOPE: 'vhtna-search-scope',
  INCOGNITO: 'vhtna-incognito',
  RAG_ACTIVE: 'vhtna-rag-active',
  MCP_ACTIVE: 'vhtna-mcp-active',
  SECTION_ORDER: 'sidebar-section-order',
  ADMIN_LAST_TAB: 'admin-last-tab',
  DENSITY: 'vhtna-density'
};

// ── Old key constants (for migration) ──
const OLD_KEYS = {
  THEME: 'odysseus-theme',
  TOGGLES: 'odysseus-toggles',
  MODELS_EXPANDED: 'odysseus-model-expanded',
  MODEL_ENDPOINTS: 'odysseus-model-endpoints',
  MODEL_SELECTED: 'odysseus-selected-model',
  SORT_ORDER: 'odysseus-sessions-sort',
  CHAT_SEARCH_SCOPE: 'odysseus-search-scope',
  INCOGNITO: 'odysseus-incognito',
  RAG_ACTIVE: 'odysseus-rag-active',
  MCP_ACTIVE: 'odysseus-mcp-active',
  DENSITY: 'odysseus-density'
};

// Run one-time migration from old odysseus-* keys to new vhtna-* keys
(function _migrateOldKeys() {
  if (!localStorage) return;
  // Only run once
  if (localStorage.getItem('vhtna-migrated')) return;
  const oldToNew = {
    'odysseus-theme': 'vhtna-theme',
    'odysseus-toggles': 'vhtna-toggles',
    'odysseus-model-expanded': 'vhtna-model-expanded',
    'odysseus-model-endpoints': 'vhtna-model-endpoints',
    'odysseus-selected-model': 'vhtna-selected-model',
    'odysseus-sessions-sort': 'vhtna-sessions-sort',
    'odysseus-search-scope': 'vhtna-search-scope',
    'odysseus-incognito': 'vhtna-incognito',
    'odysseus-rag-active': 'vhtna-rag-active',
    'odysseus-mcp-active': 'vhtna-mcp-active',
    'odysseus-density': 'vhtna-density',
    'odysseus-sensitive-blur': 'vhtna-sensitive-blur',
    'odysseus-auth-user': 'vhtna-auth-user',
    'odysseus-last-user': 'vhtna-last-user',
    'odysseus-setup-guide-messages': 'vhtna-setup-guide-messages',
    'odysseus-custom-themes': 'vhtna-custom-themes',
    'odysseus-session-sort': 'vhtna-session-sort',
    'odysseus-folder-state': 'vhtna-folder-state',
    'odysseus-folder-order': 'vhtna-folder-order',
    'odysseus-research-settings': 'vhtna-research-settings',
    'odysseus-research-settings-collapsed': 'vhtna-research-settings-collapsed',
    'odysseus.email.bubblesDisabled': 'vhtna.email.bubblesDisabled',
    'odysseus.email.summaryCollapsed': 'vhtna.email.summaryCollapsed',
    'odysseus-ui-visibility': 'vhtna-ui-visibility',
    'odysseus-msg-actions-recent': 'vhtna-msg-actions-recent',
    'odysseus-user-actions-recent': 'vhtna-user-actions-recent'
  };
  for (const [oldKey, newKey] of Object.entries(oldToNew)) {
    try {
      const val = localStorage.getItem(oldKey);
      if (val !== null) {
        localStorage.setItem(newKey, val);
        localStorage.removeItem(oldKey);
      }
    } catch (_) {}
  }
  localStorage.setItem('vhtna-migrated', '1');
})();

/**
 * Safely get and parse a JSON value from localStorage.
 * Returns fallback on any error.
 */
export function getJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback !== undefined ? fallback : null;
    return JSON.parse(raw);
  } catch (e) {
    console.warn('[Storage] Failed to parse key "' + key + '":', e.message);
    return fallback !== undefined ? fallback : null;
  }
}

/**
 * Set a JSON-serialized value in localStorage.
 */
export function setJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn('[Storage] Failed to set key "' + key + '":', e.message);
  }
}

/**
 * Get a raw string value from localStorage.
 */
export function get(key, fallback) {
  try {
    const val = localStorage.getItem(key);
    return val !== null ? val : (fallback !== undefined ? fallback : null);
  } catch (e) {
    return fallback !== undefined ? fallback : null;
  }
}

/**
 * Set a raw string value in localStorage.
 */
export function set(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    console.warn('[Storage] Failed to set key "' + key + '":', e.message);
  }
}

/**
 * Remove a key from localStorage.
 */
export function remove(key) {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    // Ignore removal errors
  }
}

// ── Toggle state helpers ──

export function loadToggleState() {
  return getJSON(KEYS.TOGGLES, {});
}

export function saveToggleState(state) {
  setJSON(KEYS.TOGGLES, state);
}

export function getToggle(name, fallback) {
  const state = loadToggleState();
  return state[name] !== undefined ? state[name] : (fallback !== undefined ? fallback : false);
}

export function setToggle(name, value) {
  const state = loadToggleState();
  state[name] = value;
  saveToggleState(state);
}

const Storage = {
  KEYS,
  getJSON,
  setJSON,
  get,
  set,
  remove,
  loadToggleState,
  saveToggleState,
  getToggle,
  setToggle
};

export default Storage;