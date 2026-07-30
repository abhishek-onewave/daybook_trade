"use client";

import { useEffect, useState } from "react";

type CapabilityState =
  | "ready"
  | "not_configured"
  | "disabled_in_demo"
  | "pending_phase";

type Capability = {
  configured: boolean;
  enabled: boolean;
  implemented: boolean;
  state: CapabilityState;
};

type HealthPayload = {
  mode: "demo" | "live";
  database: {
    connected: boolean;
    persistent: boolean;
  };
  capabilities: Record<
    "alpaca" | "anthropic" | "finnhub" | "tastytrade",
    Capability
  >;
};

const PROVIDERS = [
  {
    key: "alpaca",
    name: "Alpaca",
    purpose: "Market quotes and historical bars",
  },
  {
    key: "anthropic",
    name: "Anthropic",
    purpose: "Ask Daybook and news enrichment",
  },
  {
    key: "finnhub",
    name: "Finnhub",
    purpose: "Watchlist news feed",
  },
  {
    key: "tastytrade",
    name: "Tastytrade",
    purpose: "Read-only portfolio data",
  },
] as const;

const STATE_COPY: Record<
  CapabilityState,
  { label: string; detail: string }
> = {
  ready: {
    label: "Ready",
    detail: "Configured and available to this deployment.",
  },
  not_configured: {
    label: "Not connected",
    detail: "Daybook continues without this provider.",
  },
  disabled_in_demo: {
    label: "Preview disabled",
    detail: "Configured, but protected from use in public preview mode.",
  },
  pending_phase: {
    label: "Integration pending",
    detail: "Credentials detected; the gated integration is not built yet.",
  },
};

export function IntegrationStatus() {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/health", {
          cache: "no-store",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Health returned HTTP ${response.status}.`);
        }
        setHealth((await response.json()) as HealthPayload);
      } catch {
        if (!controller.signal.aborted) {
          setError("Connection status is temporarily unavailable.");
        }
      }
    }

    void load();
    return () => controller.abort();
  }, []);

  return (
    <section className="integration-panel" aria-labelledby="connections-title">
      <div className="card-heading">
        <div>
          <p className="section-kicker">Connections</p>
          <h2 id="connections-title">Use what&apos;s available.</h2>
          <p className="integration-intro">
            Each provider activates independently. Missing credentials never
            stop the rest of Daybook.
          </p>
        </div>
        {health ? (
          <span className="mode-badge">
            {health.mode === "demo" ? "Preview mode" : "Live mode"}
          </span>
        ) : null}
      </div>

      {error ? <p className="integration-error">{error}</p> : null}
      {!health && !error ? (
        <div className="integration-loading" aria-label="Loading connections">
          Checking configured providers…
        </div>
      ) : null}

      {health ? (
        <>
          <div className="integration-grid">
            {PROVIDERS.map((provider) => {
              const capability = health.capabilities[provider.key];
              const copy = STATE_COPY[capability.state];
              return (
                <article className="integration-card" key={provider.key}>
                  <div className="integration-card-heading">
                    <h3>{provider.name}</h3>
                    <span
                      className={`connection-state connection-${capability.state}`}
                    >
                      {copy.label}
                    </span>
                  </div>
                  <p>{provider.purpose}</p>
                  <small>{copy.detail}</small>
                </article>
              );
            })}
          </div>
          <p className="database-status">
            Database:{" "}
            <strong>
              {health.database.persistent
                ? "Persistent Supabase"
                : "Temporary preview storage"}
            </strong>
            {health.database.connected ? " · Connected" : " · Unavailable"}
          </p>
        </>
      ) : null}
    </section>
  );
}
