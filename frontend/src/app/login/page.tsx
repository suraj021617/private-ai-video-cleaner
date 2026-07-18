import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <div className="relative flex min-h-full flex-1 flex-col">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(61,214,198,0.12),transparent_45%)]"
      />
      <main className="relative z-10 mx-auto flex w-full max-w-lg flex-1 flex-col justify-center px-5 py-12">
        <p className="mb-3 font-[family-name:var(--font-display)] text-sm font-bold tracking-wide">
          Private AI Video Cleaner
        </p>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-extrabold tracking-tight sm:text-4xl">
          Sign in
        </h1>
        <p className="mt-3 mb-8 text-sm text-muted">
          Private access for the owner account only.
        </p>
        <LoginForm />
      </main>
    </div>
  );
}
