import { useEffect, useState } from "react";

import { Link } from "../router.jsx";
import { SITE } from "../site.js";

// Highlights the table-of-contents entry for the section being read.
function useActiveSection(ids) {
  const [active, setActive] = useState(ids[0]);

  useEffect(() => {
    if (typeof IntersectionObserver !== "function") return undefined;
    const visible = new Map();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) visible.set(entry.target.id, entry.isIntersecting);
        const first = ids.find((id) => visible.get(id));
        if (first) setActive(first);
      },
      { rootMargin: "-96px 0px -55% 0px", threshold: 0 },
    );
    for (const id of ids) {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, [ids]);

  return active;
}

export function LegalPage({ title, intro, highlights, sections, related }) {
  const ids = sections.map((section) => section.id);
  const [idsKey] = useState(() => ids);
  const active = useActiveSection(idsKey);

  return (
    <main className="legal" id="main">
      <header className="legal-hero reveal" style={{ "--reveal-order": 0 }}>
        <div className="legal-hero__copy">
          <p className="eyebrow eyebrow--accent">Legal</p>
          <h1>{title}</h1>
          <p className="legal-hero__intro">{intro}</p>
          <p className="legal-hero__updated">Last updated {SITE.legalUpdated}</p>
        </div>
        <ul className="glance" aria-label="At a glance">
          {highlights.map((item, index) => (
            <li key={item.title} className="glance__item" style={{ "--item": index }}>
              <span className="glance__title">{item.title}</span>
              <span className="glance__text">{item.text}</span>
            </li>
          ))}
        </ul>
      </header>

      <div className="legal-layout">
        <aside className="legal-toc reveal" style={{ "--reveal-order": 1 }}>
          <nav aria-label="On this page">
            <p className="legal-toc__label">On this page</p>
            <ol>
              {sections.map((section, index) => (
                <li key={section.id}>
                  <a
                    href={`#${section.id}`}
                    className={active === section.id ? "is-active" : undefined}
                    aria-current={active === section.id ? "location" : undefined}
                  >
                    <span className="legal-toc__num">{String(index + 1).padStart(2, "0")}</span>
                    {section.heading}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
          {related && (
            <div className="legal-toc__related">
              <span>See also</span>
              <Link to={related.to}>{related.label}</Link>
            </div>
          )}
        </aside>

        <article className="legal-article reveal" style={{ "--reveal-order": 2 }}>
          {sections.map((section, index) => (
            <section key={section.id} id={section.id} className="legal-section">
              <h2>
                <span className="legal-section__num">{String(index + 1).padStart(2, "0")}</span>
                {section.heading}
              </h2>
              <div className="legal-section__body">{section.body}</div>
            </section>
          ))}
          <p className="legal-article__contact">
            Questions? Write to <a href={`mailto:${SITE.contactEmail}`}>{SITE.contactEmail}</a>.
          </p>
        </article>
      </div>
    </main>
  );
}
