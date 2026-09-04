import type { Metadata } from "next";

import "./globals.css";
import "./broker.css";
import "./dual.css";
import "./admin.css";

export const metadata: Metadata = {
  title: "AlphaDesk — Paper Options Desk",
  description: "A deterministic, paper-only options research and execution desk.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
