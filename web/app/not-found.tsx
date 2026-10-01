import Link from "next/link";

/** Site-styled 404 (replaces Next's default page, whose inline white body style ignored the dark theme). */
export default function NotFound() {
  return (
    <div className="panel" style={{ maxWidth: 560 }}>
      <h1 style={{ fontSize: "1.6rem" }}>Page not found</h1>
      <p className="ink2">This page does not exist. Forecasts for every game are on the weekly board.</p>
      <p style={{ marginBottom: 0 }}><Link href="/">Go to this week&apos;s forecasts →</Link></p>
    </div>
  );
}
