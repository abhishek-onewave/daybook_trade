import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "Ask" };

export default function AskPage() {
  return (
    <PageScaffold
      eyebrow="Research assistant"
      title="Ask Daybook."
      description="A grounded conversation with app context, timestamps, and citations."
      showClosingBand={false}
    />
  );
}

