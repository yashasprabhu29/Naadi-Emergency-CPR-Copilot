import { Link } from "../router.jsx";
import { SITE } from "../site.js";
import { LegalPage } from "./LegalPage.jsx";

const sections = [
  {
    id: "acceptance",
    heading: "Using Naadi",
    body: (
      <p>
        These terms apply to the Naadi website and console, run by {SITE.operator}. By using Naadi you agree to them. If you
        do not agree, please do not use the site.
      </p>
    ),
  },
  {
    id: "not-emergency",
    heading: "Not an emergency or medical service",
    body: (
      <>
        <p className="legal__callout">
          In an emergency, call {SITE.emergencyNumbers}. Naadi is not connected to any emergency service and cannot send help.
        </p>
        <p>
          Naadi is a prototype built for a student challenge. It is not a medical device, has not been clinically validated,
          and must not be used to make decisions about a real patient.
        </p>
      </>
    ),
  },
  {
    id: "accuracy",
    heading: "Results can be wrong",
    body: (
      <p>
        Transcripts can contain errors, especially on noisy or mixed-language audio. The emergency detector uses fixed
        phrase rules and can miss a real emergency or flag one that is not there. Treat every result as a prompt for a human
        to check, never as a conclusion.
      </p>
    ),
  },
  {
    id: "your-uploads",
    heading: "What you may upload",
    body: (
      <>
        <p>Upload only audio that you have the right to use and that everyone recorded has agreed to share. You must not upload:</p>
        <ul>
          <li>recordings of real emergency calls or real patients;</li>
          <li>anyone&apos;s phone number, Aadhaar, PAN, bank or card details, or health records;</li>
          <li>recordings of people who have not agreed to be recorded;</li>
          <li>anything unlawful, abusive or infringing.</li>
        </ul>
        <p>
          You keep ownership of what you upload. You allow us to process it only to return a transcript and a detection
          result to you, as described in our <Link to="/privacy">privacy policy</Link>.
        </p>
      </>
    ),
  },
  {
    id: "fair-use",
    heading: "Fair use",
    body: (
      <p>
        Do not try to overload the service, get around usage limits, access the server or its API keys, or interfere with
        other users. We may limit or block access to protect the service and the credits it runs on.
      </p>
    ),
  },
  {
    id: "third-parties",
    heading: "Third-party services",
    body: (
      <p>
        Transcription is provided by Gnani AI. Naadi works only while Gnani AI&apos;s service is available and our account
        has credits. Gnani AI&apos;s own terms apply to its service.
      </p>
    ),
  },
  {
    id: "ip",
    heading: "Our work",
    body: (
      <p>
        The Naadi code, design and written content belong to the Naadi project team, except third-party libraries and fonts,
        which remain under their own licences.
      </p>
    ),
  },
  {
    id: "warranty",
    heading: "No warranty and limited liability",
    body: (
      <p>
        Naadi is provided as is, without any warranty. To the extent the law allows, the Naadi project team is not liable for
        any loss or harm arising from using or relying on the site or its results.
      </p>
    ),
  },
  {
    id: "changes",
    heading: "Changes and availability",
    body: (
      <p>
        We may change these terms, change the site or take it offline at any time. Changes take effect when we update this
        page and the date at the top.
      </p>
    ),
  },
  {
    id: "law",
    heading: "Governing law",
    body: <p>These terms are governed by the laws of India. Courts in Mysuru, Karnataka have jurisdiction.</p>,
  },
];

export function TermsPage() {
  return (
    <LegalPage
      title="Terms and conditions"
      intro="The rules for using the Naadi prototype. Please read the section on emergencies first."
      highlights={[
        { title: "Not an emergency service", text: `In an emergency, call ${SITE.emergencyNumbers}.` },
        { title: "Results can be wrong", text: "A person must check every transcript and flag." },
        { title: "Staged audio only", text: "No real calls, patients or personal numbers." },
        { title: "Provided as is", text: "A student prototype with no warranty." },
      ]}
      sections={sections}
      related={{ to: "/privacy", label: "Privacy policy" }}
    />
  );
}
