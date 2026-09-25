"use client";
import { usePathname } from "next/navigation";

const LINKS = [
  ["/", "Forecasts"],
  ["/performance/", "Performance"],
  ["/ratings/", "Team ratings"],
  ["/methodology/", "Methodology"],
  ["/about/", "About"],
] as const;

export default function Nav() {
  const path = usePathname() || "/";
  return (
    <nav className="nav" aria-label="Main">
      {LINKS.map(([href, label]) => {
        const active = href === "/" ? path === "/" || path.startsWith("/week") || path.startsWith("/game") : path.startsWith(href);
        return <a key={href} href={href} className={active ? "active" : undefined}>{label}</a>;
      })}
    </nav>
  );
}
