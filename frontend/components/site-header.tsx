"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/news", label: "News" },
  { href: "/ask", label: "Ask" },
  { href: "/stats", label: "Stats" },
  { href: "/favorites", label: "Favorites" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/settings", label: "Settings" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="site-header">
      <Link className="brand" href="/dashboard" aria-label="Daybook dashboard">
        <span className="brand-mark" aria-hidden="true">
          D
        </span>
        <span>Daybook</span>
      </Link>
      <nav aria-label="Primary navigation">
        {navigation.map((item) => {
          const isCurrent =
            pathname === item.href ||
            (item.href === "/favorites" && pathname.startsWith("/stock/"));
          return (
            <Link
              className={isCurrent ? "nav-link nav-link-active" : "nav-link"}
              href={item.href}
              key={item.href}
              aria-current={isCurrent ? "page" : undefined}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}

