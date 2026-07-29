import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "Stats" };

export default function StatsPage() {
  return (
    <PageScaffold
      eyebrow="Market pulse"
      title="The numbers at a glance."
      description="Indicative IEX quotes, index proxies, and dense watchlist statistics."
    />
  );
}

