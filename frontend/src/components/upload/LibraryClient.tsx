"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  deleteVideo,
  listVideos,
  videoContentUrl,
  type Video,
} from "@/lib/videos";
import { ApiError } from "@/lib/api";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

export function LibraryClient() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      setLoadingList(true);
      try {
        const data = await listVideos();
        if (!cancelled) setVideos(data.items);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Failed to load videos",
          );
        }
      } finally {
        if (!cancelled) setLoadingList(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (loading || !user) {
    return (
      <div className="flex min-h-full flex-1 items-center justify-center text-muted">
        Loading session…
      </div>
    );
  }

  return (
    <div className="relative mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-[family-name:var(--font-display)] text-sm font-bold tracking-wide">
            Private AI Video Cleaner
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-extrabold tracking-tight sm:text-4xl">
            Library
          </h1>
          <p className="mt-2 text-sm text-muted">
            Signed in as {user.display_name} ({user.email})
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/upload"
            className="inline-flex h-11 items-center rounded-lg bg-accent px-5 text-sm font-semibold text-[#041614]"
          >
            Upload
          </Link>
          <button
            type="button"
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
            className="h-11 rounded-lg border border-border px-5 text-sm text-foreground transition hover:bg-surface"
          >
            Sign out
          </button>
        </div>
      </header>

      <section>
        <h2 className="font-[family-name:var(--font-display)] text-xl font-bold">
          Your videos
        </h2>
        {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}
        {loadingList ? (
          <p className="mt-4 text-sm text-muted">Loading…</p>
        ) : videos.length === 0 ? (
          <p className="mt-4 text-sm text-muted">No videos uploaded yet.</p>
        ) : (
          <ul className="mt-5 space-y-4">
            {videos.map((video) => (
              <li
                key={video.id}
                className="rounded-xl border border-border bg-surface/60 p-4"
              >
                <div className="flex flex-col gap-4 lg:flex-row">
                  <video
                    className="aspect-video w-full rounded-lg bg-black object-contain lg:max-w-sm"
                    controls
                    preload="metadata"
                    src={videoContentUrl(video.id)}
                  />
                  <div className="flex flex-1 flex-col justify-between gap-3">
                    <div>
                      <p className="font-semibold text-foreground">
                        {video.original_filename}
                      </p>
                      <p className="mt-2 font-[family-name:var(--font-mono)] text-xs text-muted">
                        {video.metadata.width ?? "?"}×
                        {video.metadata.height ?? "?"} ·{" "}
                        {video.metadata.duration_seconds?.toFixed(1) ?? "?"}s ·{" "}
                        {formatBytes(video.size_bytes)} ·{" "}
                        {video.metadata.video_codec ?? "unknown codec"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link
                        href={`/editor/${video.id}`}
                        className="inline-flex h-10 items-center rounded-lg bg-accent px-4 text-sm font-semibold text-[#041614]"
                      >
                        Edit
                      </Link>
                      <button
                        type="button"
                        className="h-10 rounded-lg border border-border px-4 text-sm text-danger transition hover:bg-surface-elevated"
                        onClick={async () => {
                          await deleteVideo(video.id);
                          setVideos((current) =>
                            current.filter((item) => item.id !== video.id),
                          );
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
