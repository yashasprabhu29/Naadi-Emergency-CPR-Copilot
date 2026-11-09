import { Link } from "../router.jsx";
import { SITE } from "../site.js";
import { LegalPage } from "./LegalPage.jsx";

const mail = <a href={`mailto:${SITE.contactEmail}`}>{SITE.contactEmail}</a>;

const sections = [
  {
    id: "who-we-are",
    heading: "Who we are",
    body: (
      <p>
        Naadi is a student prototype built by {SITE.operator}, for Gnani AI&apos;s Great Indian AI Internship
        Challenge. It is not a company, an emergency service or a medical service. You can reach us at {mail}.
      </p>
    ),
  },
  {
    id: "what-we-process",
    heading: "What we process and why",
    body: (
      <>
        <p>Naadi only processes what you give it on the console page.</p>
        <ul>
          <li>
            <strong>Audio you upload.</strong> Your browser sends the file to the Naadi backend. The backend writes it to a
            temporary file for the length of the request, sends it to Gnani AI&apos;s speech-to-text service for
            transcription, and deletes the temporary file when the request ends, whether it succeeds or fails.
          </li>
          <li>
            <strong>Live microphone audio.</strong> When you press Start listening, your browser streams microphone audio to
            the Naadi backend, which passes it straight to Gnani AI&apos;s realtime speech-to-text service. The audio is not
            recorded or stored by Naadi, and streaming stops when you press Stop listening or close the tab.
          </li>
          <li>
            <strong>The transcript.</strong> The backend returns the transcript to your browser. Your browser then sends the
            transcript text back to the backend for the emergency detection check. Nothing is stored unless you press Save
            call.
          </li>
          <li>
            <strong>Saved calls.</strong> When you press Save call, the backend stores the transcript, the detection result,
            the timings, and the label and noise condition you chose, in a database file on the server that runs Naadi.
            Audio and operator notes are never saved. You can delete any saved call, or all of them, on the Call log page.
          </li>
          <li>
            <strong>CPR coaching audio.</strong> Coaching instructions are fixed, pre-written sentences. Only that text is sent
            to Gnani AI to generate speech; nothing about your call is included.
          </li>
          <li>
            <strong>Operator notes.</strong> Notes you type stay in the memory of your browser tab. They are never sent to
            the backend and are lost when you reload or close the tab.
          </li>
          <li>
            <strong>Technical logs.</strong> The backend logs events such as file type, file size, model name, Gnani request
            ID and error codes. It does not log audio or transcript text. The web server&apos;s access log records the IP
            address, time and path of each request, which we use only to run and debug the service.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "gnani",
    heading: "Gnani AI",
    body: (
      <p>
        Transcription is performed by Gnani AI (Prisma speech-to-text) and coaching speech by Gnani AI (Timbre
        text-to-speech). When you upload or stream audio, Gnani AI receives that audio and processes it under its own privacy
        policy and terms, which are published on gnani.ai. We do not control how long
        Gnani AI keeps the audio it receives. We never send your notes, your IP address or any account details to Gnani AI.
      </p>
    ),
  },
  {
    id: "no-tracking",
    heading: "Cookies and tracking",
    body: (
      <p>
        Naadi sets no cookies and uses no analytics, advertising or tracking scripts. Fonts and icons are served from our own
        server, so loading the site does not contact any third party. On the public demo, the access code you enter is kept
        in your browser&apos;s session storage for this tab only, and is deleted when you close the tab.
      </p>
    ),
  },
  {
    id: "do-not-upload",
    heading: "Please do not upload real personal data",
    body: (
      <p>
        Upload only staged or synthetic recordings that use made-up names and places, recorded with the consent of everyone
        who speaks in them. Do not upload real emergency calls, phone numbers, Aadhaar or PAN numbers, bank details, or
        health information about real people.
      </p>
    ),
  },
  {
    id: "retention",
    heading: "How long we keep data",
    body: (
      <p>
        Uploaded audio is deleted at the end of each request, and live audio is never stored. Saved calls stay until you
        delete them on the Call log page. Access logs are kept only as long as our hosting setup retains them, and we do not
        use them for any purpose other than operating the service.
      </p>
    ),
  },
  {
    id: "your-choices",
    heading: "Your choices and requests",
    body: (
      <p>
        You can use the console without uploading or saving anything, and delete saved calls yourself on the Call log page.
        If you think we hold personal data about you, or you want something removed from our logs, write to {mail} and we
        will reply within 30 days.
      </p>
    ),
  },
  {
    id: "age",
    heading: "Age",
    body: <p>Naadi is intended for people aged 18 or older.</p>,
  },
  {
    id: "changes",
    heading: "Changes to this policy",
    body: (
      <p>
        If we change how Naadi handles data, we will update this page and the date at the top. See also our{" "}
        <Link to="/terms">terms and conditions</Link>.
      </p>
    ),
  },
];

export function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy policy"
      intro="This page explains what happens to the audio, transcripts and notes you use on the Naadi console."
      highlights={[
        { title: "Audio is never kept", text: "Uploads are deleted when the request ends, and live audio is not recorded." },
        { title: "Saved only when you choose", text: "Transcripts are stored only if you press Save call, and you can delete them." },
        { title: "Notes stay with you", text: "Operator notes never leave your browser tab." },
        { title: "No cookies or trackers", text: "No analytics, ads or third-party scripts." },
      ]}
      sections={sections}
      related={{ to: "/terms", label: "Terms and conditions" }}
    />
  );
}
