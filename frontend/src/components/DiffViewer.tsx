/**
 * Split-screen Monaco Diff Editor: original change vs refactored_code.
 * Package @monaco-editor/react is listed; wire DiffEditor in the next UI step.
 */

export function DiffViewer() {
  return (
    <section className="min-h-[320px] rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <h2 className="text-sm font-medium text-zinc-200">Diff viewer</h2>
      <p className="mt-1 text-sm text-zinc-500">
        Placeholder — Monaco original vs fixed code lands here.
      </p>
    </section>
  );
}
