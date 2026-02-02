// Rate limiting logic - extracted for testability

export interface RateLimitConfig {
  requests: number;
  windowMs: number;
}

export interface RateLimitRecord {
  count: number;
  resetTime: number;
}

export interface RateLimitResult {
  limited: boolean;
  remaining: number;
  resetIn: number;
}

// Rate limit configuration by tier
export const RATE_LIMITS: Record<string, RateLimitConfig> = {
  free: { requests: 10, windowMs: 60000 }, // 10 req/min for free users
  pro: { requests: 100, windowMs: 60000 }, // 100 req/min for pro
  enterprise: { requests: 1000, windowMs: 60000 }, // 1000 req/min for enterprise
  default: { requests: 20, windowMs: 60000 }, // 20 req/min for unauthenticated
};

/**
 * Extract client IP from headers (supports X-Forwarded-For proxy header)
 */
export function getClientIdentifier(
  forwardedFor: string | null,
  fallback: string = "unknown"
): string {
  if (!forwardedFor) return fallback;
  // X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
  // The first one is the original client
  const firstIp = forwardedFor.split(",")[0].trim();
  return firstIp || fallback;
}

/**
 * Check if a request should be rate limited
 * @param store - The rate limit storage map
 * @param identifier - Client identifier (usually IP)
 * @param limit - Rate limit configuration
 * @param now - Current timestamp (injectable for testing)
 */
export function checkRateLimit(
  store: Map<string, RateLimitRecord>,
  identifier: string,
  limit: RateLimitConfig,
  now: number = Date.now()
): RateLimitResult {
  const record = store.get(identifier);

  // No record or window expired - start fresh
  if (!record || now > record.resetTime) {
    store.set(identifier, { count: 1, resetTime: now + limit.windowMs });
    return {
      limited: false,
      remaining: limit.requests - 1,
      resetIn: Math.ceil(limit.windowMs / 1000),
    };
  }

  // Check if limit exceeded
  if (record.count >= limit.requests) {
    return {
      limited: true,
      remaining: 0,
      resetIn: Math.ceil((record.resetTime - now) / 1000),
    };
  }

  // Increment count
  record.count++;
  return {
    limited: false,
    remaining: limit.requests - record.count,
    resetIn: Math.ceil((record.resetTime - now) / 1000),
  };
}

/**
 * Clean up expired entries from the rate limit store
 */
export function cleanupExpiredEntries(
  store: Map<string, RateLimitRecord>,
  now: number = Date.now()
): number {
  let cleaned = 0;
  for (const [key, value] of store.entries()) {
    if (now > value.resetTime) {
      store.delete(key);
      cleaned++;
    }
  }
  return cleaned;
}

/**
 * Get rate limit config for a tier
 */
export function getRateLimitForTier(tier: string): RateLimitConfig {
  return RATE_LIMITS[tier] || RATE_LIMITS.default;
}
