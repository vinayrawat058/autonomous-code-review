/**
 * Studio shell.
 *
 * Later layout:
 *   [ ReviewForm ]  [ DiffViewer ]
 *   [ GraphSidebar ] [ ApprovalModal when done ]
 */
import { ApprovalModal } from "./components/ApprovalModal";
import { DiffViewer } from "./components/DiffViewer";
import { GraphSidebar } from "./components/GraphSidebar";
import { ReviewForm } from "./components/ReviewForm";

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-6 py-4">
        <h1 className="text-xl font-semibold tracking-tight">
          Agentic PR Review Studio
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Structure only — wire the SSE stream and Monaco next.
        </p>
      </header>

      <main className="grid gap-4 p-6 lg:grid-cols-[280px_1fr]">
        <GraphSidebar />
        <div className="grid gap-4">
          <ReviewForm />
          <DiffViewer />
        </div>
      </main>

      <ApprovalModal open={false} />
    </div>
  );
}
