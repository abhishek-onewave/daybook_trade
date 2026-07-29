import type { Metadata } from "next";

import { SiteHeader } from "@/components/site-header";
import "@/styles/tokens.css";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Daybook",
    template: "%s · Daybook",
  },
  description: "Personal market research for Tracy.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <SiteHeader />
        <main>{children}</main>
        <footer className="site-footer">
          <p>Daybook explains markets. It doesn&apos;t recommend trades.</p>
        </footer>
      </body>
    </html>
  );
}

