# EdgeSignals API Reference

Base URL: `https://your-domain.com` (or `http://localhost:3000` for development)

---

## Rate Limiting

All API endpoints (except `/api/health` and `/api/auth/*`) are rate limited.

**Default Limits:**
| Tier | Requests/minute |
|------|-----------------|
| Unauthenticated | 20 |
| Free | 10 |
| Pro | 100 |
| Enterprise | 1000 |

**Response Headers:**
- `X-RateLimit-Limit` - Maximum requests per window
- `X-RateLimit-Remaining` - Remaining requests in current window
- `X-RateLimit-Reset` - Seconds until window resets

**429 Rate Limit Exceeded:**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please retry in 45 seconds.",
  "retryAfter": 45
}
```

The `Retry-After` header is also included with the wait time in seconds.

---

## Health Check

### GET /api/health
Service health status for monitoring and load balancers.

**Public:** Yes (not rate limited)

**Success Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-02T14:00:00.000Z",
  "version": "1.0.0",
  "uptime": 3600,
  "checks": {
    "api": "ok",
    "dataFiles": "ok",
    "memory": {
      "used": 85,
      "total": 256,
      "percentage": 33
    }
  }
}
```

**Status Values:**
- `healthy` - All systems operational
- `degraded` - Functional but with issues (e.g., high memory)
- `unhealthy` (503) - Critical failure

---

## Authentication

Some endpoints require authentication via NextAuth session. Public endpoints are noted below.

### POST /api/auth/signup
Create a new user account.

**Public:** Yes

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"           // optional
}
```

**Success Response (200):**
```json
{
  "success": true,
  "user": {
    "id": "clxxx...",
    "email": "user@example.com",
    "name": "John Doe",
    "tier": "free"
  }
}
```

**Error Responses:**
- `400` - Missing email/password or user already exists
- `500` - Server error

---

## Signals

### GET /api/signals
Fetch trading signals from the EdgeSignals system.

**Public:** Yes

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tier` | string | `free` | User tier: `free`, `pro`, or `enterprise` |
| `limit` | number | `10` | Max signals to return |

**Response (200):**
```json
{
  "signals": [
    {
      "id": "trade-1",
      "date": "01/28/2026 14:30",
      "headline": "OpenAI announces GPT-5 release date",
      "market": "Will GPT-5 release before March 2026?",
      "signal": "BUY YES",
      "confidence": "HIGH",
      "priceAtSignal": "45.2%",
      "currentPrice": "67.8%",
      "pnl": "+$156.40",
      "status": "closed"
    }
  ],
  "meta": {
    "tier": "free",
    "count": 1,
    "delayed": true,
    "timestamp": "2026-01-28T18:30:00.000Z"
  }
}
```

**Notes:**
- Free tier signals are delayed by 15 minutes
- Pro/Enterprise tiers get real-time signals
- Signals come from paper trades and edge events

---

## Track Record

### GET /api/track-record
Get historical trade performance and statistics.

**Public:** Yes

**Response (200):**
```json
{
  "trades": [
    {
      "id": 1,
      "type": "BUY",
      "market_slug": "will-gpt-5-release-before-march-2026",
      "question": "Will GPT-5 release before March 2026?",
      "outcome": "YES",
      "entry_price": 45.2,
      "exit_price": 67.8,
      "amount": 500,
      "shares": 1107,
      "pnl": 250.23,
      "status": "CLOSED",
      "timestamp": "2026-01-25T10:00:00Z",
      "reason": "OpenAI GPT-5 announcement"
    }
  ],
  "stats": {
    "totalTrades": 15,
    "closedTrades": 10,
    "openTrades": 5,
    "totalPnL": 1250.50,
    "winRate": 75.0,
    "avgReturn": 12.5,
    "wins": 8,
    "losses": 2
  },
  "lastUpdated": "2026-01-28T18:30:00.000Z"
}
```

---

## Waitlist

### POST /api/waitlist
Join the EdgeSignals waitlist.

**Public:** Yes

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200):**
```json
{
  "message": "Successfully joined waitlist",
  "count": 42
}
```

**Already Exists Response (200):**
```json
{
  "message": "Already on waitlist",
  "alreadyExists": true
}
```

**Error Response (400):**
```json
{
  "error": "Invalid email address"
}
```

### GET /api/waitlist
Get current waitlist count.

**Public:** Yes

**Response (200):**
```json
{
  "count": 42
}
```

---

## Push Notifications

### POST /api/notifications/subscribe
Subscribe to push notifications (Web Push).

**Request Body:**
```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/xxx",
  "keys": {
    "p256dh": "base64-encoded-key",
    "auth": "base64-encoded-auth"
  }
}
```

**Success Response (200):**
```json
{
  "message": "Subscribed successfully"
}
```

**Error Response (400):**
```json
{
  "error": "Invalid subscription data"
}
```

### POST /api/notifications/unsubscribe
Unsubscribe from push notifications.

**Request Body:**
```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/xxx"
}
```

**Success Response (200):**
```json
{
  "message": "Unsubscribed successfully"
}
```

### POST /api/notifications/send
Send a push notification (admin only).

**Request Body:**
```json
{
  "title": "New Signal!",
  "body": "BUY YES on GPT-5 market",
  "url": "/dashboard"
}
```

---

## Payments

EdgeSignals supports multiple payment providers for flexibility.

### POST /api/dodo/checkout
Create a Dodo Payments checkout session.

**Request Body:**
```json
{
  "plan": "pro"    // "pro" or "enterprise"
}
```

**Success Response (200):**
```json
{
  "url": "https://checkout.dodopayments.com/xxx"
}
```

**Error Responses:**
- `400` - Invalid or missing plan
- `503` - Payments not configured (returns waitlist URL)

### POST /api/dodo/webhook
Webhook for Dodo payment events. Called by Dodo servers.

### POST /api/lemonsqueezy/checkout
Create a LemonSqueezy checkout session.

**Request Body:**
```json
{
  "plan": "pro"    // "pro" or "enterprise"
}
```

**Success Response (200):**
```json
{
  "url": "https://checkout.lemonsqueezy.com/xxx"
}
```

### POST /api/lemonsqueezy/webhook
Webhook for LemonSqueezy payment events.

---

## Error Handling

All endpoints follow consistent error responses:

```json
{
  "error": "Human-readable error message"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad request (validation error)
- `401` - Unauthorized
- `404` - Not found
- `500` - Server error
- `503` - Service unavailable (e.g., payments not configured)

---

## Rate Limiting

Currently no rate limits are enforced on the API. This may change in the future.

---

## Tiers

| Tier | Price | Features |
|------|-------|----------|
| Free | $0/mo | Delayed signals (15 min), basic access |
| Pro | $49/mo | Real-time signals, priority alerts |
| Enterprise | $299/mo | API access, custom integrations, dedicated support |
