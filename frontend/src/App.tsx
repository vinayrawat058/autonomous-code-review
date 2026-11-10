/**
 * Studio shell: form → live graph → Monaco diff → approval modal.
 */

import { useState } from "react";
import { ApprovalModal } from "./components/ApprovalModal";
import { DiffViewer } from "./components/DiffViewer";
import { GraphSidebar } from "./components/GraphSidebar";
import { ReviewForm } from "./components/ReviewForm";
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
    reset,
    startReview,
  } = useAgentStream();

  const [originalDiff, setOriginalDiff] = useState("");
  const [decision, setDecision] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  async function handleSubmit(input: {
    diff_text: string;
    repo_path: string;
    test_code: string;
  }) {
    setDecision(null);
    setModalOpen(false);
    setOriginalDiff(input.diff_text);
    await startReview({
      thread_id: crypto.randomUUID(),
      diff_text: input.diff_text,
      repo_path: input.repo_path || null,
      test_code: input.test_code || null,
    });
    setModalOpen(true);
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-6 py-4">
        <h1 className="text-xl font-semibold tracking-tight">
          Agentic PR Review Studio
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Paste a change, watch the agent steps stream live, then approve the
          rewrite.
        </p>
      </header>

      <main className="grid gap-4 p-6 lg:grid-cols-[280px_1fr]">
        <GraphSidebar nodes={nodes} nodeStatus={nodeStatus} />
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
        onApprove={() => {
          setDecision("Approved — PR creation will hook up in a later step.");
          setModalOpen(false);
        }}
        onReject={() => {
          setDecision("Rejected — rewrite discarded from this session.");
          setModalOpen(false);
          reset();
          setOriginalDiff("");
        }}
      />
    </div>
  );
}
