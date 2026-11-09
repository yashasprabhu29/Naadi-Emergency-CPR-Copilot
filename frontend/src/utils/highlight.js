/**
 * Split a transcript into plain and highlighted segments for the phrases the
 * detector matched. Matching is case-insensitive and Unicode-normalised. A
 * phrase that does not occur verbatim in the transcript is skipped, so the
 * transcript text itself is never altered.
 *
 * @param {string} text
 * @param {Array<{phrase: string, category: string}>} indicators
 * @returns {Array<{text: string, category: string | null}>}
 */
export function highlightSegments(text, indicators) {
  if (!text) return [];
  if (!Array.isArray(indicators) || indicators.length === 0) {
    return [{ text, category: null }];
  }

  const normalised = text.normalize("NFC");
  const haystack = normalised.toLocaleLowerCase();
  // Lowercasing can change string length for a few characters; fall back to
  // no highlighting rather than risk misaligned offsets.
  if (haystack.length !== normalised.length) {
    return [{ text: normalised, category: null }];
  }

  const ranges = [];
  for (const indicator of indicators) {
    const phrase = (indicator?.phrase || "").normalize("NFC").toLocaleLowerCase().trim();
    if (!phrase) continue;
    let from = 0;
    while (from <= haystack.length - phrase.length) {
      const at = haystack.indexOf(phrase, from);
      if (at === -1) break;
      ranges.push({ start: at, end: at + phrase.length, category: indicator.category || null });
      from = at + phrase.length;
    }
  }

  if (ranges.length === 0) return [{ text: normalised, category: null }];

  // Earliest first, then longest first; drop overlaps.
  ranges.sort((a, b) => a.start - b.start || b.end - a.end);
  const kept = [];
  let cursor = 0;
  for (const range of ranges) {
    if (range.start < cursor) continue;
    kept.push(range);
    cursor = range.end;
  }

  const segments = [];
  let position = 0;
  for (const range of kept) {
    if (range.start > position) {
      segments.push({ text: normalised.slice(position, range.start), category: null });
    }
    segments.push({ text: normalised.slice(range.start, range.end), category: range.category });
    position = range.end;
  }
  if (position < normalised.length) {
    segments.push({ text: normalised.slice(position), category: null });
  }
  return segments;
}
