/**
 * Monaco Diff Editor: original pasted change vs refactored_code.
 */

import { DiffEditor } from "@monaco-editor/react";

type Props = {
  original: string;
  modified: string;
};

export function DiffViewer({ original, modified }: Props) {
  return (
    <section className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/60">
      <div className="border-b border-zinc-800 px-4 py-3">
        <h2 className="text-sm font-medium text-zinc-200">Diff viewer</h2>
        <p className="mt-1 text-xs text-zinc-500">
          Left: your change · Right: agent rewrite
        </p>
      </div>
      <div className="h-[420px]">
        <DiffEditor
          original={original || "// Paste a diff and start a review"}
          modified={modified || "// Refactored code appears here"}
          language="python"
          theme="vs-dark"
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            fontSize: 13,
            scrollBeyondLastLine: false,
          }}
        />
      </div>
    </section>
  );
}
