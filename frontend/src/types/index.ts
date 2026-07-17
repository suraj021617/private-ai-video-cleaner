/**
 * Shared frontend types. Expanded as API contracts stabilize (Phase 2+).
 */

export type AppPhase =
  | "scaffold"
  | "auth"
  | "upload"
  | "preview"
  | "edit"
  | "export";

export type ProcessingStrategy =
  | "blur"
  | "fill"
  | "classic_inpaint"
  | "ai_inpaint";
