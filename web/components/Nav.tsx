"use client";
import Link from "next/link";
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
        return <Link key={href} href={href} className={active ? "active" : undefined}>{label}</Link>;
      })}
    </nav>
  );
}
