import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const SUBSCRIPTIONS_FILE = path.join(process.cwd(), "..", "data", "push_subscriptions.json");

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

async function readSubscriptions(): Promise<SubscriptionsStore> {
  try {
    const data = await fs.readFile(SUBSCRIPTIONS_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return { subscriptions: [] };
  }
}

async function writeSubscriptions(store: SubscriptionsStore): Promise<void> {
  // Ensure data directory exists
  const dataDir = path.dirname(SUBSCRIPTIONS_FILE);
  await fs.mkdir(dataDir, { recursive: true });
  await fs.writeFile(SUBSCRIPTIONS_FILE, JSON.stringify(store, null, 2));
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { subscription, userId, tier } = body;

    if (!subscription?.endpoint || !subscription?.keys) {
      return NextResponse.json(
        { error: "Invalid subscription data" },
        { status: 400 }
      );
    }

    const store = await readSubscriptions();
    
    // Check if subscription already exists (by endpoint)
    const existingIndex = store.subscriptions.findIndex(
      (s) => s.endpoint === subscription.endpoint
    );

    const now = new Date().toISOString();
    const subData: PushSubscriptionData = {
      endpoint: subscription.endpoint,
      keys: subscription.keys,
      userId,
      tier: tier || "pro",
      createdAt: existingIndex >= 0 
        ? store.subscriptions[existingIndex].createdAt 
        : now,
      lastActive: now,
    };

    if (existingIndex >= 0) {
      // Update existing subscription
      store.subscriptions[existingIndex] = subData;
    } else {
      // Add new subscription
      store.subscriptions.push(subData);
    }

    await writeSubscriptions(store);

    console.log(`[Push] Subscription ${existingIndex >= 0 ? "updated" : "created"} for user ${userId || "anonymous"}`);

    return NextResponse.json({
      success: true,
      message: existingIndex >= 0 ? "Subscription updated" : "Subscription created",
    });
  } catch (error) {
    console.error("[Push] Subscribe error:", error);
    return NextResponse.json(
      { error: "Failed to save subscription" },
      { status: 500 }
    );
  }
}
