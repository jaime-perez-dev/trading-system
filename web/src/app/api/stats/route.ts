import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";
import { prisma } from "@/lib/db";

const PAPER_TRADES_FILE = path.join(process.cwd(), "..", "data", "paper_trades.json");
const SERVER_START_TIME = Date.now();

interface PaperTrade {
  id: number;
  status: string;
  pnl: number | null;
  timestamp: string;
}

interface TradesFile {
  trades: PaperTrade[];
}

async function readTradesFile(): Promise<PaperTrade[]> {
  try {
    const data = await fs.readFile(PAPER_TRADES_FILE, "utf-8");
    const parsed: TradesFile = JSON.parse(data);
    return parsed.trades || [];
  } catch {
    return [];
  }
}

function calculateStats(trades: PaperTrade[]) {
  const closedTrades = trades.filter(t => t.status === "CLOSED");
  const winningTrades = closedTrades.filter(t => t.pnl !== null && t.pnl > 0);
  const totalPnL = closedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);

  return {
    totalSignals: trades.length,
    openPositions: trades.filter(t => t.status === "OPEN").length,
    closedTrades: closedTrades.length,
    winRate: closedTrades.length > 0 
      ? Math.round((winningTrades.length / closedTrades.length) * 100) 
      : null,
    totalPnL: Math.round(totalPnL * 100) / 100,
    avgPnL: closedTrades.length > 0 
      ? Math.round((totalPnL / closedTrades.length) * 100) / 100 
      : null,
  };
}

export async function GET() {
  try {
    // Get trading stats from JSON file
    const trades = await readTradesFile();
    const tradingStats = calculateStats(trades);

    // Get user/waitlist counts from database
    let waitlistCount = 0;
    let userCount = 0;
    try {
      waitlistCount = await prisma.waitlist.count();
      userCount = await prisma.user.count();
    } catch {
      // Database might not be configured in dev
    }

    // Calculate uptime
    const uptimeMs = Date.now() - SERVER_START_TIME;
    const uptimeHours = Math.floor(uptimeMs / (1000 * 60 * 60));
    const uptimeDays = Math.floor(uptimeHours / 24);

    const response = {
      trading: tradingStats,
      community: {
        waitlistCount,
        userCount,
      },
      system: {
        status: "operational",
        uptimeHours,
        uptimeDays,
        version: process.env.npm_package_version || "1.0.0",
      },
      generatedAt: new Date().toISOString(),
    };

    return NextResponse.json(response, {
      headers: {
        "Cache-Control": "public, max-age=60, s-maxage=60",
      },
    });
  } catch (error) {
    console.error("Stats error:", error);
    return NextResponse.json(
      { error: "Failed to fetch stats" },
      { status: 500 }
    );
  }
}
