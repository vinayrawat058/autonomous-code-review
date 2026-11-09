/**
 * Live node status strip: Idle → Running → Passed / Failed.
 * Fed by SSE node events from useAgentStream.
 */

const PLACEHOLDER_NODES = [
  "ingest",
  "retrieve",
  "security",
  "refactor",
  "sandbox",
] as const;

export function GraphSidebar() {
  return (
    <aside className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <h2 className="text-sm font-medium text-zinc-200">Agent graph</h2>
      <ul className="mt-3 space-y-2">
        {PLACEHOLDER_NODES.map((name) => (
          <li
            key={name}
            className="flex items-center justify-between rounded border border-zinc-800 px-3 py-2 text-sm"
          >
            <span className="font-mono text-zinc-300">{name}</span>
            <span className="text-xs uppercase tracking-wide text-zinc-500">
              idle
            </span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
