/**
 * Live node status: idle → running → passed / failed.
 */

import type { NodeName, NodeStatus } from "../api/types";

type Props = {
  nodes: NodeName[];
  nodeStatus: Record<NodeName, NodeStatus>;
};

const STATUS_CLASS: Record<NodeStatus, string> = {
  idle: "text-zinc-500",
  running: "text-amber-400",
  passed: "text-emerald-400",
  failed: "text-rose-400",
};

export function GraphSidebar({ nodes, nodeStatus }: Props) {
  return (
    <aside className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <h2 className="text-sm font-medium text-zinc-200">Agent graph</h2>
      <ul className="mt-3 space-y-2">
        {nodes.map((name) => {
          const status = nodeStatus[name];
          return (
            <li
              key={name}
              className="flex items-center justify-between rounded border border-zinc-800 px-3 py-2 text-sm"
            >
              <span className="font-mono text-zinc-300">{name}</span>
              <span
                className={`text-xs uppercase tracking-wide ${STATUS_CLASS[status]}`}
              >
                {status}
              </span>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
