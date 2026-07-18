"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";

export function useVideoPlayer(videoRef: RefObject<HTMLVideoElement | null>) {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [ready, setReady] = useState(false);
  const rafRef = useRef<number | null>(null);
  const videoRefStable = videoRef;

  useEffect(() => {
    const video = videoRefStable.current;
    if (!video) return;

    const tick = () => {
      const el = videoRefStable.current;
      if (!el) return;
      setCurrentTime(el.currentTime);
      if (!el.paused && !el.ended) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    const onLoaded = () => {
      setDuration(video.duration || 0);
      setReady(true);
      setCurrentTime(video.currentTime);
    };
    const onPlay = () => {
      setPlaying(true);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(tick);
    };
    const onPause = () => {
      setPlaying(false);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      setCurrentTime(video.currentTime);
    };
    const onTimeUpdate = () => setCurrentTime(video.currentTime);
    const onEnded = () => setPlaying(false);

    video.addEventListener("loadedmetadata", onLoaded);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("ended", onEnded);

    if (video.readyState >= 1) onLoaded();

    return () => {
      video.removeEventListener("loadedmetadata", onLoaded);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("ended", onEnded);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [videoRefStable]);

  const play = useCallback(async () => {
    await videoRef.current?.play();
  }, [videoRef]);

  const pause = useCallback(() => {
    videoRef.current?.pause();
  }, [videoRef]);

  const toggle = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) await video.play();
    else video.pause();
  }, [videoRef]);

  const seek = useCallback(
    (time: number) => {
      const video = videoRef.current;
      if (!video || !Number.isFinite(time)) return;
      const next = Math.min(Math.max(time, 0), video.duration || duration || 0);
      video.currentTime = next;
      setCurrentTime(next);
    },
    [videoRef, duration],
  );

  const stepFrames = useCallback(
    (frames: number, fps: number) => {
      const rate = fps > 0 ? fps : 30;
      const video = videoRef.current;
      if (!video) return;
      const next = Math.min(
        Math.max(video.currentTime + frames / rate, 0),
        video.duration || duration || 0,
      );
      video.currentTime = next;
      setCurrentTime(next);
    },
    [videoRef, duration],
  );

  return {
    currentTime,
    duration,
    playing,
    ready,
    play,
    pause,
    toggle,
    seek,
    stepFrames,
  };
}
