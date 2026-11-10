/**
 * Owns studio state while SSE events arrive from the backend.
 */

import { useCallback, useRef, useState } from "react";
import { streamAgentReview } from "../api/stream";
import type { NodeName, NodeStatus, PRPayload } from "../api/types";

const NODES: NodeName[] = [
  "ingest",
  "retrieve",
  "security",
  "refactor",
  "sandbox",
];

function idleMap(): Record<NodeName, NodeStatus> {
  return Object.fromEntries(NODES.map((n) => [n, "idle"])) as Record<
    NodeName,
    NodeStatus
  >;
}

function isNodeName(value: string): value is NodeName {
  return (NODES as string[]).includes(value);
}

export function useAgentStream() {
  const [nodeStatus, setNodeStatus] = useState<Record<NodeName, NodeStatus>>(idleMap);
  const [findings, setFindings] = useState<string[]>([]);
  const [refactoredCode, setRefactoredCode] = useState("");
  const [testErrors, setTestErrors] = useState<string[]>([]);
  const [iteration, setIteration] = useState(0);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setNodeStatus(idleMap());
    setFindings([]);
    setRefactoredCode("");
    setTestErrors([]);
    setIteration(0);
    setDone(false);
    setError(null);
    setRunning(false);
  }, []);

  const startReview = useCallback(async (payload: PRPayload) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setNodeStatus(idleMap());
    setFindings([]);
    setRefactoredCode("");
    setTestErrors([]);
    setIteration(0);
    setDone(false);
    setError(null);
    setRunning(true);

    try {
      await streamAgentReview(
        payload,
        {
          onNode: (data) => {
            const name = String(data.active_node);
            if (!isNodeName(name)) return;

            setNodeStatus((prev) => {
              const next = { ...prev };
              for (const node of NODES) {
                if (next[node] === "running") next[node] = "passed";
              }
              next[name] = "running";
              return next;
            });

            const update = data.update ?? {};
            if (Array.isArray(update.findings)) {
              setFindings(update.findings.map(String));
            }
            if (typeof update.refactored_code === "string") {
              setRefactoredCode(update.refactored_code);
            }
            if (Array.isArray(update.test_errors)) {
              const errors = update.test_errors.map(String);
              setTestErrors(errors);
              if (errors.length && name === "sandbox") {
                setNodeStatus((prev) => ({ ...prev, sandbox: "failed" }));
              }
            }
            if (typeof update.iteration === "number") {
              setIteration(update.iteration);
            }
          },
          onDone: (data) => {
            setFindings(data.findings ?? []);
            setRefactoredCode(data.refactored_code ?? "");
            setTestErrors(data.test_errors ?? []);
            setIteration(data.iteration ?? 0);
            setNodeStatus((prev) => {
              const next = { ...prev };
              for (const node of NODES) {
                if (next[node] === "running") next[node] = "passed";
                if (next[node] === "idle") next[node] = "passed";
              }
              if ((data.test_errors ?? []).length) next.sandbox = "failed";
              return next;
            });
            setDone(true);
          },
          onError: (message) => setError(message),
        },
        controller.signal,
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, []);

  return {
    nodes: NODES,
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
  };
}
