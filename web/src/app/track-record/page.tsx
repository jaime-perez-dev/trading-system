"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, TrendingUp, TrendingDown, CheckCircle, Clock, ExternalLink } from "lucide-react";

interface AnalysisRecord {
  id: number;
  type: string;
  market_slug: string;
  question: string;
  outcome: string;
  entry_price: number;
  exit_price: number | null;
  amount: number;
  shares: number;
  pnl: number | null;
  status: string;
  timestamp: string;
  reason: string;
}

interface Stats {
  totalTrades: number;
  closedTrades: number;
  openTrades: number;
  totalPnL: number;
  winRate: number;
  avgReturn: number;
  wins: number;
  losses: number;
}

export default function TrackRecordPage() {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/track-record")
      .then((res) => res.json())
      .then((data) => {
        setRecords(data.trades || []);
        setStats(data.stats || null);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading analysis history...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition">
            <ArrowLeft size={20} />
            <span>Back to EdgeSignals</span>
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            📊 Analysis History
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Our sentiment analysis performance. Every analysis is logged with timestamps and outcomes.
            Transparent tracking of our research accuracy.
          </p>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            <StatCard
              label="Sentiment Change"
              value={`${stats.totalPnL >= 0 ? '+' : ''}${stats.totalPnL.toFixed(1)}%`}
              positive={stats.totalPnL >= 0}
            />
            <StatCard
              label="Accuracy Rate"
              value={`${stats.winRate.toFixed(1)}%`}
              positive={stats.winRate >= 50}
            />
            <StatCard
              label="Resolved Analyses"
              value={`${stats.wins} / ${stats.wins + stats.losses}`}
              neutral
            />
            <StatCard
              label="Active Analyses"
              value={stats.openTrades.toString()}
              neutral
            />
          </div>
        )}

        {/* Verification Notice */}
        <div className="bg-emerald-900/30 border border-emerald-700/50 rounded-lg p-4 mb-8">
          <div className="flex items-start gap-3">
            <CheckCircle className="text-emerald-400 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-emerald-300">Verified Analysis</h3>
              <p className="text-sm text-emerald-200/70 mt-1">
                All analyses are logged in real-time with immutable timestamps. 
                Market sentiment data is fetched from public APIs at time of analysis.
                <a 
                  href="https://polymarket.com" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:underline ml-1 inline-flex items-center gap-1"
                >
                  View markets <ExternalLink size={12} />
                </a>
              </p>
            </div>
          </div>
        </div>

        {/* Analysis History */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Clock size={20} className="text-gray-400" />
            Analysis History
          </h2>

          {records.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No analyses recorded yet. Check back soon!
            </div>
          ) : (
            <div className="space-y-3">
              {records.map((record) => (
                <AnalysisCard key={record.id} record={record} />
              ))}
            </div>
          )}
        </div>

        {/* Disclaimer */}
        <div className="mt-16 text-center text-xs text-gray-600 max-w-2xl mx-auto">
          <p>
            <strong>Disclaimer:</strong> This is historical analysis data for informational and research purposes only. 
            Past sentiment analysis does not predict future outcomes. 
            This is not financial advice. Always conduct your own research before making any decisions.
          </p>
        </div>
      </main>
    </div>
  );
}

function StatCard({ 
  label, 
  value, 
  positive, 
  neutral 
}: { 
  label: string; 
  value: string; 
  positive?: boolean;
  neutral?: boolean;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${
        neutral ? 'text-white' : positive ? 'text-emerald-400' : 'text-red-400'
      }`}>
        {value}
      </div>
    </div>
  );
}

function AnalysisCard({ record }: { record: AnalysisRecord }) {
  const isActive = record.status === "OPEN";
  const wasAccurate = (record.pnl ?? 0) >= 0;
  
  const formatDate = (iso: string) => {
    const date = new Date(iso);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Analysis Info */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded ${
              isActive 
                ? 'bg-blue-900/50 text-blue-300' 
                : wasAccurate 
                  ? 'bg-emerald-900/50 text-emerald-300'
                  : 'bg-red-900/50 text-red-300'
            }`}>
              {isActive ? 'ACTIVE' : wasAccurate ? 'ACCURATE' : 'INACCURATE'}
            </span>
            <span className="text-xs text-gray-500">#{record.id}</span>
          </div>
          
          <h3 className="font-medium text-white mb-1">
            {record.question}
          </h3>
          
          <p className="text-sm text-gray-400">
            {record.outcome} sentiment @ {record.entry_price.toFixed(1)}%
            {record.exit_price && (
              <span> → {record.exit_price.toFixed(1)}%</span>
            )}
          </p>
          
          <p className="text-xs text-gray-500 mt-2">
            {formatDate(record.timestamp)}
          </p>
        </div>

        {/* Sentiment Change */}
        <div className="text-right">
          <div className="text-sm text-gray-500">Tracked Value</div>
          <div className="font-medium">${record.amount.toFixed(0)}</div>
          
          {record.pnl !== null && (
            <>
              <div className="text-sm text-gray-500 mt-2">Change</div>
              <div className={`font-bold text-lg flex items-center justify-end gap-1 ${
                record.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {record.pnl >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                {record.pnl >= 0 ? '+' : ''}{record.pnl.toFixed(1)}%
              </div>
            </>
          )}
          
          {isActive && (
            <div className="text-sm text-gray-500 mt-2 italic">
              Analysis active
            </div>
          )}
        </div>
      </div>

      {/* Reason */}
      {record.reason && (
        <div className="mt-3 pt-3 border-t border-gray-800">
          <p className="text-sm text-gray-400 italic">
            "{record.reason}"
          </p>
        </div>
      )}
    </div>
  );
}
