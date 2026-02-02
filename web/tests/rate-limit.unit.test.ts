import { describe, it, expect, beforeEach } from "vitest";
import {
  checkRateLimit,
  cleanupExpiredEntries,
  getClientIdentifier,
  getRateLimitForTier,
  RATE_LIMITS,
  RateLimitRecord,
} from "../src/lib/rate-limit";

describe("RATE_LIMITS configuration", () => {
  it("has all expected tiers", () => {
    expect(RATE_LIMITS).toHaveProperty("free");
    expect(RATE_LIMITS).toHaveProperty("pro");
    expect(RATE_LIMITS).toHaveProperty("enterprise");
    expect(RATE_LIMITS).toHaveProperty("default");
  });

  it("free tier has 10 requests per minute", () => {
    expect(RATE_LIMITS.free.requests).toBe(10);
    expect(RATE_LIMITS.free.windowMs).toBe(60000);
  });

  it("pro tier has 100 requests per minute", () => {
    expect(RATE_LIMITS.pro.requests).toBe(100);
    expect(RATE_LIMITS.pro.windowMs).toBe(60000);
  });

  it("enterprise tier has 1000 requests per minute", () => {
    expect(RATE_LIMITS.enterprise.requests).toBe(1000);
    expect(RATE_LIMITS.enterprise.windowMs).toBe(60000);
  });

  it("default tier has 20 requests per minute", () => {
    expect(RATE_LIMITS.default.requests).toBe(20);
    expect(RATE_LIMITS.default.windowMs).toBe(60000);
  });

  it("tiers are ordered by limit size", () => {
    expect(RATE_LIMITS.free.requests).toBeLessThan(RATE_LIMITS.default.requests);
    expect(RATE_LIMITS.default.requests).toBeLessThan(RATE_LIMITS.pro.requests);
    expect(RATE_LIMITS.pro.requests).toBeLessThan(RATE_LIMITS.enterprise.requests);
  });
});

describe("getClientIdentifier", () => {
  it("returns fallback when forwardedFor is null", () => {
    expect(getClientIdentifier(null)).toBe("unknown");
  });

  it("returns custom fallback when forwardedFor is null", () => {
    expect(getClientIdentifier(null, "127.0.0.1")).toBe("127.0.0.1");
  });

  it("returns IP from simple X-Forwarded-For", () => {
    expect(getClientIdentifier("192.168.1.1")).toBe("192.168.1.1");
  });

  it("returns first IP from comma-separated list", () => {
    expect(getClientIdentifier("203.0.113.50, 70.41.3.18, 150.172.238.178")).toBe(
      "203.0.113.50"
    );
  });

  it("trims whitespace from IP", () => {
    expect(getClientIdentifier("  192.168.1.1  ")).toBe("192.168.1.1");
  });

  it("handles empty string", () => {
    expect(getClientIdentifier("")).toBe("unknown");
  });

  it("handles whitespace-only string", () => {
    expect(getClientIdentifier("   ")).toBe("unknown");
  });

  it("returns fallback for comma-only string", () => {
    expect(getClientIdentifier(",,,")).toBe("unknown");
  });
});

describe("getRateLimitForTier", () => {
  it("returns free tier config", () => {
    expect(getRateLimitForTier("free")).toEqual(RATE_LIMITS.free);
  });

  it("returns pro tier config", () => {
    expect(getRateLimitForTier("pro")).toEqual(RATE_LIMITS.pro);
  });

  it("returns enterprise tier config", () => {
    expect(getRateLimitForTier("enterprise")).toEqual(RATE_LIMITS.enterprise);
  });

  it("returns default for unknown tier", () => {
    expect(getRateLimitForTier("unknown")).toEqual(RATE_LIMITS.default);
  });

  it("returns default for empty string", () => {
    expect(getRateLimitForTier("")).toEqual(RATE_LIMITS.default);
  });
});

