// Time parsing/formatting — the defensive layer for API timestamps.
//
// Server serializes canonical ISO-8601 UTC with a trailing 'Z'
// (core/time_utils.iso_utc). Older rows may still arrive zone-less
// (naive UTC from the legacy serializer) — those MUST be read as UTC,
// never as the browser's local zone, or every timestamp shifts by the
// local UTC offset.

/**
 * Parse an API timestamp to epoch milliseconds.
 * Zone-less strings (legacy) are treated as UTC; invalid input -> null.
 */
export const parseTs = (s) => {
  if (!s) return null;
  const t = Date.parse(s); // canonical "...Z" / "+00:00" — exact
  if (!Number.isNaN(t)) return t;
  // Legacy zone-less forms: "YYYY-MM-DDTHH:MM:SS[.ffffff]" or "YYYY-MM-DD"
  const iso = /\d{4}-\d{2}-\d{2}T/.test(s) ? s : `${s}T00:00:00`;
  const t2 = Date.parse(`${iso}Z`);
  return Number.isNaN(t2) ? null : t2;
};

/**
 * Format an API timestamp for display; '' for null/invalid.
 */
export const fmtTs = (s) => {
  const t = parseTs(s);
  return t === null ? '' : new Date(t).toLocaleString();
};
