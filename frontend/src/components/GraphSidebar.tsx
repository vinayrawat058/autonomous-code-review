/**
 * Live node status: idle → running → passed / failed.
 * create_pr shows "waiting" while the graph is interrupted for approval.
 */

import type { NodeName, NodeStatus } from "../api/types";

type Props = {
  nodes: NodeName[];
  nodeStatus: Record<NodeName, NodeStatus>;
  awaitingApproval?: boolean;
};

const STATUS_CLASS: Record<NodeStatus, string> = {
  idle: "text-zinc-500",
  running: "text-amber-400",
  passed: "text-emerald-400",
  failed: "text-rose-400",
};

export function GraphSidebar({
  nodes,
  nodeStatus,
  awaitingApproval = false,
}: Props) {
  return (
    <aside className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <h2 className="text-sm font-medium text-zinc-200">Agent graph</h2>
      {awaitingApproval && (
        <p className="mt-2 rounded border border-amber-900/60 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200">
          Waiting for human approval before <span className="font-mono">create_pr</span>
        </p>
      )}
      <ul className="mt-3 space-y-2">
        {nodes.map((name) => {
          const status = nodeStatus[name];
          const label =
            name === "create_pr" && awaitingApproval && status === "idle"
              ? "waiting"
              : status;
          const color =
            label === "waiting"
              ? "text-amber-300"
              : STATUS_CLASS[status];
          return (
            <li
              key={name}
              className="flex items-center justify-between rounded border border-zinc-800 px-3 py-2 text-sm"
            >
              <span className="font-mono text-zinc-300">{name}</span>
              <span className={`text-xs uppercase tracking-wide ${color}`}>
                {label}
              </span>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
