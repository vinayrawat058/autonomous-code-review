/**
 * Shapes shared with the FastAPI / SSE backend.
 * Keep these aligned with backend/app/models/schemas.py and stream events.
 */

export type NodeName =
  | "ingest"
  | "retrieve"
  | "security"
  | "refactor"
  | "sandbox"
  | "create_pr";

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

export interface TokenEventData {
  node: string;
  token: string;
}

export interface LlmStartEventData {
  node: string;
}

export interface LlmEndEventData {
  node: string;
  text: string;
}

export interface DoneEventData {
  thread_id: string;
  findings: string[];
  refactored_code: string;
  test_errors: string[];
  iteration: number;
  suggested_file_path?: string;
  suggested_file_paths?: string[];
  awaiting_approval?: boolean;
  next_node?: string | null;
}

export interface InterruptEventData {
  thread_id: string;
  next_node: string;
  message?: string;
}
