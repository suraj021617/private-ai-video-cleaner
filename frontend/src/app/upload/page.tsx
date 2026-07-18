"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { VideoUploader } from "@/components/upload/VideoUploader";
import type { Video } from "@/lib/videos";

export default function UploadPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [lastUploaded, setLastUploaded] = useState<Video | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-muted">
        Loading session…
      </div>
    );
  }

  return (
    <div className="relative mx-auto flex min-h-dvh w-full max-w-3xl flex-col px-5 py-8 sm:px-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_30%_0%,rgba(61,214,198,0.12),transparent_45%)]"
      />
      <header className="relative z-10 mb-8 flex items-center justify-between gap-3">
        <div>
          <p className="font-[family-name:var(--font-display)] text-sm font-bold tracking-wide">
            Private AI Video Cleaner
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-extrabold tracking-tight">
            Upload
          </h1>
          <p className="mt-2 text-sm text-muted">
            Add a video you have permission to edit, then open the selector.
          </p>
        </div>
        <Link
          href="/library"
          className="h-10 rounded-xl border border-border px-3 text-sm leading-10"
        >
          Library
        </Link>
      </header>

      <div className="relative z-10 space-y-6">
        <VideoUploader
          onUploaded={(video) => {
            setLastUploaded(video);
          }}
        />

        {lastUploaded ? (
          <div className="animate-fade-up rounded-2xl border border-accent/30 bg-accent-soft p-5">
            <p className="font-semibold text-foreground">
              Uploaded {lastUploaded.original_filename}
            </p>
            <p className="mt-1 text-sm text-muted">
              Ready for region selection in the editor.
            </p>
            <button
              type="button"
              className="mt-4 h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-[#041614]"
              onClick={() => router.push(`/editor/${lastUploaded.id}`)}
            >
              Open editor
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
