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

// Helper for unique test data
const testEndpoint = () => `https://test-push.example.com/${Date.now()}`

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

  describe('POST /api/notifications/subscribe', () => {
    it('rejects missing subscription data', async () => {
      const { status, data } = await api('/api/notifications/subscribe', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      expect(status).toBe(400)
      expect(data.error).toContain('Invalid subscription')
    })

    it('rejects subscription without keys', async () => {
      const { status, data } = await api('/api/notifications/subscribe', {
        method: 'POST',
        body: JSON.stringify({
          subscription: { endpoint: 'https://test.com' }
        }),
      })
      expect(status).toBe(400)
      expect(data.error).toContain('Invalid subscription')
    })

    it('accepts valid subscription', async () => {
      const endpoint = testEndpoint()
      const { status, data } = await api('/api/notifications/subscribe', {
        method: 'POST',
        body: JSON.stringify({
          subscription: {
            endpoint,
            keys: { p256dh: 'test-key', auth: 'test-auth' }
          },
          userId: 'test-user',
          tier: 'pro'
        }),
      })
      expect(status).toBe(200)
      expect(data.success).toBe(true)
    })
  })

  describe('POST /api/notifications/unsubscribe', () => {
    it('rejects missing endpoint', async () => {
      const { status, data } = await api('/api/notifications/unsubscribe', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      expect(status).toBe(400)
      expect(data.error).toContain('Endpoint required')
    })

    it('handles non-existent subscription gracefully', async () => {
      const { status, data } = await api('/api/notifications/unsubscribe', {
        method: 'POST',
        body: JSON.stringify({ endpoint: 'https://nonexistent.example.com' }),
      })
      expect(status).toBe(200)
      expect(data.success).toBe(true)
      expect(data.message).toContain('not found')
    })

    it('removes existing subscription', async () => {
      // First, create a subscription
      const endpoint = testEndpoint()
      await api('/api/notifications/subscribe', {
        method: 'POST',
        body: JSON.stringify({
          subscription: {
            endpoint,
            keys: { p256dh: 'test-key', auth: 'test-auth' }
          }
        }),
      })

      // Then remove it
      const { status, data } = await api('/api/notifications/unsubscribe', {
        method: 'POST',
        body: JSON.stringify({ endpoint }),
      })
      expect(status).toBe(200)
      expect(data.success).toBe(true)
      expect(data.message).toContain('removed')
    })
  })

  describe('POST /api/auth/signup', () => {
    it('rejects missing email', async () => {
      const { status, data } = await api('/api/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ password: 'testpass123' }),
      })
      expect(status).toBe(400)
      expect(data.error).toContain('required')
    })

    it('rejects missing password', async () => {
      const { status, data } = await api('/api/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email: 'test@example.com' }),
      })
      expect(status).toBe(400)
      expect(data.error).toContain('required')
    })

    it('rejects empty body', async () => {
      const { status, data } = await api('/api/auth/signup', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      expect(status).toBe(400)
      expect(data.error).toContain('required')
    })
  })
})
