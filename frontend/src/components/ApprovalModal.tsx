/**
 * Human-in-the-loop gate after the stream finishes.
 * Approve calls POST /api/agent/approve to open a GitHub PR.
 */

import { useEffect, useState } from "react";

type Props = {
  open: boolean;
  findings: string[];
  testErrors: string[];
  iteration: number;
  defaultOwner: string;
  defaultRepo: string;
  defaultFilePath: string;
  approving: boolean;
  onApprove: (input: {
    owner: string;
    repo: string;
    base_branch: string;
    file_path: string;
    title: string;
  }) => void;
  onReject: () => void;
};

export function ApprovalModal({
  open,
  findings,
  testErrors,
  iteration,
  defaultOwner,
  defaultRepo,
  defaultFilePath,
  approving,
  onApprove,
  onReject,
}: Props) {
  const [owner, setOwner] = useState(defaultOwner);
  const [repo, setRepo] = useState(defaultRepo);
  const [baseBranch, setBaseBranch] = useState("main");
  const [filePath, setFilePath] = useState(defaultFilePath);
  const [title, setTitle] = useState("Agentic PR Review Studio: security fix");

  useEffect(() => {
    if (!open) return;
    setOwner(defaultOwner);
    setRepo(defaultRepo);
    setFilePath(defaultFilePath);
  }, [open, defaultOwner, defaultRepo, defaultFilePath]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-zinc-700 bg-zinc-900 p-6 shadow-xl">
        <h2 className="text-lg font-medium">Approve and open pull request</h2>
        <p className="mt-2 text-sm text-zinc-400">
          Iteration {iteration}. Confirm the GitHub target, then Approve to
          create a branch and PR with the rewritten code.
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

        <div className="mt-4 grid gap-3">
          <label className="grid gap-1 text-sm">
            <span className="text-zinc-400">GitHub owner</span>
            <input
              className="rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-zinc-500"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="vinayrawat058"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="text-zinc-400">Repository</span>
            <input
              className="rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-zinc-500"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="autonomous-code-review"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="text-zinc-400">Base branch</span>
            <input
              className="rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-zinc-500"
              value={baseBranch}
              onChange={(e) => setBaseBranch(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="text-zinc-400">File path to write</span>
            <input
              className="rounded border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-sm outline-none focus:border-zinc-500"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="text-zinc-400">PR title</span>
            <input
              className="rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-zinc-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            disabled={approving || !owner.trim() || !repo.trim() || !filePath.trim()}
            onClick={() =>
              onApprove({
                owner: owner.trim(),
                repo: repo.trim(),
                base_branch: baseBranch.trim() || "main",
                file_path: filePath.trim(),
                title: title.trim() || "Agentic PR Review Studio: security fix",
              })
            }
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-700"
          >
            {approving ? "Opening PR…" : "Approve & open PR"}
          </button>
          <button
            type="button"
            disabled={approving}
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
