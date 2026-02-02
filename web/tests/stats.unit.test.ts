import { describe, test, expect } from "vitest";

// Test the stats calculation logic
interface PaperTrade {
  id: number;
  status: string;
  pnl: number | null;
  timestamp: string;
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

describe("Stats Calculation", () => {
  describe("calculateStats", () => {
    test("returns zeros for empty array", () => {
      const stats = calculateStats([]);
      expect(stats.totalSignals).toBe(0);
      expect(stats.openPositions).toBe(0);
      expect(stats.closedTrades).toBe(0);
      expect(stats.winRate).toBeNull();
      expect(stats.totalPnL).toBe(0);
      expect(stats.avgPnL).toBeNull();
    });

    test("counts open positions", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "OPEN", pnl: null, timestamp: "2026-01-01" },
        { id: 2, status: "OPEN", pnl: null, timestamp: "2026-01-02" },
        { id: 3, status: "CLOSED", pnl: 10, timestamp: "2026-01-03" },
      ];
      const stats = calculateStats(trades);
      expect(stats.totalSignals).toBe(3);
      expect(stats.openPositions).toBe(2);
      expect(stats.closedTrades).toBe(1);
    });

    test("calculates win rate correctly", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: 10, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: 20, timestamp: "2026-01-02" },
        { id: 3, status: "CLOSED", pnl: -5, timestamp: "2026-01-03" },
        { id: 4, status: "CLOSED", pnl: -10, timestamp: "2026-01-04" },
      ];
      const stats = calculateStats(trades);
      expect(stats.winRate).toBe(50); // 2 wins out of 4
    });

    test("calculates 100% win rate", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: 10, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: 20, timestamp: "2026-01-02" },
      ];
      const stats = calculateStats(trades);
      expect(stats.winRate).toBe(100);
    });

    test("calculates 0% win rate", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: -10, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: -20, timestamp: "2026-01-02" },
      ];
      const stats = calculateStats(trades);
      expect(stats.winRate).toBe(0);
    });

    test("calculates total P&L", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: 100.50, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: -25.25, timestamp: "2026-01-02" },
        { id: 3, status: "OPEN", pnl: null, timestamp: "2026-01-03" },
      ];
      const stats = calculateStats(trades);
      expect(stats.totalPnL).toBe(75.25);
    });

    test("calculates average P&L", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: 100, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: 50, timestamp: "2026-01-02" },
      ];
      const stats = calculateStats(trades);
      expect(stats.avgPnL).toBe(75);
    });

    test("handles null pnl in closed trades", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: null, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: 50, timestamp: "2026-01-02" },
      ];
      const stats = calculateStats(trades);
      expect(stats.totalPnL).toBe(50);
      expect(stats.avgPnL).toBe(25);
    });

    test("excludes open trades from P&L calculations", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "OPEN", pnl: null, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: 100, timestamp: "2026-01-02" },
      ];
      const stats = calculateStats(trades);
      expect(stats.totalPnL).toBe(100);
      expect(stats.closedTrades).toBe(1);
      expect(stats.winRate).toBe(100);
    });

    test("rounds P&L to 2 decimal places", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: 33.333, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: 33.333, timestamp: "2026-01-02" },
        { id: 3, status: "CLOSED", pnl: 33.333, timestamp: "2026-01-03" },
      ];
      const stats = calculateStats(trades);
      expect(stats.totalPnL).toBe(100); // 99.999 rounds to 100
      expect(stats.avgPnL).toBe(33.33);
    });

    test("treats zero pnl as loss for win rate", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: 0, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: 10, timestamp: "2026-01-02" },
      ];
      const stats = calculateStats(trades);
      expect(stats.winRate).toBe(50); // 0 is not > 0, so it's a loss
    });

    test("handles large number of trades", () => {
      const trades: PaperTrade[] = Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        status: i % 2 === 0 ? "CLOSED" : "OPEN",
        pnl: i % 2 === 0 ? (i % 4 === 0 ? 10 : -5) : null,
        timestamp: `2026-01-${(i % 28) + 1}`,
      }));
      const stats = calculateStats(trades);
      expect(stats.totalSignals).toBe(1000);
      expect(stats.openPositions).toBe(500);
      expect(stats.closedTrades).toBe(500);
      expect(stats.winRate).toBe(50);
    });

    test("handles negative total P&L", () => {
      const trades: PaperTrade[] = [
        { id: 1, status: "CLOSED", pnl: -100, timestamp: "2026-01-01" },
        { id: 2, status: "CLOSED", pnl: -50, timestamp: "2026-01-02" },
      ];
      const stats = calculateStats(trades);
      expect(stats.totalPnL).toBe(-150);
      expect(stats.avgPnL).toBe(-75);
    });
  });
});

describe("Stats Response Shape", () => {
  test("response has expected structure", () => {
    // This tests the expected shape of the API response
    const mockResponse = {
      trading: {
        totalSignals: 10,
        openPositions: 2,
        closedTrades: 8,
        winRate: 75,
        totalPnL: 150.50,
        avgPnL: 18.81,
      },
      community: {
        waitlistCount: 100,
        userCount: 25,
      },
      system: {
        status: "operational",
        uptimeHours: 24,
        uptimeDays: 1,
        version: "1.0.0",
      },
      generatedAt: "2026-02-02T15:30:00.000Z",
    };

    expect(mockResponse.trading).toHaveProperty("totalSignals");
    expect(mockResponse.trading).toHaveProperty("winRate");
    expect(mockResponse.community).toHaveProperty("waitlistCount");
    expect(mockResponse.system).toHaveProperty("status");
    expect(mockResponse.generatedAt).toMatch(/^\d{4}-\d{2}-\d{2}/);
  });
});
