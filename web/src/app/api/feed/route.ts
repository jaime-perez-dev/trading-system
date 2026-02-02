import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

interface Trade {
  id: number;
  status: string;
  reason: string;
  market: string;
  entry_price: number;
  exit_price?: number;
  position: string;
  shares: number;
  stake: number;
  pnl?: number;
  opened_at: string;
  closed_at?: string;
}

interface EdgeEvent {
  id: number;
  headline: string;
  source: string;
  logged_at: string;
  market_before?: number;
  market_after?: number;
  acted: string;
  trade_id?: number;
}

/**
 * GET /api/feed
 * Returns RSS 2.0 feed of recent trading signals
 * Public endpoint for RSS readers
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get("limit") || "20"), 50);

  try {
    // Read paper_trades.json (same data source as /api/signals)
    const tradesPath = path.join(process.cwd(), "..", "data", "paper_trades.json");
    const eventsPath = path.join(process.cwd(), "..", "data", "edge_events.json");

    let trades: Trade[] = [];
    let events: EdgeEvent[] = [];

    try {
      const tradesData = await fs.readFile(tradesPath, "utf-8");
      trades = JSON.parse(tradesData);
    } catch {
      // No trades file yet
    }

    try {
      const eventsData = await fs.readFile(eventsPath, "utf-8");
      events = JSON.parse(eventsData);
    } catch {
      // No events file yet
    }

    // Build feed items from both trades and events
    const items: { title: string; description: string; pubDate: string; guid: string }[] = [];

    // Add trades as feed items
    for (const trade of trades.slice(-limit)) {
      const title = trade.status === "open"
        ? `🔵 NEW: ${trade.position.toUpperCase()} at ${trade.entry_price}%`
        : trade.pnl && trade.pnl > 0
          ? `✅ WIN: +$${trade.pnl.toFixed(2)}`
          : `🔴 LOSS: $${trade.pnl?.toFixed(2) || 0}`;

      items.push({
        title: `${title} - ${trade.market}`,
        description: `
          <p><strong>Market:</strong> ${trade.market}</p>
          <p><strong>Position:</strong> ${trade.position.toUpperCase()}</p>
          <p><strong>Entry:</strong> ${trade.entry_price}%</p>
          ${trade.exit_price ? `<p><strong>Exit:</strong> ${trade.exit_price}%</p>` : ""}
          <p><strong>Thesis:</strong> ${trade.reason}</p>
          ${trade.pnl !== undefined ? `<p><strong>P&L:</strong> $${trade.pnl.toFixed(2)}</p>` : ""}
        `.trim(),
        pubDate: new Date(trade.opened_at).toUTCString(),
        guid: `trade-${trade.id}`,
      });
    }

    // Add events as feed items (that don't have an associated trade)
    const tradedEventIds = new Set(trades.filter(t => t.id).map(t => t.id));
    for (const event of events.slice(-limit)) {
      if (!event.trade_id || !tradedEventIds.has(event.trade_id)) {
        const priceChange = event.market_before && event.market_after
          ? event.market_after - event.market_before
          : null;
        const changeStr = priceChange !== null
          ? priceChange > 0 ? `+${priceChange}%` : `${priceChange}%`
          : "";

        items.push({
          title: `📰 ${event.headline}`,
          description: `
            <p><strong>Source:</strong> ${event.source}</p>
            ${event.market_before ? `<p><strong>Market Before:</strong> ${event.market_before}%</p>` : ""}
            ${event.market_after ? `<p><strong>Market After:</strong> ${event.market_after}%</p>` : ""}
            ${changeStr ? `<p><strong>Change:</strong> ${changeStr}</p>` : ""}
            <p><strong>Action:</strong> ${event.acted}</p>
          `.trim(),
          pubDate: new Date(event.logged_at).toUTCString(),
          guid: `event-${event.id}`,
        });
      }
    }

    // Sort by date descending
    items.sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime());

    // Build RSS XML
    const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>EdgeSignals - AI Prediction Market Alerts</title>
    <link>https://edgesignals.ai</link>
    <description>Real-time trading signals for AI prediction markets. Get alerts when news moves markets.</description>
    <language>en-us</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="https://edgesignals.ai/api/feed" rel="self" type="application/rss+xml"/>
    ${items.slice(0, limit).map(item => `
    <item>
      <title><![CDATA[${item.title}]]></title>
      <description><![CDATA[${item.description}]]></description>
      <pubDate>${item.pubDate}</pubDate>
      <guid isPermaLink="false">${item.guid}</guid>
    </item>`).join("")}
  </channel>
</rss>`;

    return new NextResponse(rss, {
      status: 200,
      headers: {
        "Content-Type": "application/rss+xml; charset=utf-8",
        "Cache-Control": "public, max-age=300", // Cache for 5 minutes
      },
    });
  } catch (error) {
    console.error("RSS feed error:", error);
    return NextResponse.json(
      { error: "Failed to generate feed" },
      { status: 500 }
    );
  }
}
