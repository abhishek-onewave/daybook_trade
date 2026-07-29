import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "News" };

export default function NewsPage() {
  return (
    <PageScaffold
      eyebrow="Live briefing"
      title="News, without the noise."
      description="Watchlist-tagged reporting, source links, sentiment, and a plain-English read."
    />
  );
}

