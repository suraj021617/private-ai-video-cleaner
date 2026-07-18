"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { ApiError, apiRequest } from "@/lib/api";

type AppSettings = {
  lama_model_dir: string;
  lama_prefer_gpu: boolean;
  lama_cpu_threads: number;
  lama_padding: number;
  lama_blend_strength: number;
  lama_feather_radius: number;
  processing_temp_dir: string;
  storage_root: string;
};

export default function SettingsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<AppSettings | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lama, setLama] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const settings = await apiRequest<AppSettings>("/api/v1/settings", {
          method: "GET",
        });
        const lamaStatus = await apiRequest<Record<string, unknown>>(
          "/api/v1/settings/lama-status",
          { method: "GET" },
        );
        if (!cancelled) {
          setForm(settings);
          setLama(lamaStatus);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load settings");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!form) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const saved = await apiRequest<AppSettings>("/api/v1/settings", {
        method: "PUT",
        json: form,
      });
      setForm(saved);
      setStatus("Settings saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function ensureModel() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiRequest<Record<string, unknown>>(
        "/api/v1/settings/lama-ensure",
        { method: "POST" },
      );
      setLama(result);
      setStatus("LaMa model ready");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Model download failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading || !user) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-muted">
        Loading…
      </div>
    );
  }

  if (!form) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-muted">
        {error || "Loading settings…"}
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-2xl flex-col gap-6 px-5 py-8 sm:px-8">
      <header className="flex items-center justify-between gap-3">
        <div>
          <p className="font-[family-name:var(--font-display)] text-sm font-bold">
            Private AI Video Cleaner
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-extrabold">
            Settings
          </h1>
        </div>
        <div className="flex gap-2">
          <Link
            href="/diagnostics"
            className="h-10 rounded-xl border border-border px-3 text-sm leading-10"
          >
            Diagnostics
          </Link>
          <Link
            href="/library"
            className="h-10 rounded-xl border border-border px-3 text-sm leading-10"
          >
            Library
          </Link>
        </div>
      </header>

      <form onSubmit={onSave} className="space-y-4 rounded-2xl border border-border bg-surface/80 p-5">
        <label className="block text-sm">
          <span className="text-muted">AI model location</span>
          <input
            className="mt-2 h-11 w-full rounded-xl border border-border bg-surface-elevated px-3"
            value={form.lama_model_dir}
            onChange={(e) =>
              setForm({ ...form, lama_model_dir: e.target.value })
            }
          />
        </label>

        <label className="flex items-center justify-between gap-3 text-sm">
          <span className="text-muted">Enable GPU</span>
          <input
            type="checkbox"
            checked={form.lama_prefer_gpu}
            onChange={(e) =>
              setForm({ ...form, lama_prefer_gpu: e.target.checked })
            }
          />
        </label>

        <label className="block text-sm">
          <span className="text-muted">CPU threads (0 = default)</span>
          <input
            type="number"
            min={0}
            max={128}
            className="mt-2 h-11 w-full rounded-xl border border-border bg-surface-elevated px-3"
            value={form.lama_cpu_threads}
            onChange={(e) =>
              setForm({ ...form, lama_cpu_threads: Number(e.target.value) })
            }
          />
        </label>

        <label className="block text-sm">
          <span className="text-muted">Mask padding (px)</span>
          <input
            type="number"
            min={0}
            max={256}
            className="mt-2 h-11 w-full rounded-xl border border-border bg-surface-elevated px-3"
            value={form.lama_padding}
            onChange={(e) =>
              setForm({ ...form, lama_padding: Number(e.target.value) })
            }
          />
        </label>

        <label className="block text-sm">
          <span className="text-muted">Blend strength (0–1)</span>
          <input
            type="number"
            min={0}
            max={1}
            step={0.05}
            className="mt-2 h-11 w-full rounded-xl border border-border bg-surface-elevated px-3"
            value={form.lama_blend_strength}
            onChange={(e) =>
              setForm({ ...form, lama_blend_strength: Number(e.target.value) })
            }
          />
        </label>

        <label className="block text-sm">
          <span className="text-muted">Temp folder</span>
          <input
            className="mt-2 h-11 w-full rounded-xl border border-border bg-surface-elevated px-3"
            value={form.processing_temp_dir}
            onChange={(e) =>
              setForm({ ...form, processing_temp_dir: e.target.value })
            }
          />
        </label>

        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="submit"
            disabled={busy}
            className="h-11 flex-1 rounded-xl bg-accent text-sm font-semibold text-[#041614] disabled:opacity-50"
          >
            Save settings
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void ensureModel()}
            className="h-11 flex-1 rounded-xl border border-border text-sm disabled:opacity-50"
          >
            Download / load LaMa
          </button>
        </div>
      </form>

      {lama ? (
        <div className="rounded-2xl border border-border bg-surface/60 p-4 font-[family-name:var(--font-mono)] text-xs text-muted">
          <p>status: {String(lama.status)}</p>
          <p>device: {String(lama.device)}</p>
          <p>model_loaded: {String(lama.model_loaded)}</p>
          {lama.checkpoint ? <p>checkpoint: {String(lama.checkpoint)}</p> : null}
        </div>
      ) : null}

      {status ? <p className="text-sm text-accent">{status}</p> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}
    </div>
  );
}
