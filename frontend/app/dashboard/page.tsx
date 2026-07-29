import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <PageScaffold
      eyebrow="Good morning, Tracy"
      title="Your market day, in context."
      description="Quotes, watchlist signals, and the stories that matter will meet here."
    />
  );
}

