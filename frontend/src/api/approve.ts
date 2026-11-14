/**
 * POST /api/agent/approve — open a GitHub PR after the human clicks Approve.
 */

export type ApproveRequest = {
  thread_id: string;
  owner: string;
  repo: string;
  base_branch: string;
  file_path: string;
  title?: string;
  body?: string;
};

export type ApproveResponse = {
  status: string;
  thread_id: string;
  pr_url: string;
  branch: string;
  number: number | null;
  dry_run: boolean;
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
