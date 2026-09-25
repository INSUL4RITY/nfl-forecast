import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "nflcast · NFL game forecasts",
  description: "Expected scores, margins, totals and win probabilities for every NFL game, with transparent validation.",
};

function Mark() {
  // Original simple mark: a yard-line grid with a rising forecast line.
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
      <rect x="1" y="1" width="26" height="26" rx="6" fill="#13213c" />
      <path d="M7 5v18M14 5v18M21 5v18" stroke="#3a4d73" strokeWidth="1.5" />
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
            <a href="/" className="brand"><Mark /> nflcast <small>NFL forecasts</small></a>
            <Nav />
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="site-footer">
          <div className="container">
            Forecasts are produced by a Python pipeline and published as versioned files; this site only displays them.
            Only the market point spread and total are used as market inputs; no betting prices. Not betting advice.
            Data: <a href="https://github.com/nflverse">nflverse</a> (CC-BY 4.0). Presentation inspired by, but independent of, davidsasser.com/nfl.
          </div>
        </footer>
      </body>
    </html>
  );
}
