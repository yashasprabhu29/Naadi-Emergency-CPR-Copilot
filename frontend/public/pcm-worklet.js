// Turns microphone audio into 1,024-byte frames of 16-bit mono PCM
// (512 samples), the exact frame size Gnani's realtime API requires.
// Runs on the audio thread, so frames leave at real-time cadence.
class PcmFrameProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.frame = new Int16Array(512);
    this.filled = 0;
    this.levelSum = 0;
    this.levelCount = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;

    for (let i = 0; i < channel.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, channel[i]));
      this.frame[this.filled] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      this.filled += 1;
      this.levelSum += sample * sample;
      this.levelCount += 1;

      if (this.filled === this.frame.length) {
        const level = Math.sqrt(this.levelSum / this.levelCount);
        const buffer = this.frame.buffer.slice(0);
        this.port.postMessage({ frame: buffer, level }, [buffer]);
        this.filled = 0;
        this.levelSum = 0;
        this.levelCount = 0;
      }
    }
    return true;
  }
}

registerProcessor("pcm-frame-processor", PcmFrameProcessor);
