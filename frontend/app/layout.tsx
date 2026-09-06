import type { Metadata } from "next";
import "./globals.css";
import WorkspaceCloseControl from "./workspace-close-control";

export const metadata: Metadata = {
  title: "ReverseEngineer-SDLC",
  description: "Reverse engineer GitHub repositories into SDLC documentation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><WorkspaceCloseControl />{children}</body></html>;
}
