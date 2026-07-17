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
          Phase 1
        </span>
      </header>

      <main className="relative z-10 mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-5 pb-16 pt-8 sm:px-8">
        <p className="animate-fade-up mb-4 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.2em] text-accent">
          Private · Owner-only
        </p>
        <h1 className="animate-fade-up font-[family-name:var(--font-display)] text-4xl font-extrabold leading-[1.05] tracking-tight text-foreground sm:text-6xl">
          Private AI Video Cleaner
        </h1>
        <p className="animate-fade-up-delay mt-5 max-w-xl text-base leading-relaxed text-muted sm:text-lg">
          Edit videos you have permission to edit. Manual rectangle and brush
          selection today — architecture ready for AI-assisted inpainting,
          overlays, and clean MP4 export.
        </p>

        <div className="animate-fade-up-delay mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
          <a
            href="#roadmap"
            className="inline-flex h-12 items-center justify-center rounded-lg bg-accent px-6 text-sm font-semibold text-[#041614] transition hover:brightness-110"
          >
            View roadmap
          </a>
          <p className="text-sm text-muted sm:ml-2">
            Auth, upload, and editor arrive in later phases.
          </p>
        </div>

        <section
          id="roadmap"
          className="mt-16 border-t border-border pt-8"
          aria-labelledby="roadmap-heading"
        >
          <h2
            id="roadmap-heading"
            className="font-[family-name:var(--font-display)] text-xl font-bold text-foreground"
          >
            Build phases
          </h2>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Phase 1 configures the repository and apps. Later phases unlock
            features after approval.
          </p>
          <ol className="mt-6 space-y-3 font-[family-name:var(--font-mono)] text-sm text-muted">
            <li className="flex gap-3">
              <span className="text-accent">01</span>
              <span className="text-foreground">Repository &amp; configuration</span>
            </li>
            <li className="flex gap-3">
              <span className="text-accent/70">02</span>
              <span>API contract &amp; local DX</span>
            </li>
            <li className="flex gap-3">
              <span className="text-accent/70">03</span>
              <span>Secure authentication</span>
            </li>
            <li className="flex gap-3">
              <span className="text-accent/70">04–08</span>
              <span>Upload, preview, selection, export, overlays</span>
            </li>
            <li className="flex gap-3">
              <span className="text-accent/70">09–10</span>
              <span>AI inpainting hooks &amp; production hardening</span>
            </li>
          </ol>
        </section>
      </main>

      <footer className="relative z-10 border-t border-border px-5 py-4 text-xs text-muted sm:px-8">
        Use only on media you own or have permission to edit.
      </footer>
    </div>
  );
}
