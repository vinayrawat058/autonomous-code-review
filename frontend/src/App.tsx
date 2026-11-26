/**
 * Studio shell: form → live graph → Monaco diff → approval → GitHub PR.
 */

import { useState } from "react";
import { approveReview } from "./api/approve";
import { ApprovalModal } from "./components/ApprovalModal";
import { DiffViewer } from "./components/DiffViewer";
import { GraphSidebar } from "./components/GraphSidebar";
import { ReviewForm } from "./components/ReviewForm";
import { TokenStream } from "./components/TokenStream";
import { useAgentStream } from "./hooks/useAgentStream";

export default function App() {
  const {
    nodes,
    nodeStatus,
    findings,
    refactoredCode,
    testErrors,
    iteration,
    running,
    done,
    error,
    tokenNode,
    liveTokens,
    reset,
    startReview,
    markCreatePr,
  } = useAgentStream();

  const [originalDiff, setOriginalDiff] = useState("");
  const [threadId, setThreadId] = useState("");
  const [suggestedFilePath, setSuggestedFilePath] = useState("app.py");
  const [decision, setDecision] = useState<string | null>(null);
  const [prUrl, setPrUrl] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [approving, setApproving] = useState(false);

  async function handleSubmit(input: {
    diff_text: string;
    repo_path: string;
    test_code: string;
  }) {
    setDecision(null);
    setPrUrl(null);
    setModalOpen(false);
    setOriginalDiff(input.diff_text);
    const id = crypto.randomUUID();
    setThreadId(id);
    const result = await startReview({
      thread_id: id,
      diff_text: input.diff_text,
      repo_path: input.repo_path || null,
      test_code: input.test_code || null,
    });
    if (result?.suggested_file_path) {
      setSuggestedFilePath(result.suggested_file_path);
    }
    setModalOpen(true);
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-6 py-4">
        <h1 className="text-xl font-semibold tracking-tight">
          Agentic PR Review Studio
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Paste a change, watch the agent steps stream live, then approve a
          GitHub pull request.
        </p>
      </header>

      <main className="grid gap-4 p-6 lg:grid-cols-[280px_1fr]">
        <div className="grid gap-4 self-start">
          <GraphSidebar nodes={nodes} nodeStatus={nodeStatus} />
          <TokenStream node={tokenNode} text={liveTokens} running={running} />
        </div>
        <div className="grid gap-4">
          <ReviewForm running={running} onSubmit={handleSubmit} />
          {error && (
            <p className="rounded border border-rose-900 bg-rose-950/40 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
          )}
          {decision && (
            <p className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-300">
              {decision}
              {prUrl && (
                <>
                  {" "}
                  <a
                    className="text-emerald-400 underline"
                    href={prUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open PR
                  </a>
                </>
              )}
            </p>
          )}
          <DiffViewer original={originalDiff} modified={refactoredCode} />
        </div>
      </main>

      <ApprovalModal
        open={modalOpen && done && !running}
        findings={findings}
        testErrors={testErrors}
        iteration={iteration}
        defaultOwner="vinayrawat058"
        defaultRepo="autonomous-code-review"
        defaultFilePath={suggestedFilePath}
        approving={approving}
        onApprove={async (input) => {
          if (!threadId) return;
          setApproving(true);
          markCreatePr("running");
          try {
            const result = await approveReview({
              thread_id: threadId,
              owner: input.owner,
              repo: input.repo,
              base_branch: input.base_branch,
              file_path: input.file_path,
              title: input.title,
            });
            markCreatePr("passed");
            setPrUrl(result.pr_url);
            setDecision(
              result.dry_run
                ? `${result.message} Compare URL ready.`
                : result.message,
            );
            setModalOpen(false);
          } catch (err) {
            markCreatePr("failed");
            setDecision(
              err instanceof Error ? err.message : "Failed to open pull request.",
            );
          } finally {
            setApproving(false);
          }
        }}
        onReject={() => {
          setDecision("Rejected — rewrite discarded from this session.");
          setPrUrl(null);
          setModalOpen(false);
          reset();
          setOriginalDiff("");
          setThreadId("");
        }}
      />
    </div>
  );
}
