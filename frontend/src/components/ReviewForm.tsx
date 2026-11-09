/**
 * Paste the diff / optional repo path / optional test code, then start a review.
 * Will call useAgentStream().startReview on submit.
 */

export function ReviewForm() {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <h2 className="text-sm font-medium text-zinc-200">Review input</h2>
      <p className="mt-1 text-sm text-zinc-500">
        Placeholder — textarea for the diff and a Start Review button come next.
      </p>
    </section>
  );
}
