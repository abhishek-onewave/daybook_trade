import type { Metadata } from "next";

import { DashboardQuotes } from "@/components/dashboard-quotes";
import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <PageScaffold
      eyebrow="Good morning, Tracy"
      title="Your market day, in context."
      description="Live, validated watchlist quotes and broad-market context — with every value tied to its source time."
    >
      <DashboardQuotes />
    </PageScaffold>
  );
}
