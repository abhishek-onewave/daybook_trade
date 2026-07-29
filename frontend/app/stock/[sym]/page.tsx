import type { Metadata } from "next";

import { PageScaffold } from "@/components/page-scaffold";

type StockPageProps = {
  params: Promise<{ sym: string }>;
};

export async function generateMetadata({
  params,
}: StockPageProps): Promise<Metadata> {
  const { sym } = await params;
  return { title: sym.toUpperCase() };
}

export default async function StockPage({ params }: StockPageProps) {
  const { sym } = await params;
  const symbol = sym.toUpperCase();
  return (
    <PageScaffold
      eyebrow="Stock detail"
      title={symbol}
      description={`Quote history, key figures, and sourced news for ${symbol}.`}
    />
  );
}
