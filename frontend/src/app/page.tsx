import Link from "next/link";

export default function Home() {
  return (
    <div className="relative flex min-h-full flex-1 flex-col overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,rgba(61,214,198,0.16),transparent_50%),radial-gradient(ellipse_at_90%_20%,rgba(80,120,255,0.08),transparent_40%),linear-gradient(180deg,#07080b_0%,#0b0e14_55%,#07080b_100%)]"
      />
      <div
        aria-hidden
        className="animate-pulse-glow pointer-events-none absolute -top-24 left-1/2 h-64 w-[min(90vw,36rem)] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,var(--glow),transparent_70%)] blur-2xl"
      />

      <header className="relative z-10 flex items-center justify-between px-5 py-5 sm:px-8">
        <p className="font-[family-name:var(--font-display)] text-sm font-bold tracking-wide text-foreground">
          Private AI Video Cleaner
        </p>
        <span className="rounded-md border border-border bg-surface px-2.5 py-1 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.14em] text-muted">
          Phase 6–7
        </span>
      </header>

      <main className="relative z-10 mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-5 pb-16 pt-8 sm:px-8">
        <p className="animate-fade-up mb-4 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.2em] text-accent">
          Offline · Private · Owner-only
        </p>
        <h1 className="animate-fade-up font-[family-name:var(--font-display)] text-4xl font-extrabold leading-[1.05] tracking-tight text-foreground sm:text-6xl">
          Private AI Video Cleaner
        </h1>
        <p className="animate-fade-up-delay mt-5 max-w-xl text-base leading-relaxed text-muted sm:text-lg">
          Edit videos you own, locally. Mask objects, clean with classic or AI
          tools, export without uploading your media to the cloud.
        </p>

        <div className="animate-fade-up-delay mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
          <Link
            href="/login"
            className="inline-flex h-12 items-center justify-center rounded-lg bg-accent px-6 text-sm font-semibold text-[#041614] transition hover:brightness-110"
          >
            Sign in
          </Link>
          <Link
            href="/bootstrap"
            className="inline-flex h-12 items-center justify-center rounded-lg border border-border px-6 text-sm text-foreground transition hover:bg-surface"
          >
            First-time setup
          </Link>
          <Link
            href="/upload"
            className="inline-flex h-12 items-center justify-center rounded-lg border border-border px-6 text-sm text-foreground transition hover:bg-surface"
          >
            Upload & edit
          </Link>
        </div>
      </main>

      <footer className="relative z-10 border-t border-border px-5 py-4 text-xs text-muted sm:px-8">
        Use only on media you own or have permission to edit. Built for local
        machines — see docs/FROM_MOBILE.md if you are coding from a phone.
      </footer>
    </div>
  );
}
