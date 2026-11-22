import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import Nav from "@/components/Nav";

const SITE = "https://insul4rity.github.io/nfl-forecast/";
const DESC = "Expected scores, win probabilities, margins and totals for every NFL game, compared with the market and validated openly.";

// Open Graph / Twitter preview (display only, 2026-11-20): public/og.png is built by scripts/og_image.mjs.
export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: "Insularity NFL Forecast",
  description: DESC,
  openGraph: {
    type: "website", url: SITE, siteName: "Insularity NFL Forecast", title: "Insularity NFL Forecast", description: DESC,
    locale: "en_GB",
    images: [{ url: "og.png", width: 1200, height: 630, alt: "Insularity NFL Forecast: model lines set against the market line" }],
  },
  twitter: {
    card: "summary_large_image", title: "Insularity NFL Forecast", description: DESC,
    images: [{ url: "og.png", alt: "Insularity NFL Forecast: model lines set against the market line" }],
  },
};

function Mark() {
  // Original simple mark: a yard-line grid with a rising forecast line.
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
      <rect x="1" y="1" width="26" height="26" rx="6" fill="#1f4e8c" />
      <path d="M7 5v18M14 5v18M21 5v18" stroke="#3d6db5" strokeWidth="1.5" />
      <path d="M5 19l6-5 5 3 7-9" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="container">
            <Link href="/" className="brand"><Mark /> <span className="brand-name">INSULARITY</span> <small>NFL Forecast</small></Link>
            <Nav />
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="site-footer">
          <div className="container">
            Forecasts are produced by a Python pipeline and published as versioned files; this site only displays them.
            Only the market point spread and total are used as market inputs; no prices. For analysis and education only.
            Data: <a href="https://github.com/nflverse">nflverse</a> (CC-BY 4.0).
          </div>
        </footer>
      </body>
    </html>
  );
}
