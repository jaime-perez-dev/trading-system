import { NextRequest, NextResponse } from "next/server";

// Simple in-memory rate limiting (consider Redis for production multi-instance)
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();

// Rate limit configuration by tier
const RATE_LIMITS = {
  free: { requests: 10, windowMs: 60000 }, // 10 req/min for free users
  pro: { requests: 100, windowMs: 60000 }, // 100 req/min for pro
  enterprise: { requests: 1000, windowMs: 60000 }, // 1000 req/min for enterprise
  default: { requests: 20, windowMs: 60000 }, // 20 req/min for unauthenticated
};

function getClientIdentifier(request: NextRequest): string {
  // Use IP as identifier, falling back to a generic key
  const forwarded = request.headers.get("x-forwarded-for");
  const ip = forwarded ? forwarded.split(",")[0].trim() : "unknown";
  return ip;
}

function isRateLimited(
  identifier: string,
  limit: { requests: number; windowMs: number }
): { limited: boolean; remaining: number; resetIn: number } {
  const now = Date.now();
  const record = rateLimitMap.get(identifier);

  if (!record || now > record.resetTime) {
    // Start new window
    rateLimitMap.set(identifier, { count: 1, resetTime: now + limit.windowMs });
    return { limited: false, remaining: limit.requests - 1, resetIn: limit.windowMs };
  }

  if (record.count >= limit.requests) {
    return {
      limited: true,
      remaining: 0,
      resetIn: Math.ceil((record.resetTime - now) / 1000),
    };
  }

  record.count++;
  return {
    limited: false,
    remaining: limit.requests - record.count,
    resetIn: Math.ceil((record.resetTime - now) / 1000),
  };
}

// Cleanup old entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of rateLimitMap.entries()) {
    if (now > value.resetTime) {
      rateLimitMap.delete(key);
    }
  }
}, 60000); // Clean every minute

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only rate limit API routes (except health check)
  if (!pathname.startsWith("/api") || pathname === "/api/health") {
    return NextResponse.next();
  }

  // Skip rate limiting for auth endpoints
  if (pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  const identifier = getClientIdentifier(request);
  
  // TODO: Get user tier from session when auth is fully implemented
  // For now, use default limits
  const limit = RATE_LIMITS.default;
  
  const { limited, remaining, resetIn } = isRateLimited(identifier, limit);

  if (limited) {
    return new NextResponse(
      JSON.stringify({
        error: "Rate limit exceeded",
        message: `Too many requests. Please retry in ${resetIn} seconds.`,
        retryAfter: resetIn,
      }),
      {
        status: 429,
        headers: {
          "Content-Type": "application/json",
          "Retry-After": String(resetIn),
          "X-RateLimit-Limit": String(limit.requests),
          "X-RateLimit-Remaining": "0",
          "X-RateLimit-Reset": String(resetIn),
        },
      }
    );
  }

  // Add rate limit headers to successful responses
  const response = NextResponse.next();
  response.headers.set("X-RateLimit-Limit", String(limit.requests));
  response.headers.set("X-RateLimit-Remaining", String(remaining));
  response.headers.set("X-RateLimit-Reset", String(resetIn));
  
  return response;
}

export const config = {
  matcher: "/api/:path*",
};
