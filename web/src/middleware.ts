import { NextRequest, NextResponse } from "next/server";
import {
  checkRateLimit,
  cleanupExpiredEntries,
  getClientIdentifier,
  getRateLimitForTier,
  RateLimitRecord,
} from "./lib/rate-limit";

// Simple in-memory rate limiting (consider Redis for production multi-instance)
const rateLimitMap = new Map<string, RateLimitRecord>();

// Cleanup old entries periodically
setInterval(() => {
  cleanupExpiredEntries(rateLimitMap);
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

  const forwardedFor = request.headers.get("x-forwarded-for");
  const identifier = getClientIdentifier(forwardedFor);

  // TODO: Get user tier from session when auth is fully implemented
  // For now, use default limits
  const limit = getRateLimitForTier("default");

  const { limited, remaining, resetIn } = checkRateLimit(
    rateLimitMap,
    identifier,
    limit
  );

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
