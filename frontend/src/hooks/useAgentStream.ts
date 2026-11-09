/**
 * React hook that owns review UI state while SSE events arrive.
 *
 * Will track: node statuses, findings, original diff, refactored code.
 * Components call startReview(payload) — no fetch logic in the UI itself.
 */

import { useCallback, useState } from "react";
import type { NodeName, NodeStatus, PRPayload } from "../api/types";

const NODES: NodeName[] = [
  "ingest",
  "retrieve",
  "security",
  "refactor",
  "sandbox",
];

export function useAgentStream() {
  const [nodeStatus, setNodeStatus] = useState<Record<NodeName, NodeStatus>>(
    () => Object.fromEntries(NODES.map((n) => [n, "idle"])) as Record<
      NodeName,
      NodeStatus
    >,
  );
  const [findings, setFindings] = useState<string[]>([]);
  const [refactoredCode, setRefactoredCode] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setNodeStatus(
      Object.fromEntries(NODES.map((n) => [n, "idle"])) as Record<
        NodeName,
        NodeStatus
      >,
    );
    setFindings([]);
    setRefactoredCode("");
    setError(null);
  }, []);

  const startReview = useCallback(async (_payload: PRPayload) => {
    setRunning(true);
    setError("SSE hook not wired yet — structure only.");
    setRunning(false);
  }, []);

  return {
    nodes: NODES,
    nodeStatus,
    findings,
    refactoredCode,
    running,
    error,
    reset,
    startReview,
  };
}
