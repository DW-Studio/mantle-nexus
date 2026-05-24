"use client";

import { useEffect, useState } from "react";

/* ── Types ─────────────────────────────────────────────── */

interface Insight {
  id: number;
  tx_hash: string;
  sender: string;
  receiver: string;
  amount_mnt: number;
  ai_assessment: string;
  timestamp: string;
}

/* ── Helpers ────────────────────────────────────────────── */

const truncateHash = (hash: string, prefix = 6, suffix = 4) =>
  `${hash.slice(0, prefix)}...${hash.slice(-suffix)}`;

const truncateAddress = (addr: string) =>
  `${addr.slice(0, 6)}...${addr.slice(-4)}`;

const formatMNT = (amount: number) => amount.toFixed(4);

/* ── Component ──────────────────────────────────────────── */

export default function Dashboard() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchInsights = async () => {
      try {
        const res = await fetch("/api/insights");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: Insight[] = await res.json();
        if (!cancelled) {
          setInsights(data);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to fetch");
          setLoading(false);
        }
      }
    };

    // Fetch immediately, then poll every 5 seconds
    fetchInsights();
    const interval = setInterval(fetchInsights, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  /* ── Render ──────────────────────────────────────────── */

  return (
    <div className="min-h-screen bg-black text-zinc-300 font-mono p-6">
      {/* Header */}
      <header className="max-w-4xl mx-auto mb-10 border-b border-green-400/30 pb-4">
        <h1 className="text-2xl tracking-widest text-green-400 font-bold">
          MANTLE-NEXUS // INTELLIGENCE FEED
        </h1>
        <p className="text-xs text-zinc-500 mt-1 tracking-widest">
          LIVE · MONITORING · SMART · MONEY
        </p>
      </header>

      {/* Body */}
      <main className="max-w-4xl mx-auto space-y-4">
        {/* Loading state */}
        {loading && (
          <div className="text-center py-20">
            <span className="text-green-400 animate-pulse text-sm tracking-widest">
              CONNECTING TO DATABASE...
            </span>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="text-center py-20">
            <p className="text-red-400 text-sm tracking-widest mb-2">
              ⚠ ERROR — {error.toUpperCase()}
            </p>
            <p className="text-zinc-600 text-xs">
              RETRYING EVERY 5 SECONDS...
            </p>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && insights.length === 0 && (
          <div className="text-center py-20">
            <p className="text-zinc-500 text-sm tracking-widest">
              NO INSIGHTS AVAILABLE
            </p>
            <p className="text-zinc-700 text-xs mt-2">
              WAITING FOR DATA FROM THE SNIPER...
            </p>
          </div>
        )}

        {/* Insight cards */}
        {!loading &&
          insights.map((insight) => (
            <div
              key={insight.id}
              className="bg-zinc-950 border border-zinc-800 border-l-2 border-l-green-400 rounded-sm p-4 hover:bg-zinc-900/80 transition-colors"
            >
              {/* Top row: tx hash + timestamp */}
              <div className="flex items-center justify-between text-xs mb-3">
                <span className="text-green-400 tracking-wider">
                  TX{" "}
                  <span className="text-cyan-400">
                    {truncateHash(insight.tx_hash)}
                  </span>
                </span>
                <span className="text-zinc-600">{insight.timestamp}</span>
              </div>

              {/* Details row */}
              <div className="grid grid-cols-3 gap-4 text-xs mb-3">
                <div>
                  <span className="text-zinc-500 block">SENDER</span>
                  <span className="text-cyan-400">
                    {truncateAddress(insight.sender)}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500 block">RECEIVER</span>
                  <span className="text-cyan-400">
                    {truncateAddress(insight.receiver)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-zinc-500 block">AMOUNT</span>
                  <span className="text-green-400 font-bold">
                    {formatMNT(insight.amount_mnt)} MNT
                  </span>
                </div>
              </div>

              {/* AI Assessment */}
              <div className="border-t border-zinc-800 pt-3">
                <span className="text-[10px] tracking-widest text-zinc-500 block mb-1">
                  AI ASSESSMENT
                </span>
                <p className="text-sm text-white leading-relaxed">
                  {insight.ai_assessment}
                </p>
              </div>
            </div>
          ))}

        {/* Live indicator */}
        {!loading && (
          <div className="text-center pt-6 pb-4">
            <span className="inline-flex items-center gap-2 text-[10px] tracking-widest text-zinc-600">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              LIVE — AUTO-REFRESHING EVERY 5S
            </span>
          </div>
        )}
      </main>
    </div>
  );
}
