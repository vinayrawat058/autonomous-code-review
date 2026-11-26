/**
 * POST /api/agent/approve — resume LangGraph create_pr after human approval.
 * POST /api/agent/reject  — cancel a paused graph thread.
 */

export type ApproveRequest = {
  thread_id: string;
  owner: string;
  repo: string;
  base_branch: string;
  file_path: string;
  title?: string;
  body?: string;
  force?: boolean;
};

export type ApproveResponse = {
  status: string;
  thread_id: string;
  pr_url: string;
  branch: string;
  number: number | null;
  dry_run: boolean;
  message: string;
  files_written?: string[];
};

export type RejectResponse = {
  status: string;
  thread_id: string;
  message: string;
};

const baseUrl = () => import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export async function approveReview(
  payload: ApproveRequest,
): Promise<ApproveResponse> {
  const response = await fetch(`${baseUrl()}/api/agent/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : `Approve failed (${response.status})`;
    throw new Error(detail);
  }
  return data as ApproveResponse;
}

export async function rejectReview(threadId: string): Promise<RejectResponse> {
  const response = await fetch(`${baseUrl()}/api/agent/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : `Reject failed (${response.status})`;
    throw new Error(detail);
  }
  return data as RejectResponse;
}
