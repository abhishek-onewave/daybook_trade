import type { Metadata } from "next";

import { SiteHeader } from "@/components/site-header";
import { environmentFlag } from "@/lib/environment";
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
  const demoMode = environmentFlag(process.env.DAYBOOK_DEMO_MODE);

  return (
    <html lang="en">
      <body>
        {demoMode ? (
          <div className="demo-banner" role="status">
            Preview mode · Live market, AI, brokerage, and Supabase connections
            are not configured.
          </div>
        ) : null}
        <SiteHeader />
        <main>{children}</main>
        <footer className="site-footer">
          <p>Daybook explains markets. It doesn&apos;t recommend trades.</p>
        </footer>
      </body>
    </html>
  );
}
