"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { ApiError } from "@/lib/api";

export function BootstrapForm() {
  const { bootstrap } = useAuth();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await bootstrap(email, password, displayName);
      router.replace("/library");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to create owner account.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-md space-y-5">
      <div>
        <label htmlFor="displayName" className="mb-2 block text-sm text-muted">
          Display name
        </label>
        <input
          id="displayName"
          required
          minLength={1}
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="h-12 w-full rounded-lg border border-border bg-surface px-4 text-foreground outline-none ring-accent focus:ring-2"
        />
      </div>
      <div>
        <label htmlFor="email" className="mb-2 block text-sm text-muted">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="h-12 w-full rounded-lg border border-border bg-surface px-4 text-foreground outline-none ring-accent focus:ring-2"
        />
      </div>
      <div>
        <label htmlFor="password" className="mb-2 block text-sm text-muted">
          Password (min 12 characters)
        </label>
        <input
          id="password"
          type="password"
          required
          minLength={12}
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="h-12 w-full rounded-lg border border-border bg-surface px-4 text-foreground outline-none ring-accent focus:ring-2"
        />
      </div>
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="inline-flex h-12 w-full items-center justify-center rounded-lg bg-accent px-6 text-sm font-semibold text-[#041614] transition hover:brightness-110 disabled:opacity-60"
      >
        {pending ? "Creating…" : "Create owner account"}
      </button>
    </form>
  );
}
