// Signal processing logic - extracted for testability

export interface Signal {
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

export interface PaperTrade {
  id: number;
  type: string;
  market_slug: string;
  question: string;
  outcome: string;
  entry_price: number;
  amount: number;
  shares: number;
  reason: string;
  timestamp: string;
  status: string;
  exit_price: number | null;
  pnl: number | null;
}

export interface EdgeEvent {
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

/**
 * Format a paper trade into a display signal
 */
export function formatSignalFromTrade(trade: PaperTrade): Signal {
  const entryPercent = trade.entry_price.toFixed(1);
  const currentPercent = trade.exit_price !== null
    ? trade.exit_price.toFixed(1) 
    : entryPercent;

  return {
    id: `trade-${trade.id}`,
    date: formatDateForDisplay(trade.timestamp),
    headline: trade.reason || `Signal detected for ${trade.question}`,
    market: trade.question,
    signal: `${trade.type.toUpperCase()} ${trade.outcome.toUpperCase()}`,
    confidence: "HIGH",
    priceAtSignal: `${entryPercent}%`,
    currentPrice: `${currentPercent}%`,
    pnl: formatPnL(trade.pnl),
    status: trade.status.toLowerCase() as "open" | "closed",
  };
}

/**
 * Format edge event into a display signal
 */
export function formatSignalFromEdgeEvent(event: EdgeEvent): Signal {
  return {
    id: `edge-${event.id}`,
    date: formatDateForDisplay(event.news_time),
    headline: event.headline,
    market: event.market_slug.replace(/-/g, " ").replace(/\d+/g, "").trim(),
    signal: "NEWS ALERT",
    confidence: "HIGH",
    priceAtSignal: event.market_price_at_news ? `${event.market_price_at_news}%` : "N/A",
    currentPrice: event.market_price_1h_later ? `${event.market_price_1h_later}%` : undefined,
    status: "pending",
  };
}

/**
 * Format date for consistent display
 */
export function formatDateForDisplay(timestamp: string): string {
  return new Date(timestamp).toLocaleString("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).replace(",", "");
}

/**
 * Check if edge event has associated trade in signals list
 */
export function hasAssociatedTrade(event: EdgeEvent, signals: Signal[]): boolean {
  return signals.some((s) => 
    s.headline.toLowerCase().includes(event.headline.toLowerCase().slice(0, 30)) ||
    s.market.toLowerCase().includes(event.market_slug.split("-").slice(0, 3).join(" "))
  );
}

/**
 * Combine trades and edge events into unified signals list
 */
export function combineSignals(trades: PaperTrade[], edgeEvents: EdgeEvent[]): Signal[] {
  const signals: Signal[] = trades.map(formatSignalFromTrade);

  edgeEvents.forEach((event) => {
    if (!hasAssociatedTrade(event, signals)) {
      signals.push(formatSignalFromEdgeEvent(event));
    }
  });

  // Sort by date descending
  return signals.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

/**
 * Apply free tier delay filter (hide signals newer than 15 minutes)
 */
export function applyFreeTierDelay(signals: Signal[], nowMs: number = Date.now()): Signal[] {
  const fifteenMinutesAgo = nowMs - 15 * 60 * 1000;
  return signals.filter(s => new Date(s.date).getTime() < fifteenMinutesAgo);
}

/**
 * Calculate P&L string from numeric value
 */
export function formatPnL(pnl: number | null): string | undefined {
  if (pnl === null) return undefined;
  if (pnl > 0) return `+$${pnl.toFixed(2)}`;
  if (pnl < 0) return `-$${Math.abs(pnl).toFixed(2)}`;
  return `$${pnl.toFixed(2)}`;
}

/**
 * Calculate share count from amount and price
 */
export function calculateShares(amount: number, pricePercent: number): number {
  if (pricePercent <= 0 || pricePercent >= 100) return 0;
  const pricePerShare = pricePercent / 100;
  return Math.floor(amount / pricePerShare);
}

/**
 * Calculate potential profit from position
 */
export function calculatePotentialProfit(shares: number, entryPrice: number): number {
  // Each share pays $1 if correct, cost is entry price per share
  const costBasis = shares * (entryPrice / 100);
  return shares - costBasis;
}

/**
 * Calculate ROI percentage
 */
export function calculateROI(profit: number, costBasis: number): number {
  if (costBasis === 0) return 0;
  return (profit / costBasis) * 100;
}
