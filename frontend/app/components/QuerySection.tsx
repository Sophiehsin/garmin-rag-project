"use client";

import { useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type QueryState = "idle" | "loading" | "done" | "error";

interface ChunkResult {
  content: string;
  metadata: Record<string, unknown>;
  score: number;
}

interface QueryResponse {
  query: string;
  answer: string | null;
  results: ChunkResult[];
}

// ---------------------------------------------------------------------------
// Loading status messages — cycle while waiting for the first token (Task 11)
// ---------------------------------------------------------------------------

const STATUS_MESSAGES = [
  "Analyzing your training intent...",
  "Ranking results across your history...",
  "Generating insight...",
];

// ---------------------------------------------------------------------------
// Skeleton components (Task 11)
// ---------------------------------------------------------------------------

function SkeletonAnswer() {
  return (
    <div className="space-y-3 mt-6" aria-hidden="true">
      <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
      <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
      <div className="h-4 bg-gray-200 rounded animate-pulse w-4/6" />
    </div>
  );
}

function SkeletonSources() {
  return (
    <div className="space-y-3 mt-4" aria-hidden="true">
      {[0, 1].map((i) => (
        <div key={i} className="p-4 border border-gray-100 rounded-lg bg-white">
          <div className="h-3 bg-gray-200 rounded animate-pulse w-1/3 mb-2" />
          <div className="h-3 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-3 bg-gray-200 rounded animate-pulse w-2/3 mt-1" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function QuerySection() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<QueryState>("idle");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [statusIdx, setStatusIdx] = useState(0);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Rotate status message every 1.5 s while loading
  useEffect(() => {
    if (state === "loading") {
      setStatusIdx(0);
      intervalRef.current = setInterval(() => {
        setStatusIdx((i) => (i + 1) % STATUS_MESSAGES.length);
      }, 1500);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [state]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setState("loading");
    setResponse(null);
    setErrorMsg("");

    try {
      const res = await fetch("/api/v1/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token") ?? ""}`,
        },
        body: JSON.stringify({ query: query.trim(), use_llm: true }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail?.detail ?? `HTTP ${res.status}`);
      }

      const data: QueryResponse = await res.json();
      setResponse(data);
      setState("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  }

  return (
    <section>
      {/* Query input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. How has my running improved this year?"
          disabled={state === "loading"}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={state === "loading" || !query.trim()}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          Ask
        </button>
      </form>

      {/* Loading state */}
      {state === "loading" && (
        <div className="mt-4">
          <p className="text-sm text-blue-600 font-medium transition-all duration-300">
            {STATUS_MESSAGES[statusIdx]}
          </p>
          <SkeletonAnswer />
          <SkeletonSources />
        </div>
      )}

      {/* Error state */}
      {state === "error" && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {errorMsg}
        </div>
      )}

      {/* Done state */}
      {state === "done" && response && (
        <div className="mt-6">
          {response.answer && (
            <div className="prose prose-sm max-w-none bg-white border border-gray-200 rounded-lg p-5">
              <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                {response.answer}
              </p>
            </div>
          )}

          {response.results.length > 0 && (
            <div className="mt-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Sources ({response.results.length})
              </h2>
              <div className="space-y-3">
                {response.results.map((r, i) => (
                  <SourceCard key={i} result={r} index={i + 1} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Source card
// ---------------------------------------------------------------------------

function SourceCard({ result, index }: { result: ChunkResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const date = result.metadata.date as string | undefined;
  const dtype = result.metadata.data_type as string | undefined;
  const sport = result.metadata.activity_type as string | undefined;
  const score = (result.score * 100).toFixed(0);

  const label = [dtype, sport].filter(Boolean).join(" / ");

  return (
    <div className="p-4 border border-gray-100 bg-white rounded-lg">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500">
          #{index} · {label || "record"}{date ? ` · ${date}` : ""}
        </span>
        <span className="text-xs text-gray-400">score {score}%</span>
      </div>
      <p className={`text-sm text-gray-700 ${expanded ? "" : "line-clamp-2"}`}>
        {result.content}
      </p>
      {result.content.length > 120 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-blue-500 mt-1 hover:underline"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}
