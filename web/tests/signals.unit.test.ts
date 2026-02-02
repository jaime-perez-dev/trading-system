import { describe, it, expect } from 'vitest'
import {
  formatSignalFromTrade,
  formatSignalFromEdgeEvent,
  hasAssociatedTrade,
  combineSignals,
  applyFreeTierDelay,
  formatPnL,
  calculateShares,
  calculatePotentialProfit,
  calculateROI,
  type PaperTrade,
  type EdgeEvent,
  type Signal,
} from '../src/lib/signals'

describe('Signal Business Logic', () => {
  describe('formatSignalFromTrade', () => {
    it('formats open trade correctly', () => {
      const trade: PaperTrade = {
        id: 1,
        type: 'BUY',
        market_slug: 'will-openai-release-gpt5',
        question: 'Will OpenAI release GPT-5 in 2026?',
        outcome: 'YES',
        entry_price: 45.5,
        amount: 100,
        shares: 219,
        reason: 'GPT-5 announcement detected',
        timestamp: '2026-02-01T10:00:00Z',
        status: 'OPEN',
        exit_price: null,
        pnl: null,
      }

      const signal = formatSignalFromTrade(trade)

      expect(signal.id).toBe('trade-1')
      expect(signal.headline).toBe('GPT-5 announcement detected')
      expect(signal.market).toBe('Will OpenAI release GPT-5 in 2026?')
      expect(signal.signal).toBe('BUY YES')
      expect(signal.confidence).toBe('HIGH')
      expect(signal.priceAtSignal).toBe('45.5%')
      expect(signal.currentPrice).toBe('45.5%') // Same as entry when no exit
      expect(signal.pnl).toBeUndefined()
      expect(signal.status).toBe('open')
    })

    it('formats closed trade with profit', () => {
      const trade: PaperTrade = {
        id: 2,
        type: 'BUY',
        market_slug: 'will-anthropic-raise-2026',
        question: 'Will Anthropic raise $5B?',
        outcome: 'YES',
        entry_price: 30.0,
        amount: 200,
        shares: 666,
        reason: 'Funding round leaked',
        timestamp: '2026-01-20T14:00:00Z',
        status: 'CLOSED',
        exit_price: 85.0,
        pnl: 366.70,
      }

      const signal = formatSignalFromTrade(trade)

      expect(signal.status).toBe('closed')
      expect(signal.priceAtSignal).toBe('30.0%')
      expect(signal.currentPrice).toBe('85.0%')
      expect(signal.pnl).toBe('+$366.70')
    })

    it('formats closed trade with loss', () => {
      const trade: PaperTrade = {
        id: 3,
        type: 'BUY',
        market_slug: 'will-google-acquire',
        question: 'Will Google acquire Anthropic?',
        outcome: 'YES',
        entry_price: 60.0,
        amount: 100,
        shares: 166,
        reason: 'Merger rumor',
        timestamp: '2026-01-15T09:00:00Z',
        status: 'CLOSED',
        exit_price: 15.0,
        pnl: -75.10,
      }

      const signal = formatSignalFromTrade(trade)

      expect(signal.pnl).toBe('-$75.10')
    })

    it('uses default headline when reason empty', () => {
      const trade: PaperTrade = {
        id: 4,
        type: 'SELL',
        market_slug: 'test-market',
        question: 'Test Question?',
        outcome: 'NO',
        entry_price: 50.0,
        amount: 50,
        shares: 100,
        reason: '',
        timestamp: '2026-02-01T12:00:00Z',
        status: 'OPEN',
        exit_price: null,
        pnl: null,
      }

      const signal = formatSignalFromTrade(trade)

      expect(signal.headline).toBe('Signal detected for Test Question?')
      expect(signal.signal).toBe('SELL NO')
    })
  })

  describe('formatSignalFromEdgeEvent', () => {
    it('formats edge event correctly', () => {
      const event: EdgeEvent = {
        id: 100,
        type: 'news',
        headline: 'OpenAI announces GPT-5 preview',
        source: 'TechCrunch',
        market_slug: 'will-openai-release-gpt5-2026',
        news_time: '2026-02-01T08:00:00Z',
        market_price_at_news: '25.5',
        market_price_1h_later: '42.0',
        market_price_24h_later: null,
        final_resolution: null,
        notes: 'Major announcement',
      }

      const signal = formatSignalFromEdgeEvent(event)

      expect(signal.id).toBe('edge-100')
      expect(signal.headline).toBe('OpenAI announces GPT-5 preview')
      expect(signal.market).toBe('will openai release gpt') // Numbers stripped
      expect(signal.signal).toBe('NEWS ALERT')
      expect(signal.priceAtSignal).toBe('25.5%')
      expect(signal.currentPrice).toBe('42.0%')
      expect(signal.status).toBe('pending')
    })

    it('handles missing prices gracefully', () => {
      const event: EdgeEvent = {
        id: 101,
        type: 'news',
        headline: 'Mystery event',
        source: 'Unknown',
        market_slug: 'mystery-market-123',
        news_time: '2026-02-01T10:00:00Z',
        market_price_at_news: '',
        market_price_1h_later: null,
        market_price_24h_later: null,
        final_resolution: null,
        notes: '',
      }

      const signal = formatSignalFromEdgeEvent(event)

      expect(signal.priceAtSignal).toBe('N/A')
      expect(signal.currentPrice).toBeUndefined()
    })
  })

  describe('hasAssociatedTrade', () => {
    const signals: Signal[] = [
      {
        id: 'trade-1',
        date: '02/01/2026 10:00',
        headline: 'OpenAI announces GPT-5 release date',
        market: 'Will OpenAI release GPT-5?',
        signal: 'BUY YES',
        confidence: 'HIGH',
        priceAtSignal: '30%',
        status: 'open',
      },
    ]

    it('returns true when headline matches', () => {
      const event: EdgeEvent = {
        id: 1,
        type: 'news',
        headline: 'OpenAI announces GPT-5 release date confirmed',
        source: 'TechCrunch',
        market_slug: 'some-other-market',
        news_time: '2026-02-01T10:00:00Z',
        market_price_at_news: '30',
        market_price_1h_later: null,
        market_price_24h_later: null,
        final_resolution: null,
        notes: '',
      }

      expect(hasAssociatedTrade(event, signals)).toBe(true)
    })

    it('returns true when market slug matches', () => {
      const event: EdgeEvent = {
        id: 2,
        type: 'news',
        headline: 'Completely different headline',
        source: 'Unknown',
        market_slug: 'will-openai-release-gpt5',
        news_time: '2026-02-01T11:00:00Z',
        market_price_at_news: '35',
        market_price_1h_later: null,
        market_price_24h_later: null,
        final_resolution: null,
        notes: '',
      }

      expect(hasAssociatedTrade(event, signals)).toBe(true)
    })

    it('returns false when no match', () => {
      const event: EdgeEvent = {
        id: 3,
        type: 'news',
        headline: 'Anthropic raises funding',
        source: 'Bloomberg',
        market_slug: 'will-anthropic-raise-funds',
        news_time: '2026-02-01T12:00:00Z',
        market_price_at_news: '50',
        market_price_1h_later: null,
        market_price_24h_later: null,
        final_resolution: null,
        notes: '',
      }

      expect(hasAssociatedTrade(event, signals)).toBe(false)
    })
  })

  describe('combineSignals', () => {
    it('combines trades and unique edge events', () => {
      const trades: PaperTrade[] = [
        {
          id: 1,
          type: 'BUY',
          market_slug: 'test-market',
          question: 'Test Question?',
          outcome: 'YES',
          entry_price: 50,
          amount: 100,
          shares: 200,
          reason: 'Test trade',
          timestamp: '2026-02-01T12:00:00Z',
          status: 'OPEN',
          exit_price: null,
          pnl: null,
        },
      ]

      const edgeEvents: EdgeEvent[] = [
        {
          id: 100,
          type: 'news',
          headline: 'Unrelated news event',
          source: 'Reuters',
          market_slug: 'different-market-slug',
          news_time: '2026-02-01T11:00:00Z',
          market_price_at_news: '40',
          market_price_1h_later: null,
          market_price_24h_later: null,
          final_resolution: null,
          notes: '',
        },
      ]

      const combined = combineSignals(trades, edgeEvents)

      expect(combined).toHaveLength(2)
      expect(combined[0].id).toBe('trade-1') // Newer by timestamp
      expect(combined[1].id).toBe('edge-100')
    })

    it('filters out duplicate edge events', () => {
      const trades: PaperTrade[] = [
        {
          id: 1,
          type: 'BUY',
          market_slug: 'openai-gpt5-release',
          question: 'Will OpenAI release GPT-5?',
          outcome: 'YES',
          entry_price: 50,
          amount: 100,
          shares: 200,
          reason: 'OpenAI announces GPT-5 preview',
          timestamp: '2026-02-01T12:00:00Z',
          status: 'OPEN',
          exit_price: null,
          pnl: null,
        },
      ]

      const edgeEvents: EdgeEvent[] = [
        {
          id: 100,
          type: 'news',
          headline: 'OpenAI announces GPT-5 preview confirmed',
          source: 'TechCrunch',
          market_slug: 'openai-gpt5-release',
          news_time: '2026-02-01T11:00:00Z',
          market_price_at_news: '40',
          market_price_1h_later: null,
          market_price_24h_later: null,
          final_resolution: null,
          notes: '',
        },
      ]

      const combined = combineSignals(trades, edgeEvents)

      // Edge event should be filtered out (matches trade headline)
      expect(combined).toHaveLength(1)
      expect(combined[0].id).toBe('trade-1')
    })

    it('sorts by date descending', () => {
      const trades: PaperTrade[] = [
        {
          id: 1,
          type: 'BUY',
          market_slug: 'old-market',
          question: 'Old trade?',
          outcome: 'YES',
          entry_price: 50,
          amount: 100,
          shares: 200,
          reason: 'Old trade',
          timestamp: '2026-01-01T12:00:00Z', // Old
          status: 'CLOSED',
          exit_price: 80,
          pnl: 60,
        },
        {
          id: 2,
          type: 'BUY',
          market_slug: 'new-market',
          question: 'New trade?',
          outcome: 'YES',
          entry_price: 30,
          amount: 100,
          shares: 333,
          reason: 'New trade',
          timestamp: '2026-02-01T12:00:00Z', // New
          status: 'OPEN',
          exit_price: null,
          pnl: null,
        },
      ]

      const combined = combineSignals(trades, [])

      expect(combined[0].id).toBe('trade-2') // Newer first
      expect(combined[1].id).toBe('trade-1')
    })
  })

  describe('applyFreeTierDelay', () => {
    const now = new Date('2026-02-01T12:00:00Z').getTime()

    it('filters out signals from last 15 minutes', () => {
      const signals: Signal[] = [
        {
          id: '1',
          date: '2026-02-01T11:50:00Z', // 10 min ago - should be filtered
          headline: 'Recent signal',
          market: 'Test',
          signal: 'BUY YES',
          confidence: 'HIGH',
          priceAtSignal: '50%',
          status: 'open',
        },
        {
          id: '2',
          date: '2026-02-01T11:30:00Z', // 30 min ago - should pass
          headline: 'Older signal',
          market: 'Test',
          signal: 'BUY YES',
          confidence: 'HIGH',
          priceAtSignal: '40%',
          status: 'open',
        },
      ]

      const filtered = applyFreeTierDelay(signals, now)

      expect(filtered).toHaveLength(1)
      expect(filtered[0].id).toBe('2')
    })

    it('returns all signals if all are old enough', () => {
      const signals: Signal[] = [
        {
          id: '1',
          date: '2026-02-01T10:00:00Z', // 2 hours ago
          headline: 'Old signal',
          market: 'Test',
          signal: 'BUY YES',
          confidence: 'HIGH',
          priceAtSignal: '50%',
          status: 'open',
        },
      ]

      const filtered = applyFreeTierDelay(signals, now)

      expect(filtered).toHaveLength(1)
    })

    it('returns empty array if all signals are too recent', () => {
      const signals: Signal[] = [
        {
          id: '1',
          date: '2026-02-01T11:55:00Z', // 5 min ago
          headline: 'Very recent',
          market: 'Test',
          signal: 'BUY YES',
          confidence: 'HIGH',
          priceAtSignal: '50%',
          status: 'open',
        },
      ]

      const filtered = applyFreeTierDelay(signals, now)

      expect(filtered).toHaveLength(0)
    })
  })

  describe('formatPnL', () => {
    it('formats positive P&L with plus sign', () => {
      expect(formatPnL(100.50)).toBe('+$100.50')
    })

    it('formats negative P&L with minus sign', () => {
      expect(formatPnL(-50.25)).toBe('-$50.25')
    })

    it('formats zero P&L', () => {
      expect(formatPnL(0)).toBe('$0.00')
    })

    it('returns undefined for null', () => {
      expect(formatPnL(null)).toBeUndefined()
    })
  })

  describe('calculateShares', () => {
    it('calculates shares correctly', () => {
      // $100 at 50% = $0.50/share = 200 shares
      expect(calculateShares(100, 50)).toBe(200)
    })

    it('calculates shares at low price', () => {
      // $100 at 10% = $0.10/share = 1000 shares
      expect(calculateShares(100, 10)).toBe(1000)
    })

    it('handles fractional results by flooring', () => {
      // $100 at 33% = ~303 shares
      expect(calculateShares(100, 33)).toBe(303)
    })

    it('returns 0 for invalid price (0%)', () => {
      expect(calculateShares(100, 0)).toBe(0)
    })

    it('returns 0 for invalid price (100%)', () => {
      expect(calculateShares(100, 100)).toBe(0)
    })

    it('returns 0 for negative price', () => {
      expect(calculateShares(100, -5)).toBe(0)
    })
  })

  describe('calculatePotentialProfit', () => {
    it('calculates profit for favorable odds', () => {
      // 200 shares at 50% entry = $100 cost, $200 payout = $100 profit
      expect(calculatePotentialProfit(200, 50)).toBe(100)
    })

    it('calculates profit for low entry', () => {
      // 1000 shares at 10% = $100 cost, $1000 payout = $900 profit
      expect(calculatePotentialProfit(1000, 10)).toBe(900)
    })

    it('returns 0 for 100% entry (no profit)', () => {
      // 100 shares at 100% = $100 cost, $100 payout = $0 profit
      expect(calculatePotentialProfit(100, 100)).toBe(0)
    })
  })

  describe('calculateROI', () => {
    it('calculates ROI correctly', () => {
      // $100 profit on $100 cost = 100% ROI
      expect(calculateROI(100, 100)).toBe(100)
    })

    it('calculates high ROI', () => {
      // $900 profit on $100 cost = 900% ROI
      expect(calculateROI(900, 100)).toBe(900)
    })

    it('calculates negative ROI', () => {
      // -$50 loss on $100 cost = -50% ROI
      expect(calculateROI(-50, 100)).toBe(-50)
    })

    it('returns 0 for zero cost basis', () => {
      expect(calculateROI(100, 0)).toBe(0)
    })
  })
})
