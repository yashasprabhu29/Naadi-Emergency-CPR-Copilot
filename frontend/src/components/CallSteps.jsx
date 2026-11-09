import { CheckIcon, FileAudioIcon, LungsIcon, ShieldIcon, UploadIcon } from "./Icons.jsx";

const STEPS = [
  { title: "Load or stream a call", text: "A recording up to 30 seconds, or live from the microphone.", Icon: UploadIcon },
  { title: "Prisma transcribes it", text: "Gnani Prisma v3.0 writes out the caller's words, including mixed Kannada and English.", Icon: FileAudioIcon },
  { title: "Rules check two signs", text: "Unresponsive and not breathing normally, in the last three caller sentences.", Icon: LungsIcon },
  { title: "Review, then coach", text: "You confirm the flag, then Naadi coaches CPR in the caller's language.", Icon: ShieldIcon },
];

/**
 * @param {number} active 1-based index of the current step
 * @param {number|null} failed 1-based index of a step that failed, if any
 */
export function CallSteps({ active, failed = null }) {
  return (
    <ol className="steps reveal" style={{ "--reveal-order": 1 }} aria-label="How a call moves through Naadi">
      {STEPS.map((step, index) => {
        const number = index + 1;
        const state = failed === number ? "failed" : number < active ? "done" : number === active ? "current" : "upcoming";
        const { Icon } = step;
        return (
          <li key={step.title} className={`step step--${state}`} aria-current={state === "current" ? "step" : undefined}>
            <span className="step__marker" aria-hidden="true">
              {state === "done" ? <CheckIcon size={16} /> : <Icon size={16} />}
            </span>
            <div className="step__body">
              <span className="step__number">Step {number}</span>
              <span className="step__title">{step.title}</span>
              <span className="step__text">{step.text}</span>
            </div>
            <span className="step__bar" aria-hidden="true" />
          </li>
        );
      })}
    </ol>
  );
}
