import { describe, it, expect } from 'vitest'

/**
 * Unit tests for RSS feed generation logic
 * Tests cover XML structure, item formatting, and edge cases
 */

interface FeedItem {
  title: string
  description: string
  pubDate: string
  guid: string
}

interface Trade {
  id: number
  status: string
  reason: string
  market: string
  entry_price: number
  exit_price?: number
  position: string
  shares: number
  stake: number
  pnl?: number
  opened_at: string
  closed_at?: string
}

interface EdgeEvent {
  id: number
  headline: string
  source: string
  logged_at: string
  market_before?: number
  market_after?: number
  acted: string
  trade_id?: number
}

// Helper function to generate feed item from trade (mirrors route logic)
function formatTradeToFeedItem(trade: Trade): FeedItem {
  const title = trade.status === "open"
    ? `🔵 NEW: ${trade.position.toUpperCase()} at ${trade.entry_price}%`
    : trade.pnl && trade.pnl > 0
      ? `✅ WIN: +$${trade.pnl.toFixed(2)}`
      : `🔴 LOSS: $${trade.pnl?.toFixed(2) || 0}`;

  return {
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
  };
}

// Helper function to generate feed item from event (mirrors route logic)
function formatEventToFeedItem(event: EdgeEvent): FeedItem {
  const priceChange = event.market_before && event.market_after
    ? event.market_after - event.market_before
    : null;
  const changeStr = priceChange !== null
    ? priceChange > 0 ? `+${priceChange}%` : `${priceChange}%`
    : "";

  return {
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
  };
}

describe('RSS Feed Generation', () => {
  describe('formatTradeToFeedItem', () => {
    it('formats open trade correctly', () => {
      const trade: Trade = {
        id: 1,
        status: 'open',
        reason: 'GPT-5 announcement',
        market: 'Will OpenAI release GPT-5?',
        entry_price: 45,
        position: 'yes',
        shares: 100,
        stake: 45,
        opened_at: '2026-02-01T10:00:00Z',
      }

      const item = formatTradeToFeedItem(trade)

      expect(item.title).toBe('🔵 NEW: YES at 45% - Will OpenAI release GPT-5?')
      expect(item.guid).toBe('trade-1')
      expect(item.description).toContain('GPT-5 announcement')
      expect(item.description).toContain('YES')
    })

    it('formats winning trade correctly', () => {
      const trade: Trade = {
        id: 2,
        status: 'closed',
        reason: 'GPT-5 announcement',
        market: 'Will OpenAI release GPT-5?',
        entry_price: 45,
        exit_price: 75,
        position: 'yes',
        shares: 100,
        stake: 45,
        pnl: 30,
        opened_at: '2026-02-01T10:00:00Z',
        closed_at: '2026-02-01T12:00:00Z',
      }

      const item = formatTradeToFeedItem(trade)

      expect(item.title).toContain('✅ WIN: +$30.00')
      expect(item.description).toContain('Exit:</strong> 75%')
      expect(item.description).toContain('P&L:</strong> $30.00')
    })

    it('formats losing trade correctly', () => {
      const trade: Trade = {
        id: 3,
        status: 'closed',
        reason: 'Bad call',
        market: 'Will AI pass test?',
        entry_price: 60,
        exit_price: 40,
        position: 'yes',
        shares: 100,
        stake: 60,
        pnl: -20,
        opened_at: '2026-02-01T10:00:00Z',
      }

      const item = formatTradeToFeedItem(trade)

      expect(item.title).toContain('🔴 LOSS: $-20.00')
    })

    it('generates valid pubDate', () => {
      const trade: Trade = {
        id: 1,
        status: 'open',
        reason: 'Test',
        market: 'Test market',
        entry_price: 50,
        position: 'yes',
        shares: 10,
        stake: 5,
        opened_at: '2026-02-01T14:30:00Z',
      }

      const item = formatTradeToFeedItem(trade)
      const date = new Date(item.pubDate)
      
      expect(date.getTime()).not.toBeNaN()
    })
  })

  describe('formatEventToFeedItem', () => {
    it('formats event with price change correctly', () => {
      const event: EdgeEvent = {
        id: 1,
        headline: 'OpenAI announces GPT-5',
        source: 'Reuters',
        logged_at: '2026-02-01T10:00:00Z',
        market_before: 45,
        market_after: 65,
        acted: 'BUY',
      }

      const item = formatEventToFeedItem(event)

      expect(item.title).toBe('📰 OpenAI announces GPT-5')
      expect(item.guid).toBe('event-1')
      expect(item.description).toContain('Reuters')
      expect(item.description).toContain('+20%')
    })

    it('formats event with negative price change', () => {
      const event: EdgeEvent = {
        id: 2,
        headline: 'AI regulation passed',
        source: 'NYT',
        logged_at: '2026-02-01T10:00:00Z',
        market_before: 70,
        market_after: 50,
        acted: 'SELL',
      }

      const item = formatEventToFeedItem(event)

      expect(item.description).toContain('-20%')
    })

    it('handles event without price data', () => {
      const event: EdgeEvent = {
        id: 3,
        headline: 'Breaking news',
        source: 'Twitter',
        logged_at: '2026-02-01T10:00:00Z',
        acted: 'WATCH',
      }

      const item = formatEventToFeedItem(event)

      expect(item.title).toBe('📰 Breaking news')
      expect(item.description).not.toContain('Change')
    })
  })

  describe('Feed item sorting', () => {
    it('sorts items by date descending', () => {
      const items: FeedItem[] = [
        { title: 'Old', description: '', pubDate: new Date('2026-02-01').toUTCString(), guid: '1' },
        { title: 'New', description: '', pubDate: new Date('2026-02-03').toUTCString(), guid: '2' },
        { title: 'Mid', description: '', pubDate: new Date('2026-02-02').toUTCString(), guid: '3' },
      ]

      items.sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime())

      expect(items[0].title).toBe('New')
      expect(items[1].title).toBe('Mid')
      expect(items[2].title).toBe('Old')
    })
  })

  describe('GUID uniqueness', () => {
    it('generates unique GUIDs for trades and events', () => {
      const trade: Trade = {
        id: 1,
        status: 'open',
        reason: 'Test',
        market: 'Test',
        entry_price: 50,
        position: 'yes',
        shares: 10,
        stake: 5,
        opened_at: '2026-02-01T10:00:00Z',
      }

      const event: EdgeEvent = {
        id: 1,
        headline: 'Test',
        source: 'Test',
        logged_at: '2026-02-01T10:00:00Z',
        acted: 'WATCH',
      }

      const tradeItem = formatTradeToFeedItem(trade)
      const eventItem = formatEventToFeedItem(event)

      expect(tradeItem.guid).toBe('trade-1')
      expect(eventItem.guid).toBe('event-1')
      expect(tradeItem.guid).not.toBe(eventItem.guid)
    })
  })

  describe('XML safety', () => {
    it('handles special characters in headlines', () => {
      const event: EdgeEvent = {
        id: 1,
        headline: 'OpenAI <> Google: "AI War"',
        source: 'Reuters & AP',
        logged_at: '2026-02-01T10:00:00Z',
        acted: 'WATCH',
      }

      const item = formatEventToFeedItem(event)
      
      // The title should contain the raw characters (CDATA wrapping handles escaping)
      expect(item.title).toContain('OpenAI <> Google')
      expect(item.description).toContain('Reuters & AP')
    })
  })
})
