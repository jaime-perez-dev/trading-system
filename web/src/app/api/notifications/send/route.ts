import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";
import webpush from "web-push";

const SUBSCRIPTIONS_FILE = path.join(process.cwd(), "..", "data", "push_subscriptions.json");

// VAPID keys should be set in environment variables
const VAPID_SUBJECT = process.env.VAPID_SUBJECT || "mailto:alerts@edgesignals.io";
const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
const VAPID_PRIVATE_KEY = process.env.VAPID_PRIVATE_KEY;

interface PushSubscriptionData {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  userId?: string;
  tier?: string;
  createdAt: string;
  lastActive: string;
}

interface SubscriptionsStore {
  subscriptions: PushSubscriptionData[];
}

interface NotificationPayload {
  title: string;
  body: string;
  icon?: string;
  badge?: string;
  tag?: string;
  data?: Record<string, unknown>;
  // Optional: target specific users
  userIds?: string[];
  tier?: "free" | "pro" | "enterprise";
}

async function readSubscriptions(): Promise<SubscriptionsStore> {
  try {
    const data = await fs.readFile(SUBSCRIPTIONS_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return { subscriptions: [] };
  }
}

async function writeSubscriptions(store: SubscriptionsStore): Promise<void> {
  await fs.writeFile(SUBSCRIPTIONS_FILE, JSON.stringify(store, null, 2));
}

export async function POST(request: NextRequest) {
  // Verify API key for server-to-server calls
  const authHeader = request.headers.get("authorization");
  const apiKey = process.env.NOTIFICATION_API_KEY;
  
  if (apiKey && authHeader !== `Bearer ${apiKey}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!VAPID_PUBLIC_KEY || !VAPID_PRIVATE_KEY) {
    return NextResponse.json(
      { error: "VAPID keys not configured" },
      { status: 500 }
    );
  }

  try {
    webpush.setVapidDetails(VAPID_SUBJECT, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY);

    const payload: NotificationPayload = await request.json();

    if (!payload.title || !payload.body) {
      return NextResponse.json(
        { error: "Title and body required" },
        { status: 400 }
      );
    }

    const store = await readSubscriptions();
    
    // Filter subscriptions by criteria
    let targetSubscriptions = store.subscriptions;
    
    if (payload.userIds && payload.userIds.length > 0) {
      targetSubscriptions = targetSubscriptions.filter(
        (s) => s.userId && payload.userIds?.includes(s.userId)
      );
    }
    
    if (payload.tier) {
      // Only send to subscriptions at or above the specified tier
      const tierPriority = { free: 0, pro: 1, enterprise: 2 };
      const minTier = tierPriority[payload.tier] || 0;
      targetSubscriptions = targetSubscriptions.filter((s) => {
        const subTier = tierPriority[(s.tier as keyof typeof tierPriority) || "free"] || 0;
        return subTier >= minTier;
      });
    }

    const notificationPayload = JSON.stringify({
      title: payload.title,
      body: payload.body,
      icon: payload.icon || "/icon-192.png",
      badge: payload.badge || "/badge-72.png",
      tag: payload.tag || "signal",
      data: payload.data || {},
    });

    const results = await Promise.allSettled(
      targetSubscriptions.map(async (sub) => {
        try {
          await webpush.sendNotification(
            {
              endpoint: sub.endpoint,
              keys: sub.keys,
            },
            notificationPayload
          );
          return { success: true, endpoint: sub.endpoint };
        } catch (error: unknown) {
          // Handle expired subscriptions
          const webPushError = error as { statusCode?: number };
          if (webPushError.statusCode === 410 || webPushError.statusCode === 404) {
            // Remove expired subscription
            store.subscriptions = store.subscriptions.filter(
              (s) => s.endpoint !== sub.endpoint
            );
            return { success: false, endpoint: sub.endpoint, expired: true };
          }
          throw error;
        }
      })
    );

    // Save updated subscriptions (with expired ones removed)
    await writeSubscriptions(store);

    const successful = results.filter(
      (r) => r.status === "fulfilled" && (r.value as { success: boolean }).success
    ).length;
    const failed = results.length - successful;
    const expired = results.filter(
      (r) => r.status === "fulfilled" && (r.value as { expired?: boolean }).expired
    ).length;

    console.log(`[Push] Sent to ${successful}/${targetSubscriptions.length} subscribers (${expired} expired)`);

    return NextResponse.json({
      success: true,
      sent: successful,
      failed,
      expired,
      total: targetSubscriptions.length,
    });
  } catch (error) {
    console.error("[Push] Send error:", error);
    return NextResponse.json(
      { error: "Failed to send notifications" },
      { status: 500 }
    );
  }
}
