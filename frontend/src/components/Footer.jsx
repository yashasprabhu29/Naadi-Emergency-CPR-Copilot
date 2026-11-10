import { Link } from "../router.jsx";
import { SITE } from "../site.js";
import { NaadiMark, PhoneIcon } from "./Icons.jsx";

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div className="footer__brand">
          <div className="footer__name">
            <NaadiMark size={26} />
            <span>{SITE.name} <span lang="kn" className="brand__kn">{SITE.nameKannada}</span></span>
          </div>
          <p>
            A student prototype for Gnani AI&apos;s Great Indian AI Internship Challenge. Speech-to-text by Gnani Prisma,
            coaching audio by Gnani Timbre. Not a medical device.
          </p>
        </div>

        <div className="footer__col">
          <p className="footer__heading">Product</p>
          <Link to="/">Operator console</Link>
          <Link to="/calls">Call log</Link>
          <a href={SITE.repoUrl} target="_blank" rel="noreferrer">Source code</a>
        </div>

        <div className="footer__col">
          <p className="footer__heading">Legal</p>
          <Link to="/privacy">Privacy policy</Link>
          <Link to="/terms">Terms and conditions</Link>
        </div>

        <div className="footer__emergency">
          <PhoneIcon size={18} />
          <div>
            <p className="footer__heading">In an emergency</p>
            <p>Call {SITE.emergencyNumbers}. Naadi cannot send help.</p>
          </div>
        </div>
      </div>
      <div className="footer__base">
        <span>{SITE.name} prototype, {new Date().getFullYear()}</span>
        <span>Staged and synthetic audio only</span>
      </div>
    </footer>
  );
}
