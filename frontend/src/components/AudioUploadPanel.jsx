import { useRef, useState } from "react";

import {
  MAX_UPLOAD_SIZE_BYTES,
  SUPPORTED_AUDIO_EXTENSIONS,
  validateAudioFile,
} from "../services/api.js";
import { formatDuration } from "../utils/audioDuration.js";
import { ArrowRightIcon, CheckIcon, FileAudioIcon, UploadIcon } from "./Icons.jsx";

function formatBytes(bytes) {
  // Number() drops trailing zeros, so 25 MiB reads "25 MB" rather than "25.00 MB".
  if (bytes < 1024 * 1024) return `${Number((bytes / 1024).toFixed(1))} KB`;
  return `${Number((bytes / (1024 * 1024)).toFixed(2))} MB`;
}

export function AudioUploadPanel({ selectedFile, fileDuration, onFileSelected, onSubmit, status, error, modeSwitch }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const isUploading = status === "uploading";

  function handleFile(file) {
    const validationError = validateAudioFile(file);
    onFileSelected(file, validationError);
  }

  function handleInputChange(event) {
    handleFile(event.target.files?.[0] || null);
    // Allow choosing the same file again after an error.
    event.target.value = "";
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    if (isUploading) return;
    handleFile(event.dataTransfer.files?.[0] || null);
  }

  const dropzoneClass = [
    "dropzone",
    isDragging ? "dropzone--active" : "",
    selectedFile && !error ? "dropzone--selected" : "",
  ].filter(Boolean).join(" ");

  return (
    <section className="panel upload-panel reveal" style={{ "--reveal-order": 1 }} aria-labelledby="upload-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow"><span className="eyebrow__index">01</span>Staged audio</p>
          <h2 id="upload-title">Load a call recording</h2>
        </div>
        {modeSwitch}
      </div>

      <div
        className={dropzoneClass}
        onDragEnter={(event) => { event.preventDefault(); if (!isUploading) setIsDragging(true); }}
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
        <span className="dropzone__icon"><UploadIcon size={20} /></span>
        <p className="dropzone__title">Drop a staged call recording here</p>
        <p className="dropzone__copy">Use role-play calls with made-up names and places only.</p>
        <button
          type="button"
          className="button button--secondary"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
        >
          Browse files
        </button>
      </div>

      <ul className="upload-constraints" aria-label="Upload requirements">
        <li>WAV, MP3, OGG, FLAC, AAC or M4A</li>
        <li>Up to 30 seconds of audio</li>
        <li>File size up to {formatBytes(MAX_UPLOAD_SIZE_BYTES)}</li>
      </ul>

      {selectedFile && (
        <div className={`selected-file${error ? " selected-file--invalid" : ""}`} aria-label="Selected audio file">
          <span className="selected-file__icon"><FileAudioIcon /></span>
          <div className="selected-file__meta">
            <strong title={selectedFile.name}>{selectedFile.name}</strong>
            <span>
              {formatBytes(selectedFile.size)}
              {fileDuration != null ? `, ${formatDuration(fileDuration)}` : ""}
              {error ? "" : ", ready to transcribe"}
            </span>
          </div>
          {!error && <span className="selected-file__check" aria-label="File selected"><CheckIcon size={16} /></span>}
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
        {!isUploading && <ArrowRightIcon size={16} />}
      </button>
    </section>
  );
}
