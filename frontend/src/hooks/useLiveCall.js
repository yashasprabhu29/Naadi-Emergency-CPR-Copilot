import { useCallback, useEffect, useRef, useState } from "react";

import { streamUrl } from "../services/api.js";

const ACCEPTED_RATES = new Set([8000, 16000, 44100, 48000]);

/**
 * Streams the microphone to the Naadi backend, which relays it to Gnani
 * Prisma realtime STT. Returns live state plus start/stop controls.
 * onTranscript(utterances) runs after every committed sentence.
 */
export function useLiveCall({ onTranscript } = {}) {
  const [status, setStatus] = useState("idle"); // idle | connecting | live | stopping | ended | error
  const [error, setError] = useState("");
  const [utterances, setUtterances] = useState([]);
  const [level, setLevel] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const [config, setConfig] = useState(null);

  const resources = useRef({});
  const startedAt = useRef(null);
  const utterancesRef = useRef([]);
  const statusRef = useRef("idle");
  const callbackRef = useRef(onTranscript);
  callbackRef.current = onTranscript;

  const updateStatus = useCallback((next) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  const releaseAudio = useCallback(() => {
    const { stream, context, node, timer, raf } = resources.current;
    if (node) node.port.onmessage = null;
    stream?.getTracks().forEach((track) => track.stop());
    if (context && context.state !== "closed") context.close().catch(() => {});
    if (timer) clearInterval(timer);
    if (raf) cancelAnimationFrame(raf);
    resources.current = { socket: resources.current.socket };
    setLevel(0);
    setSpeaking(false);
  }, []);

  const releaseAll = useCallback(() => {
    releaseAudio();
    const { socket } = resources.current;
    if (socket && socket.readyState <= WebSocket.OPEN) socket.close();
    resources.current = {};
  }, [releaseAudio]);

  useEffect(() => releaseAll, [releaseAll]);

  const fail = useCallback((message) => {
    setError(message);
    updateStatus("error");
    releaseAll();
  }, [releaseAll, updateStatus]);

  const start = useCallback(async () => {
    if (statusRef.current === "connecting" || statusRef.current === "live" || statusRef.current === "stopping") return;
    if (!navigator.mediaDevices?.getUserMedia || typeof AudioWorkletNode === "undefined") {
      fail("This browser cannot stream the microphone. Use a recent Chrome, Edge or Firefox.");
      return;
    }

    setError("");
    setUtterances([]);
    utterancesRef.current = [];
    setElapsed(0);
    setConfig(null);
    startedAt.current = null;
    updateStatus("connecting");

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
    } catch (micError) {
      fail(micError?.name === "NotAllowedError"
        ? "Microphone access was blocked. Allow it in the address bar and try again."
        : "No microphone was found.");
      return;
    }

    let context;
    let source;
    try {
      // 16 kHz is Gnani's native rate. Some browsers cannot resample the
      // microphone, so fall back to the device rate (Gnani resamples 44.1/48 kHz).
      try {
        context = new AudioContext({ sampleRate: 16000 });
        source = context.createMediaStreamSource(stream);
      } catch {
        if (context) context.close().catch(() => {});
        context = new AudioContext();
        source = context.createMediaStreamSource(stream);
      }
      if (!ACCEPTED_RATES.has(context.sampleRate)) {
        throw new Error(`The microphone runs at ${context.sampleRate} Hz, which Gnani does not accept.`);
      }
      await context.audioWorklet.addModule("/pcm-worklet.js");
    } catch (setupError) {
      stream.getTracks().forEach((track) => track.stop());
      if (context) context.close().catch(() => {});
      fail(setupError?.message?.includes("Hz") ? setupError.message : "Could not start audio capture in this browser.");
      return;
    }

    const node = new AudioWorkletNode(context, "pcm-frame-processor");
    const silent = context.createGain();
    silent.gain.value = 0;
    source.connect(node);
    node.connect(silent).connect(context.destination);

    const socket = new WebSocket(`${streamUrl()}?sample_rate=${context.sampleRate}`);
    socket.binaryType = "arraybuffer";
    resources.current = { stream, context, node, socket };

    let latestLevel = 0;
    node.port.onmessage = (event) => {
      latestLevel = event.data.level;
      if (statusRef.current === "live" && socket.readyState === WebSocket.OPEN) {
        socket.send(event.data.frame);
      }
    };
    const paintLevel = () => {
      setLevel((previous) => previous * 0.6 + Math.min(1, latestLevel * 4) * 0.4);
      resources.current.raf = requestAnimationFrame(paintLevel);
    };
    resources.current.raf = requestAnimationFrame(paintLevel);

    socket.onmessage = (event) => {
      if (typeof event.data !== "string") return;
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (message.type === "ready") {
        startedAt.current = performance.now();
        setConfig(message);
        updateStatus("live");
        resources.current.timer = setInterval(() => {
          setElapsed((performance.now() - startedAt.current) / 1000);
        }, 250);
      } else if (message.type === "speech_start") {
        setSpeaking(true);
      } else if (message.type === "transcript") {
        setSpeaking(false);
        const at = startedAt.current ? (performance.now() - startedAt.current) / 1000 : 0;
        const next = [
          ...utterancesRef.current,
          {
            text: message.text,
            language: message.detected_language_code || null,
            index: utterancesRef.current.length,
            latencyMs: message.latency_ms ?? null,
            at,
          },
        ];
        utterancesRef.current = next;
        setUtterances(next);
        callbackRef.current?.(next, startedAt.current);
      } else if (message.type === "error") {
        setError(message.message || "The live session failed.");
      } else if (message.type === "ended") {
        updateStatus("ended");
      }
    };
    socket.onclose = () => {
      releaseAudio();
      if (statusRef.current === "ended" || statusRef.current === "error") return;
      if (statusRef.current === "stopping") {
        updateStatus("ended");
      } else {
        setError((current) => current || "The live connection closed.");
        updateStatus("error");
      }
    };
    socket.onerror = () => {
      setError((current) => current || "Cannot reach the Naadi backend for live audio.");
    };
  }, [fail, releaseAudio, updateStatus]);

  const stop = useCallback(() => {
    const { socket, stream } = resources.current;
    if (statusRef.current !== "live" && statusRef.current !== "connecting") return;
    updateStatus("stopping");
    // Stop listening at once; the server returns the last open sentence.
    stream?.getTracks().forEach((track) => track.stop());
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "stop" }));
    } else {
      releaseAll();
      updateStatus("ended");
    }
  }, [releaseAll, updateStatus]);

  const reset = useCallback(() => {
    if (statusRef.current === "live" || statusRef.current === "connecting" || statusRef.current === "stopping") return;
    setUtterances([]);
    utterancesRef.current = [];
    setError("");
    setElapsed(0);
    updateStatus("idle");
  }, [updateStatus]);

  return { status, error, utterances, level, elapsed, speaking, config, start, stop, reset };
}
