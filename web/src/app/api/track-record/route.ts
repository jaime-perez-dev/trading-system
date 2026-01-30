import { NextResponse } from "next/server";
import { readFileSync, existsSync } from "fs";
import { join } from "path";

interface Trade {
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

export async function GET() {
  try {
    // Path to paper_trades.json (adjust based on deployment)
    const tradesPath = join(process.cwd(), "..", "data", "paper_trades.json");
    
    let trades: Trade[] = [];
    
    if (existsSync(tradesPath)) {
      const content = readFileSync(tradesPath, "utf-8");
      trades = JSON.parse(content);
    } else {
      // Fallback: try relative path from trading-system root
      const fallbackPath = join(process.cwd(), "data", "paper_trades.json");
      if (existsSync(fallbackPath)) {
        const content = readFileSync(fallbackPath, "utf-8");
        trades = JSON.parse(content);
      }
    }

    // Calculate stats
    const closedTrades = trades.filter((t) => t.status === "CLOSED");
    const openTrades = trades.filter((t) => t.status === "OPEN");
    
    const wins = closedTrades.filter((t) => (t.pnl ?? 0) > 0).length;
    const losses = closedTrades.filter((t) => (t.pnl ?? 0) <= 0).length;
    
    const totalPnL = closedTrades.reduce((sum, t) => sum + (t.pnl ?? 0), 0);
    const winRate = closedTrades.length > 0 ? (wins / closedTrades.length) * 100 : 0;
    const avgReturn = closedTrades.length > 0 
      ? totalPnL / closedTrades.reduce((sum, t) => sum + t.amount, 0) * 100
      : 0;

    const stats: Stats = {
      totalTrades: trades.length,
      closedTrades: closedTrades.length,
      openTrades: openTrades.length,
      totalPnL,
      winRate,
      avgReturn,
      wins,
      losses,
    };

    // Sort trades by timestamp (newest first)
    const sortedTrades = [...trades].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    return NextResponse.json({
      trades: sortedTrades,
      stats,
      lastUpdated: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error loading track record:", error);
    
    // Return empty state on error
    return NextResponse.json({
      trades: [],
      stats: {
        totalTrades: 0,
        closedTrades: 0,
        openTrades: 0,
        totalPnL: 0,
        winRate: 0,
        avgReturn: 0,
        wins: 0,
        losses: 0,
      },
      error: "Failed to load trades",
    });
  }
}
