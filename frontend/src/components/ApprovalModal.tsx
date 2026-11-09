/**
 * Human-in-the-loop gate before PR creation.
 * Opens when the stream finishes; Approve will call POST /api/agent/approve.
 */

type Props = {
  open: boolean;
};

export function ApprovalModal({ open }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 p-6">
        <h2 className="text-lg font-medium">Approve pull request?</h2>
        <p className="mt-2 text-sm text-zinc-400">
          Placeholder — Approve / Reject actions wire up after the stream works
          in the UI.
        </p>
      </div>
    </div>
  );
}
