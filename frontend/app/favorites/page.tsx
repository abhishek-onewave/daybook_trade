import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "Favorites" };

export default function FavoritesPage() {
  return (
    <PageScaffold
      eyebrow="Your watchlist"
      title="Follow what matters."
      description="NVDA, AAPL, MSFT, TSLA, and AMD are ready as the initial set."
    />
  );
}

