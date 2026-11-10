/**
 * Human-in-the-loop gate after the stream finishes.
 * Approve endpoint is still a backend stub — UI records the choice locally.
 */

type Props = {
  open: boolean;
  findings: string[];
  testErrors: string[];
  iteration: number;
  onApprove: () => void;
  onReject: () => void;
};

export function ApprovalModal({
  open,
  findings,
  testErrors,
  iteration,
  onApprove,
  onReject,
}: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-lg border border-zinc-700 bg-zinc-900 p-6 shadow-xl">
        <h2 className="text-lg font-medium">Review finished</h2>
        <p className="mt-2 text-sm text-zinc-400">
          Iteration {iteration}. Approve to keep the rewrite, or reject and
          discard it. GitHub PR creation wires up later.
        </p>

        {findings.length > 0 && (
          <div className="mt-4">
            <h3 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Findings
            </h3>
            <ul className="mt-2 space-y-2 text-sm text-zinc-200">
              {findings.map((item) => (
                <li
                  key={item}
                  className="rounded border border-zinc-800 bg-zinc-950 px-3 py-2"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {testErrors.length > 0 && (
          <div className="mt-4">
            <h3 className="text-xs font-medium uppercase tracking-wide text-rose-400">
              Test errors
            </h3>
            <pre className="mt-2 max-h-40 overflow-auto rounded border border-zinc-800 bg-zinc-950 p-3 text-xs text-rose-200">
              {testErrors.join("\n")}
            </pre>
          </div>
        )}

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onApprove}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={onReject}
            className="rounded border border-zinc-600 px-4 py-2 text-sm text-zinc-200"
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}
