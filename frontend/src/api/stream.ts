/**
 * Low-level client for POST /api/agent/stream.
 *
 * fetch() + ReadableStream is used instead of EventSource because
 * the backend expects a POST body (diff, repo_path, test_code).
 * Logic lands in the next UI step — this file is a stub for now.
 */

import type { DoneEventData, NodeEventData, PRPayload } from "./types";

const baseUrl = () => import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export type StreamHandlers = {
  onStarted?: (threadId: string) => void;
  onNode?: (data: NodeEventData) => void;
  onDone?: (data: DoneEventData) => void;
  onError?: (message: string) => void;
};

export async function streamAgentReview(
  _payload: PRPayload,
  _handlers: StreamHandlers = {},
): Promise<void> {
  void baseUrl;
  throw new Error("streamAgentReview is not wired yet — next step.");
}
