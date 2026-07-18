"use client";

import { useCallback, useState } from "react";
import type { SelectionItem, SelectionPayload } from "@/lib/editor/types";

const MAX_HISTORY = 80;

type HistoryState = {
  past: SelectionPayload[];
  present: SelectionPayload;
  future: SelectionPayload[];
};

export function useSelectionHistory(initial: SelectionPayload) {
  const [state, setState] = useState<HistoryState>({
    past: [],
    present: initial,
    future: [],
  });

  const commit = useCallback((next: SelectionPayload) => {
    setState((prev) => ({
      past: [...prev.past.slice(-(MAX_HISTORY - 1)), prev.present],
      present: next,
      future: [],
    }));
  }, []);

  const replace = useCallback((next: SelectionPayload) => {
    setState({ past: [], present: next, future: [] });
  }, []);

  const setItems = useCallback(
    (items: SelectionItem[]) => {
      commit({ ...state.present, items });
    },
    [commit, state.present],
  );

  const addItem = useCallback(
    (item: SelectionItem) => {
      commit({ ...state.present, items: [...state.present.items, item] });
    },
    [commit, state.present],
  );

  const clear = useCallback(() => {
    if (state.present.items.length === 0) return;
    commit({ ...state.present, items: [] });
  }, [commit, state.present]);

  const undo = useCallback(() => {
    setState((prev) => {
      if (prev.past.length === 0) return prev;
      const previous = prev.past[prev.past.length - 1];
      return {
        past: prev.past.slice(0, -1),
        present: previous,
        future: [...prev.future, prev.present],
      };
    });
  }, []);

  const redo = useCallback(() => {
    setState((prev) => {
      if (prev.future.length === 0) return prev;
      const next = prev.future[prev.future.length - 1];
      return {
        past: [...prev.past, prev.present],
        present: next,
        future: prev.future.slice(0, -1),
      };
    });
  }, []);

  return {
    payload: state.present,
    setItems,
    addItem,
    clear,
    undo,
    redo,
    replace,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
  };
}
