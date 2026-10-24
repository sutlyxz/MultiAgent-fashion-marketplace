import type { PropsWithChildren } from "react";
import { Link } from "react-router-dom";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div aria-live="polite" className="py-16 text-center text-sm text-ink/60" role="status">
      <span className="mr-2 inline-block animate-pulse text-clay">●</span>{label}
    </div>
  );
}

export function ErrorMessage({ children }: PropsWithChildren) {
  return <p className="rounded bg-red-50 px-4 py-3 text-sm text-red-800 break-words" role="alert">{children}</p>;
}

export function EmptyState({
  title,
  detail,
  action = "Browse pieces",
  to = "/products",
}: {
  title: string;
  detail: string;
  action?: string;
  to?: string;
}) {
  return (
    <div className="py-16 px-5 sm:px-8 text-center">
      <p className="eyebrow">A fresh start</p>
      <h2 className="mt-3 font-display text-2xl sm:text-3xl text-ink tracking-tight">{title}</h2>
      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-ink/60">{detail}</p>
      <Link className="button-primary mt-7 inline-flex" to={to}>{action}</Link>
    </div>
  );
}
