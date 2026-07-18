"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  deleteMask,
  getMask,
  listMasks,
  saveMask,
  updateMask,
} from "@/lib/editor/masks";
import type { MaskSummary, SelectionPayload } from "@/lib/editor/types";
import { ApiError } from "@/lib/api";

type Props = {
  videoId: string;
  payload: SelectionPayload;
  activeMaskId: string | null;
  onLoaded: (maskId: string, payload: SelectionPayload, name: string) => void;
  onSaved: (maskId: string, name: string) => void;
};

export function MaskPanel({
  videoId,
  payload,
  activeMaskId,
  onLoaded,
  onSaved,
}: Props) {
  const [masks, setMasks] = useState<MaskSummary[]>([]);
  const [name, setName] = useState("Selection mask");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const data = await listMasks(videoId);
    setMasks(data.items);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listMasks(videoId);
        if (!cancelled) setMasks(data.items);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load masks");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [videoId]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      if (activeMaskId) {
        const updated = await updateMask(videoId, activeMaskId, {
          name,
          payload,
        });
        onSaved(updated.id, updated.name);
        setStatus("Mask updated");
      } else {
        const created = await saveMask(videoId, name, payload);
        onSaved(created.id, created.name);
        setStatus("Mask saved");
      }
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onLoad(maskId: string) {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const mask = await getMask(videoId, maskId);
      setName(mask.name);
      onLoaded(mask.id, mask.payload, mask.name);
      setStatus(`Loaded “${mask.name}”`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Load failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(maskId: string) {
    setBusy(true);
    setError(null);
    try {
      await deleteMask(videoId, maskId);
      await refresh();
      setStatus("Mask deleted");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-border bg-surface/90 p-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
          Selection masks
        </h2>
        <p className="mt-1 text-sm text-muted">
          Save and reload rectangle/brush selections. No AI removal in this phase.
        </p>
      </div>

      <form onSubmit={onSave} className="flex flex-col gap-3 sm:flex-row">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={160}
          className="h-11 flex-1 rounded-xl border border-border bg-surface-elevated px-3 text-sm outline-none ring-accent focus:ring-2"
          placeholder="Mask name"
        />
        <button
          type="submit"
          disabled={busy}
          className="h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-[#041614] disabled:opacity-50"
        >
          {activeMaskId ? "Update mask" : "Save mask"}
        </button>
        {activeMaskId ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              onSaved("", name);
              setStatus("Editing as new mask");
            }}
            className="h-11 rounded-xl border border-border px-4 text-sm"
          >
            Save as new
          </button>
        ) : null}
      </form>

      {error ? <p className="text-sm text-danger">{error}</p> : null}
      {status ? <p className="text-sm text-accent">{status}</p> : null}

      <ul className="space-y-2">
        {masks.length === 0 ? (
          <li className="text-sm text-muted">No saved masks yet.</li>
        ) : (
          masks.map((mask) => (
            <li
              key={mask.id}
              className={`flex flex-col gap-2 rounded-xl border px-3 py-3 sm:flex-row sm:items-center sm:justify-between ${
                activeMaskId === mask.id
                  ? "border-accent/50 bg-accent-soft"
                  : "border-border bg-surface-elevated/60"
              }`}
            >
              <div>
                <p className="text-sm font-semibold">{mask.name}</p>
                <p className="font-[family-name:var(--font-mono)] text-[11px] text-muted">
                  {mask.item_count} items ·{" "}
                  {new Date(mask.updated_at).toLocaleString()}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onLoad(mask.id)}
                  className="h-10 rounded-lg border border-border px-3 text-sm"
                >
                  Load
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onDelete(mask.id)}
                  className="h-10 rounded-lg border border-border px-3 text-sm text-danger"
                >
                  Delete
                </button>
              </div>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
