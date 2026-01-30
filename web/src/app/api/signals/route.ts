import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const PAPER_TRADES_FILE = path.join(process.cwd(), "..", "data", "paper_trades.json");
const EDGE_EVENTS_FILE = path.join(process.cwd(), "..", "data", "edge_events.json");

interface Signal {
  id: string;
  date: string;
  headline: string;
  market: string;
  signal: string;
  confidence: string;
  priceAtSignal: string;
  currentPrice?: string;
  pnl?: string;
  status: "open" | "closed" | "pending";
}

interface PaperTrade {
  id: number;
  type: string; // BUY or SELL
  market_slug: string;
  question: string;
  outcome: string;
  entry_price: number; // already in percentage (e.g., 4.45 means 4.45%)
  amount: number;
  shares: number;
  reason: string;
  timestamp: string;
  status: string; // OPEN or CLOSED
  exit_price: number | null;
  pnl: number | null;
}

interface EdgeEvent {
  id: number;
  type: string;
  headline: string;
  source: string;
  market_slug: string;
  news_time: string;
  market_price_at_news: string;
  market_price_1h_later: string | null;
  market_price_24h_later: string | null;
  final_resolution: string | null;
  notes: string;
}

interface EdgeEventsFile {
  events: EdgeEvent[];
  stats: Record<string, unknown>;
}

async function readJsonFile<T>(filePath: string, defaultValue: T): Promise<T> {
  try {
    const data = await fs.readFile(filePath, "utf-8");
    return JSON.parse(data);
  } catch {
    return defaultValue;
  }
}

function formatSignalFromTrade(trade: PaperTrade): Signal {
  const entryPercent = trade.entry_price.toFixed(1);
  const currentPercent = trade.exit_price !== null
    ? trade.exit_price.toFixed(1) 
    : entryPercent;
  
  const pnl = trade.pnl !== null
    ? `${trade.pnl > 0 ? "+" : ""}$${trade.pnl.toFixed(2)}` 
    : undefined;

  return {
    id: `trade-${trade.id}`,
    date: new Date(trade.timestamp).toLocaleString("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).replace(",", ""),
    headline: trade.reason || `Signal detected for ${trade.question}`,
    market: trade.question,
    signal: `${trade.type.toUpperCase()} ${trade.outcome.toUpperCase()}`,
    confidence: "HIGH",
    priceAtSignal: `${entryPercent}%`,
    currentPrice: `${currentPercent}%`,
    pnl,
    status: trade.status.toLowerCase() as "open" | "closed",
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const tier = searchParams.get("tier") || "free";
  const limit = parseInt(searchParams.get("limit") || "10", 10);

  try {
    // Read paper trades
    const trades: PaperTrade[] = await readJsonFile(PAPER_TRADES_FILE, []);
    const edgeEventsFile: EdgeEventsFile = await readJsonFile(EDGE_EVENTS_FILE, { events: [], stats: {} });
    const edgeEvents = edgeEventsFile.events || [];

    // Convert trades to signals format
    let signals: Signal[] = trades.map(formatSignalFromTrade);

    // Add edge events that don't have associated trades
    edgeEvents.forEach((event) => {
      const hasAssociatedTrade = signals.some((s) => 
        s.headline.toLowerCase().includes(event.headline.toLowerCase().slice(0, 30)) ||
        s.market.toLowerCase().includes(event.market_slug.split("-").slice(0, 3).join(" "))
      );
      
      if (!hasAssociatedTrade) {
        signals.push({
          id: `edge-${event.id}`,
          date: new Date(event.news_time).toLocaleString("en-US", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          }).replace(",", ""),
          headline: event.headline,
          market: event.market_slug.replace(/-/g, " ").replace(/\d+/g, "").trim(),
          signal: "NEWS ALERT",
          confidence: "HIGH",
          priceAtSignal: event.market_price_at_news ? `${event.market_price_at_news}%` : "N/A",
          currentPrice: event.market_price_1h_later ? `${event.market_price_1h_later}%` : undefined,
          status: "pending",
        });
      }
    });

    // Sort by date descending
    signals.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    // For free tier, add 15-minute delay (hide recent signals)
    if (tier === "free") {
      const fifteenMinutesAgo = Date.now() - 15 * 60 * 1000;
      signals = signals.filter(
        (s) => new Date(s.date).getTime() < fifteenMinutesAgo
      );
    }

    // Apply limit
    signals = signals.slice(0, limit);

    return NextResponse.json({
      signals,
      meta: {
        tier,
        count: signals.length,
        delayed: tier === "free",
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    console.error("Signals API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch signals", signals: [] },
      { status: 500 }
    );
  }
}
