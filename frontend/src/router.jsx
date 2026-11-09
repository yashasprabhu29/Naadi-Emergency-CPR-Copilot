import { useEffect, useState } from "react";

const NAVIGATE_EVENT = "naadi:navigate";

function currentPath() {
  const path = window.location.pathname || "/";
  return path.length > 1 ? path.replace(/\/+$/, "") : "/";
}

export function navigate(to) {
  if (to === currentPath()) return;
  window.history.pushState({}, "", to);
  window.dispatchEvent(new Event(NAVIGATE_EVENT));
  window.scrollTo(0, 0);
}

export function usePath() {
  const [path, setPath] = useState(currentPath);

  useEffect(() => {
    const update = () => setPath(currentPath());
    window.addEventListener("popstate", update);
    window.addEventListener(NAVIGATE_EVENT, update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener(NAVIGATE_EVENT, update);
    };
  }, []);

  return path;
}

export function Link({ to, children, ...props }) {
  function handleClick(event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  }

  return (
    <a href={to} onClick={handleClick} {...props}>
      {children}
    </a>
  );
}
