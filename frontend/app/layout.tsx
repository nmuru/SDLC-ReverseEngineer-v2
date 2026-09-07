import type { Metadata } from "next";
import "./globals.css";
import WorkspaceCloseControl from "./workspace-close-control";

export const metadata: Metadata = {
  title: "ReverseEngineer-SDLC",
  description: "Reverse engineer GitHub repositories into SDLC documentation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><WorkspaceCloseControl /><a className="guide-link" href="/using-reverse-sdlc.html" target="_blank" rel="noreferrer">Using Reverse SDLC · Recommended: run 3–4 phases at a time</a>{children}<style>{`body .guide-link { display: none; } body:has(.landing) .guide-link { display: block; position: fixed; top: 16px; right: 18px; z-index: 20; padding: 8px 12px; border: 1px solid var(--border, #d0d5dd); border-radius: 8px; background: var(--card, #fff); color: var(--accent, #175cd3); font-size: 12px; font-weight: 700; text-decoration: none; box-shadow: 0 2px 8px rgba(16,24,40,.06); } body:has(.landing) .guide-link:hover { text-decoration: underline; }`}</style></body></html>;
}
