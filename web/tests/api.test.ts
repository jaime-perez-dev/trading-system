import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { spawn, ChildProcess } from 'child_process'

const BASE_URL = 'http://localhost:3456'
let serverProcess: ChildProcess | null = null

// Simple fetch wrapper
async function api(path: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await res.json().catch(() => null)
  return { status: res.status, data, headers: res.headers }
}

describe('EdgeSignals API', () => {
  // Note: These tests assume a dev server is running
  // Run: npm run dev -- -p 3456

  describe('GET /api/signals', () => {
    it('returns signals array for free tier', async () => {
      const { status, data } = await api('/api/signals')
      expect(status).toBe(200)
      expect(data).toHaveProperty('signals')
      expect(Array.isArray(data.signals)).toBe(true)
      expect(data.meta).toHaveProperty('tier', 'free')
      expect(data.meta).toHaveProperty('delayed', true)
    })

    it('respects limit parameter', async () => {
      const { status, data } = await api('/api/signals?limit=5')
      expect(status).toBe(200)
      expect(data.signals.length).toBeLessThanOrEqual(5)
    })

    it('returns pro tier without delay', async () => {
      const { status, data } = await api('/api/signals?tier=pro')
      expect(status).toBe(200)
      expect(data.meta.tier).toBe('pro')
      expect(data.meta.delayed).toBe(false)
    })
  })

  describe('GET /api/track-record', () => {
    it('returns track record data', async () => {
      const { status, data } = await api('/api/track-record')
      expect(status).toBe(200)
      expect(data).toHaveProperty('trades')
      expect(data).toHaveProperty('stats')
    })
  })

  describe('POST /api/waitlist', () => {
    it('rejects invalid email', async () => {
      const { status, data } = await api('/api/waitlist', {
        method: 'POST',
        body: JSON.stringify({ email: 'not-an-email' }),
      })
      expect(status).toBe(400)
      expect(data.error).toContain('Invalid')
    })

    it('rejects missing email', async () => {
      const { status } = await api('/api/waitlist', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      expect(status).toBe(400)
    })
  })

  describe('GET /api/waitlist', () => {
    it('returns waitlist count', async () => {
      const { status, data } = await api('/api/waitlist')
      expect(status).toBe(200)
      expect(typeof data.count).toBe('number')
    })
  })
})
