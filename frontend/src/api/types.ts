/**
 * Shapes shared with the FastAPI / SSE backend.
 * Keep these aligned with backend/app/models/schemas.py and stream events.
 */

export type NodeName =
  | "ingest"
  | "retrieve"
  | "security"
  | "refactor"
  | "sandbox";

export type NodeStatus = "idle" | "running" | "passed" | "failed";

export interface PRPayload {
  thread_id: string;
  diff_text: string;
  repo_path?: string | null;
  test_code?: string | null;
}

export interface NodeEventData {
  active_node: NodeName | string;
  update: Record<string, unknown>;
}

export interface DoneEventData {
  thread_id: string;
  findings: string[];
  refactored_code: string;
  test_errors: string[];
  iteration: number;
}
