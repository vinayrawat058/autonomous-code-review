/**
 * Owns studio state while SSE events arrive from the backend.
 * Applies node updates and live LLM token chunks as they stream.
 */

import { useCallback, useRef, useState } from "react";
import { streamAgentReview } from "../api/stream";
import type { DoneEventData, NodeName, NodeStatus, PRPayload } from "../api/types";

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
  const [tokenNode, setTokenNode] = useState<string | null>(null);
  const [liveTokens, setLiveTokens] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const markRunning = useCallback((name: string) => {
    if (!isNodeName(name)) return;
    setNodeStatus((prev) => {
      const next = { ...prev };
      for (const node of NODES) {
        if (next[node] === "running") next[node] = "passed";
      }
      next[name] = "running";
      return next;
    });
  }, []);

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
    setTokenNode(null);
    setLiveTokens("");
  }, []);

  const startReview = useCallback(
    async (payload: PRPayload): Promise<DoneEventData | null> => {
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
      setTokenNode(null);
      setLiveTokens("");

      const doneRef: { current: DoneEventData | null } = { current: null };
      let securityDraft = "";
      let refactorDraft = "";

      try {
        await streamAgentReview(
          payload,
          {
            onLlmStart: (data) => {
              setTokenNode(data.node);
              setLiveTokens("");
              markRunning(data.node);
              if (data.node === "security") securityDraft = "";
              if (data.node === "refactor") refactorDraft = "";
            },
            onToken: (data) => {
              setTokenNode(data.node);
              setLiveTokens((prev) => prev + data.token);
              markRunning(data.node);
              if (data.node === "security") {
                securityDraft += data.token;
                const lines = securityDraft
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean)
                  .filter((line) => line.toUpperCase() !== "NONE");
                if (lines.length) setFindings(lines);
              }
              if (data.node === "refactor") {
                refactorDraft += data.token;
                setRefactoredCode(refactorDraft);
              }
            },
            onLlmEnd: (data) => {
              setTokenNode(data.node);
              setLiveTokens(data.text || "");
              if (data.node === "security" && data.text) {
                const lines = data.text
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean)
                  .filter((line) => line.toUpperCase() !== "NONE");
                setFindings(
                  lines.length
                    ? lines
                    : ["No rule from the rulebook matched this change."],
                );
              }
              if (data.node === "refactor" && data.text) {
                setRefactoredCode(data.text);
              }
            },
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
              doneRef.current = data;
              setFindings(data.findings ?? []);
              setRefactoredCode(data.refactored_code ?? "");
              setTestErrors(data.test_errors ?? []);
              setIteration(data.iteration ?? 0);
              setTokenNode(null);
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
        return doneRef.current;
      } catch (err) {
        if ((err as Error).name === "AbortError") return null;
        setError(err instanceof Error ? err.message : String(err));
        return null;
      } finally {
        setRunning(false);
        abortRef.current = null;
      }
    },
    [markRunning],
  );

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
    tokenNode,
    liveTokens,
    reset,
    startReview,
  };
}