describe("checkRateLimit", () => {
  let store: Map<string, RateLimitRecord>;
  const limit = { requests: 3, windowMs: 1000 };
  const now = 1000000;

  beforeEach(() => {
    store = new Map();
  });

  it("allows first request and creates record", () => {
    const result = checkRateLimit(store, "client1", limit, now);

    expect(result.limited).toBe(false);
    expect(result.remaining).toBe(2); // 3 - 1 = 2
    expect(store.has("client1")).toBe(true);
    expect(store.get("client1")?.count).toBe(1);
  });

  it("allows requests up to limit", () => {
    // First request
    checkRateLimit(store, "client1", limit, now);
    expect(store.get("client1")?.count).toBe(1);

    // Second request
    checkRateLimit(store, "client1", limit, now + 100);
    expect(store.get("client1")?.count).toBe(2);

    // Third request (at limit)
    const result = checkRateLimit(store, "client1", limit, now + 200);
    expect(result.limited).toBe(false);
    expect(result.remaining).toBe(0);
    expect(store.get("client1")?.count).toBe(3);
  });

  it("blocks requests over limit", () => {
    // Fill up the limit
    checkRateLimit(store, "client1", limit, now);
    checkRateLimit(store, "client1", limit, now + 100);
    checkRateLimit(store, "client1", limit, now + 200);

    // Fourth request should be blocked
    const result = checkRateLimit(store, "client1", limit, now + 300);
    expect(result.limited).toBe(true);
    expect(result.remaining).toBe(0);
  });

  it("returns correct resetIn when blocked", () => {
    checkRateLimit(store, "client1", limit, now);
    checkRateLimit(store, "client1", limit, now);
    checkRateLimit(store, "client1", limit, now);

    // 500ms into the 1000ms window
    const result = checkRateLimit(store, "client1", limit, now + 500);
    expect(result.limited).toBe(true);
    // resetIn should be ~0.5 seconds (500ms remaining / 1000 = 0.5, rounded up = 1)
    expect(result.resetIn).toBe(1);
  });

  it("resets after window expires", () => {
    // Fill up the limit
    checkRateLimit(store, "client1", limit, now);
    checkRateLimit(store, "client1", limit, now);
    checkRateLimit(store, "client1", limit, now);

    // Verify blocked
    const blocked = checkRateLimit(store, "client1", limit, now + 500);
    expect(blocked.limited).toBe(true);

    // After window expires (1001ms later), should allow again
    const result = checkRateLimit(store, "client1", limit, now + 1001);
    expect(result.limited).toBe(false);
    expect(result.remaining).toBe(2);
    expect(store.get("client1")?.count).toBe(1);
  });

  it("tracks different clients independently", () => {
    // Client 1 uses up limit
    checkRateLimit(store, "client1", limit, now);
    checkRateLimit(store, "client1", limit, now);
    checkRateLimit(store, "client1", limit, now);
    const client1 = checkRateLimit(store, "client1", limit, now);
    expect(client1.limited).toBe(true);

    // Client 2 should still be allowed
    const client2 = checkRateLimit(store, "client2", limit, now);
    expect(client2.limited).toBe(false);
    expect(client2.remaining).toBe(2);
  });

  it("returns remaining correctly as count increases", () => {
    const r1 = checkRateLimit(store, "client1", limit, now);
    expect(r1.remaining).toBe(2);

    const r2 = checkRateLimit(store, "client1", limit, now);
    expect(r2.remaining).toBe(1);

    const r3 = checkRateLimit(store, "client1", limit, now);
    expect(r3.remaining).toBe(0);
  });

  it("handles limit of 1 request", () => {
    const strictLimit = { requests: 1, windowMs: 1000 };

    const r1 = checkRateLimit(store, "client1", strictLimit, now);
    expect(r1.limited).toBe(false);
    expect(r1.remaining).toBe(0);

    const r2 = checkRateLimit(store, "client1", strictLimit, now + 100);
    expect(r2.limited).toBe(true);
  });

  it("handles very large windows", () => {
    const hourLimit = { requests: 100, windowMs: 3600000 }; // 1 hour

    const result = checkRateLimit(store, "client1", hourLimit, now);
    expect(result.limited).toBe(false);
    expect(result.resetIn).toBe(3600); // 1 hour in seconds
  });
});

describe("cleanupExpiredEntries", () => {
  let store: Map<string, RateLimitRecord>;
  const now = 1000000;

  beforeEach(() => {
    store = new Map();
  });

  it("removes expired entries", () => {
    store.set("expired", { count: 5, resetTime: now - 1000 });
    store.set("valid", { count: 3, resetTime: now + 1000 });

    const cleaned = cleanupExpiredEntries(store, now);

    expect(cleaned).toBe(1);
    expect(store.has("expired")).toBe(false);
    expect(store.has("valid")).toBe(true);
  });

  it("keeps entries that expire exactly at now", () => {
    store.set("boundary", { count: 5, resetTime: now });

    const cleaned = cleanupExpiredEntries(store, now);

    expect(cleaned).toBe(0);
    expect(store.has("boundary")).toBe(true);
  });

  it("handles empty store", () => {
    const cleaned = cleanupExpiredEntries(store, now);
    expect(cleaned).toBe(0);
  });

  it("removes all entries when all expired", () => {
    store.set("a", { count: 1, resetTime: now - 100 });
    store.set("b", { count: 2, resetTime: now - 200 });
    store.set("c", { count: 3, resetTime: now - 300 });

    const cleaned = cleanupExpiredEntries(store, now);

    expect(cleaned).toBe(3);
    expect(store.size).toBe(0);
  });

  it("keeps all entries when none expired", () => {
    store.set("a", { count: 1, resetTime: now + 100 });
    store.set("b", { count: 2, resetTime: now + 200 });
    store.set("c", { count: 3, resetTime: now + 300 });

    const cleaned = cleanupExpiredEntries(store, now);

    expect(cleaned).toBe(0);
    expect(store.size).toBe(3);
  });
});
