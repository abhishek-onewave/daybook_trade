import Link from "next/link";

type PageScaffoldProps = {
  eyebrow: string;
  title: string;
  description: string;
  children?: React.ReactNode;
  showClosingBand?: boolean;
};

export function PageScaffold({
  eyebrow,
  title,
  description,
  children,
  showClosingBand = true,
}: PageScaffoldProps) {
  return (
    <>
      <section className="page-hero">
        <div className="page-shell">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="hero-description">{description}</p>
        </div>
      </section>
      <section className="page-content">
        <div className="page-shell">
          {children ?? (
            <div className="placeholder-card">
              <p className="placeholder-label">Phase 0 shell</p>
              <h2>The foundation is ready.</h2>
              <p>
                Live data and interaction arrive in their gated build phases. This
                route already shares Daybook&apos;s navigation, design tokens, and
                advisory footer.
              </p>
            </div>
          )}
        </div>
      </section>
      {showClosingBand ? (
        <section className="closing-band">
          <div className="page-shell closing-band-inner">
            <p>Ask Daybook why your stocks are moving.</p>
            <Link className="button button-light" href="/ask">
              Open Ask
            </Link>
          </div>
        </section>
      ) : null}
    </>
  );
}

