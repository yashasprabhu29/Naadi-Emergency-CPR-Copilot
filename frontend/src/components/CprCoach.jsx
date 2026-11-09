import { useCallback, useEffect, useRef, useState } from "react";

import { getPromptAudioUrl, listPrompts } from "../services/api.js";

const BPM = 110;
const BEAT_SECONDS = 60 / BPM;
const SWAP_EVERY_SECONDS = 120;

const LANGUAGES = [
  { code: "kn-IN", label: "Kannada", key: "kannada" },
  { code: "hi-IN", label: "Hindi", key: "hindi" },
  { code: "en-IN", label: "English", key: "english" },
];

function languageFor(code) {
  return LANGUAGES.find((language) => language.code === code) || LANGUAGES[2];
}

function clock(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/**
 * Hands-only CPR coaching after the operator has reviewed a flag.
 * Plays a pre-written Timbre instruction in the caller's language, then a
 * metronome at 110 compressions per minute with a live count.
 */
export function CprCoach({ detectedLanguage }) {
  const [language, setLanguage] = useState(() => languageFor(detectedLanguage).code);
  const [phase, setPhase] = useState("idle"); // idle | loading | speaking | pushing
  const [error, setError] = useState("");
  const [count, setCount] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [promptTexts, setPromptTexts] = useState({});
  const [nowPlaying, setNowPlaying] = useState(null);

  const audioRef = useRef(null);
  const ctxRef = useRef(null);
  const schedulerRef = useRef(null);
  const rafRef = useRef(null);
  const beatStartRef = useRef(0);
  const nextBeatRef = useRef(0);
  const sessionStartRef = useRef(0);
  const ringRef = useRef(null);
  const phaseRef = useRef("idle");

  const setPhaseSafe = (next) => {
    phaseRef.current = next;
    setPhase(next);
  };

  useEffect(() => {
    let cancelled = false;
    listPrompts()
      .then((body) => {
        if (cancelled || !body?.prompts) return;
        const texts = {};
        for (const [id, meta] of Object.entries(body.prompts)) texts[id] = meta.text;
        setPromptTexts(texts);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const stopBeat = useCallback(() => {
    if (schedulerRef.current) clearInterval(schedulerRef.current);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    schedulerRef.current = null;
    rafRef.current = null;
  }, []);

  const stopAll = useCallback(() => {
    stopBeat();
    audioRef.current?.pause();
    audioRef.current = null;
    if (ctxRef.current && ctxRef.current.state !== "closed") ctxRef.current.close().catch(() => {});
    ctxRef.current = null;
    setNowPlaying(null);
    setPhaseSafe("idle");
  }, [stopBeat]);

  useEffect(() => stopAll, [stopAll]);

  const click = (ctx, at) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = 1100;
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.5, at + 0.004);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.06);
    osc.connect(gain).connect(ctx.destination);
    osc.start(at);
    osc.stop(at + 0.07);
  };

  const startBeat = useCallback(() => {
    const ctx = ctxRef.current;
    if (!ctx) return;
    stopBeat();
    beatStartRef.current = ctx.currentTime + 0.1;
    nextBeatRef.current = beatStartRef.current;
    // Look-ahead scheduler: keeps the beat exact even if the page is busy.
    schedulerRef.current = setInterval(() => {
      while (nextBeatRef.current < ctx.currentTime + 0.15) {
        click(ctx, nextBeatRef.current);
        nextBeatRef.current += BEAT_SECONDS;
      }
    }, 25);
    const paint = () => {
      const t = ctx.currentTime - beatStartRef.current;
      if (t >= 0) {
        const phaseInBeat = (t % BEAT_SECONDS) / BEAT_SECONDS;
        ringRef.current?.style.setProperty("--beat", String(1 - Math.min(1, phaseInBeat * 3)));
        setCount(Math.floor(t / BEAT_SECONDS) + 1);
      }
      setElapsed(ctx.currentTime - sessionStartRef.current);
      rafRef.current = requestAnimationFrame(paint);
    };
    rafRef.current = requestAnimationFrame(paint);
    setPhaseSafe("pushing");
  }, [stopBeat]);

  const playPrompt = useCallback(async (kind) => {
    const { key } = languageFor(language);
    const promptId = `${kind}_${key}`;
    setError("");
    const resumeBeat = phaseRef.current === "pushing";
    if (!resumeBeat) setPhaseSafe("loading");

    let url;
    try {
      url = await getPromptAudioUrl(promptId);
    } catch (loadError) {
      setError(loadError.message);
      if (!resumeBeat) startBeat();
      return;
    }

    stopBeat();
    audioRef.current?.pause();
    const audio = new Audio(url);
    audioRef.current = audio;
    setNowPlaying(promptId);
    setPhaseSafe("speaking");
    const after = () => {
      if (audioRef.current !== audio) return;
      setNowPlaying(null);
      startBeat();
    };
    audio.onended = after;
    audio.onerror = () => {
      setError("The coaching audio could not play.");
      after();
    };
    try {
      await audio.play();
    } catch {
      setError("The browser blocked audio playback. Click Start again.");
      after();
    }
  }, [language, startBeat, stopBeat]);

  const start = useCallback(async () => {
    if (phaseRef.current !== "idle") return;
    const ctx = new AudioContext();
    await ctx.resume().catch(() => {});
    ctxRef.current = ctx;
    sessionStartRef.current = ctx.currentTime;
    setCount(0);
    setElapsed(0);
    await playPrompt("start_cpr");
  }, [playPrompt]);

  const active = phase !== "idle";
  // For the first 15 seconds of every two-minute block after the first.
  const swapDue = active && elapsed >= SWAP_EVERY_SECONDS && elapsed % SWAP_EVERY_SECONDS < 15;
  const currentText = promptTexts[nowPlaying || `start_cpr_${languageFor(language).key}`];

  return (
    <section className="panel coach reveal" style={{ "--reveal-order": 0 }} aria-labelledby="coach-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow"><span className="eyebrow__index">CPR</span>Hands-only coaching</p>
          <h2 id="coach-title">Coach the caller through CPR</h2>
        </div>
        <div className="segmented" role="group" aria-label="Coaching language">
          {LANGUAGES.map((option) => (
            <button
              key={option.code}
              type="button"
              className={`segmented__option${language === option.code ? " is-selected" : ""}`}
              aria-pressed={language === option.code}
              onClick={() => setLanguage(option.code)}
              disabled={phase === "speaking" || phase === "loading"}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="coach__body">
        <div className={`compressor compressor--${phase}`} ref={ringRef} aria-hidden="true">
          <svg viewBox="0 0 200 200" className="compressor__svg">
            <circle cx="100" cy="100" r="88" className="compressor__track" />
            <circle cx="100" cy="100" r="88" className="compressor__pulse" />
            <circle cx="100" cy="100" r="62" className="compressor__core" />
          </svg>
          <div className="compressor__readout">
            <span className="compressor__count">{count}</span>
            <span className="compressor__unit">compressions</span>
          </div>
        </div>

        <div className="coach__side">
          <dl className="coach__stats">
            <div><dt>Rate</dt><dd>{BPM} per minute</dd></div>
            <div><dt>Time</dt><dd>{clock(elapsed)}</dd></div>
            <div><dt>Status</dt><dd>{phase === "idle" ? "Not started" : phase === "loading" ? "Loading audio" : phase === "speaking" ? "Speaking instruction" : "Beat running"}</dd></div>
          </dl>

          {currentText && (
            <figure className="coach__script">
              <figcaption>{nowPlaying ? "Now playing" : "First instruction"}</figcaption>
              <blockquote lang={language.slice(0, 2)}>{currentText}</blockquote>
            </figure>
          )}

          {swapDue && <p className="coach__swap" role="status">Two minutes passed. If someone else is there, ask them to take over compressions.</p>}
          {error && <p className="inline-alert inline-alert--danger" role="alert">{error}</p>}

          <div className="coach__actions">
            {!active ? (
              <button type="button" className="button button--danger" onClick={start}>Start CPR coaching</button>
            ) : (
              <>
                <button type="button" className="button button--secondary" onClick={() => playPrompt("start_cpr")} disabled={phase === "speaking" || phase === "loading"}>
                  Repeat instruction
                </button>
                <button type="button" className="button button--secondary" onClick={() => playPrompt("check_breathing")} disabled={phase === "speaking" || phase === "loading"}>
                  Ask to check breathing
                </button>
                <button type="button" className="button button--ghost" onClick={stopAll}>Stop</button>
              </>
            )}
          </div>
          <p className="coach__note">
            Audio plays on this device. Put the call on speaker near it, or read the instruction to the caller.
            Instructions are generated by Gnani Timbre from a fixed, pre-written script.
          </p>
        </div>
      </div>
    </section>
  );
}
