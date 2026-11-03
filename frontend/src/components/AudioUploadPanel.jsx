import { useRef, useState } from "react";

import {
  MAX_UPLOAD_SIZE_BYTES,
  SUPPORTED_AUDIO_EXTENSIONS,
  validateAudioFile,
} from "../services/api.js";

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function AudioUploadPanel({ selectedFile, onFileSelected, onSubmit, status, error }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const isUploading = status === "uploading";

  function handleFile(file) {
    const validationError = validateAudioFile(file);
    onFileSelected(file, validationError);
  }

  function handleInputChange(event) {
    handleFile(event.target.files?.[0] || null);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    handleFile(event.dataTransfer.files?.[0] || null);
  }

  return (
    <section className="panel upload-panel" aria-labelledby="upload-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">STAGED AUDIO INTAKE</p>
          <h2 id="upload-title">Load a call recording</h2>
        </div>
        <span className="panel-index">01</span>
      </div>

      <div
        className={`dropzone ${isDragging ? "dropzone--active" : ""} ${selectedFile ? "dropzone--selected" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          className="visually-hidden"
          id="audio-file"
          aria-label="Choose audio recording"
          type="file"
          accept={SUPPORTED_AUDIO_EXTENSIONS.join(",")}
          onChange={handleInputChange}
          disabled={isUploading}
        />
        <div className="dropzone-icon" aria-hidden="true">⇧</div>
        <p className="dropzone-title">Drop an emergency-call recording here</p>
        <p className="dropzone-copy">or choose a file from this workstation</p>
        <button
          type="button"
          className="button button--secondary"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
        >
          Browse recordings
        </button>
      </div>

      <div className="upload-constraints">
        <span>WAV · MP3 · OGG · FLAC · AAC · M4A</span>
        <span>Maximum 30 seconds via Prisma</span>
        <span>Local limit {formatBytes(MAX_UPLOAD_SIZE_BYTES)}</span>
      </div>

      {selectedFile && (
        <div className="selected-file" aria-label="Selected audio file">
          <div className="file-icon" aria-hidden="true">♫</div>
          <div className="selected-file__meta">
            <strong>{selectedFile.name}</strong>
            <span>{formatBytes(selectedFile.size)} · ready for transcription</span>
          </div>
          <span className="selected-file__check" aria-label="File selected">✓</span>
        </div>
      )}

      {error && <div className="inline-alert inline-alert--danger" role="alert">{error}</div>}

      {isUploading && (
        <div className="upload-progress" role="status" aria-live="polite">
          <div className="progress-track"><div className="progress-indicator" /></div>
          <span>Sending recording to Prisma…</span>
        </div>
      )}

      <button
        type="button"
        className="button button--primary button--full"
        onClick={onSubmit}
        disabled={!selectedFile || Boolean(error) || isUploading}
      >
        {isUploading ? "Transcribing recording" : "Transcribe staged call"}
        {!isUploading && <span aria-hidden="true">→</span>}
      </button>
    </section>
  );
}
