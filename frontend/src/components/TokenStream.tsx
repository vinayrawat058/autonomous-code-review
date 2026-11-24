/**
 * Live model output while security / refactor tokens arrive over SSE.
 */

type Props = {
  node: string | null;
  text: string;
  running: boolean;
};

export function TokenStream({ node, text, running }: Props) {
  const idle = !running && !text;
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-zinc-200">Live model tokens</h2>
        <span className="font-mono text-xs uppercase tracking-wide text-zinc-500">
          {node ? node : idle ? "idle" : "done"}
        </span>
      </div>
      <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded border border-zinc-800 bg-zinc-950/80 p-3 font-mono text-xs leading-relaxed text-zinc-300">
        {text ||
          (running
            ? "Waiting for the next Groq token…"
            : "Tokens from security and refactor will appear here as they stream.")}
        {running && node ? (
          <span className="ml-0.5 inline-block h-3 w-1.5 animate-pulse bg-amber-400 align-middle" />
        ) : null}
      </pre>
    </section>
  );
}
