import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "Portfolio" };

export default function PortfolioPage() {
  return (
    <PageScaffold
      eyebrow="Read-only brokerage"
      title="Portfolio intelligence."
      description="Balances, positions, and deterministic metrics will appear after a secure connection."
    />
  );
}

