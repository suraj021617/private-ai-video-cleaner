"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { EditorWorkspace } from "@/components/editor/EditorWorkspace";
import { ApiError } from "@/lib/api";
import { getVideo, type Video } from "@/lib/videos";

export function EditorPageClient() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;
  const { user, loading } = useAuth();
  const router = useRouter();
  const [video, setVideo] = useState<Video | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || !videoId) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getVideo(videoId);
        if (!cancelled) setVideo(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Video not found");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, videoId]);

  if (loading || !user) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-muted">
        Loading session…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 px-5 text-center">
        <p className="text-danger">{error}</p>
        <button
          type="button"
          className="h-11 rounded-xl border border-border px-4 text-sm"
          onClick={() => router.push("/library")}
        >
          Back to library
        </button>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-muted">
        Opening editor…
      </div>
    );
  }

  return <EditorWorkspace video={video} />;
}
