/**
 * Client for POST /api/agent/stream.
 *
 * Uses fetch() + ReadableStream (not EventSource) because the backend
 * expects a POST body with the diff. Handles node + live token events.
 */

import type {
  DoneEventData,
  InterruptEventData,
  LlmEndEventData,
  LlmStartEventData,
  NodeEventData,
  PRPayload,
  TokenEventData,
} from "./types";

const baseUrl = () => import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export type StreamHandlers = {
  onStarted?: (threadId: string) => void;
  onNode?: (data: NodeEventData) => void;
  onToken?: (data: TokenEventData) => void;
  onLlmStart?: (data: LlmStartEventData) => void;
  onLlmEnd?: (data: LlmEndEventData) => void;
  onInterrupt?: (data: InterruptEventData) => void;
  onDone?: (data: DoneEventData) => void;
  onError?: (message: string) => void;
};

function parseSseChunk(buffer: string, handlers: StreamHandlers): string {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";

  for (const block of parts) {
    if (!block.trim()) continue;
    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (!dataLines.length) continue;
    const raw = dataLines.join("\n");
    let payload: unknown;
    try {
      payload = JSON.parse(raw);
    } catch {
      handlers.onError?.(raw);
      continue;
    }

    if (eventName === "started" && payload && typeof payload === "object") {
      const threadId = (payload as { thread_id?: string }).thread_id ?? "";
      handlers.onStarted?.(threadId);
    } else if (eventName === "node") {
      handlers.onNode?.(payload as NodeEventData);
    } else if (eventName === "token") {
      handlers.onToken?.(payload as TokenEventData);
    } else if (eventName === "llm_start") {
      handlers.onLlmStart?.(payload as LlmStartEventData);
    } else if (eventName === "llm_end") {
      handlers.onLlmEnd?.(payload as LlmEndEventData);
    } else if (eventName === "interrupt") {
      handlers.onInterrupt?.(payload as InterruptEventData);
    } else if (eventName === "done") {
      handlers.onDone?.(payload as DoneEventData);
    } else if (eventName === "error") {
      const message =
        payload && typeof payload === "object" && "message" in payload
          ? String((payload as { message: unknown }).message)
          : "Stream error";
      handlers.onError?.(message);
    }
  }

  return rest;
}

export async function streamAgentReview(
  payload: PRPayload,
  handlers: StreamHandlers = {},
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${baseUrl()}/api/agent/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Stream failed (${response.status})`);
  }
  if (!response.body) {
    throw new Error("Browser did not provide a response body for SSE.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = parseSseChunk(buffer, handlers);
  }
  if (buffer.trim()) {
    parseSseChunk(`${buffer}\n\n`, handlers);
  }
}
