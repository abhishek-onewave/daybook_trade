import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <PageScaffold
      eyebrow="Preferences"
      title="Make Daybook yours."
      description="Answer depth, refresh cadence, connection status, and usage controls."
      showClosingBand={false}
    />
  );
}

