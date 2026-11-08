/**
 * Utility functions for parsing transcripts into structured utterances.
 * 
 * This module handles the conversion of plain transcript text into
 * structured utterance objects that can be analyzed by the emergency
 * detection engine.
 */

/**
 * Parse a plain transcript into structured utterances.
 * 
 * Current implementation: Simple sentence-based splitting for single-speaker
 * transcripts. Future enhancements will add speaker diarization support.
 * 
 * @param {string} transcript - Raw transcript text
 * @param {string} defaultSpeaker - Default speaker role ('caller' or 'operator')
 * @param {Object} options - Parsing options
 * @returns {Array} Array of utterance objects
 */
export function parseTranscriptToUtterances(transcript, defaultSpeaker = "caller", options = {}) {
  if (!transcript || typeof transcript !== "string") {
    return [];
  }

  const {
    language = null,
    confidence = null,
    source = "sentence_boundary",
  } = options;

  // Simple sentence splitting (basic implementation)
  // Splits on sentence boundaries: . ! ?
  // Future: Use more sophisticated NLP or diarization data
  const sentences = transcript
    .split(/[.!?]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  // Convert to structured utterances
  return sentences.map((text, index) => ({
    text,
    speaker: defaultSpeaker,
    utterance_index: index,
    utterance_id: `utt-${Date.now()}-${index}`,
    timestamp: null,
    language,
    confidence,
    source,
  }));
}

/**
 * Parse transcript with manual speaker annotations.
 * 
 * Supports format like:
 * "CALLER: He is unconscious
 *  OPERATOR: Where is he?
 *  CALLER: Not breathing"
 * 
 * @param {string} transcript - Annotated transcript text
 * @returns {Array} Array of utterance objects
 */
export function parseAnnotatedTranscript(transcript) {
  if (!transcript || typeof transcript !== "string") {
    return [];
  }

  const lines = transcript.split("\n").filter((line) => line.trim());
  const utterances = [];

  lines.forEach((line, index) => {
    const callerMatch = line.match(/^CALLER:\s*(.+)$/i);
    const operatorMatch = line.match(/^OPERATOR:\s*(.+)$/i);

    if (callerMatch) {
      utterances.push({
        text: callerMatch[1].trim(),
        speaker: "caller",
        utterance_index: index,
        utterance_id: `utt-${Date.now()}-${index}`,
        timestamp: null,
        language: null,
        confidence: null,
        source: "manual",
      });
    } else if (operatorMatch) {
      utterances.push({
        text: operatorMatch[1].trim(),
        speaker: "operator",
        utterance_index: index,
        utterance_id: `utt-${Date.now()}-${index}`,
        timestamp: null,
        language: null,
        confidence: null,
        source: "manual",
      });
    } else {
      // Untagged line - default to caller
      utterances.push({
        text: line.trim(),
        speaker: "caller",
        utterance_index: index,
        utterance_id: `utt-${Date.now()}-${index}`,
        timestamp: null,
        language: null,
        confidence: null,
        source: "manual",
      });
    }
  });

  return utterances;
}

/**
 * Merge multiple single-utterance structures into one array.
 * Used when combining transcription results.
 * 
 * @param {Array} utteranceArrays - Arrays of utterances to merge
 * @returns {Array} Merged and re-indexed utterances
 */
export function mergeUtterances(...utteranceArrays) {
  const merged = [];
  let globalIndex = 0;

  for (const arr of utteranceArrays) {
    for (const utterance of arr) {
      merged.push({
        ...utterance,
        utterance_index: globalIndex++,
      });
    }
  }

  return merged;
}
