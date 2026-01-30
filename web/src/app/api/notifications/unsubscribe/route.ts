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
  await fs.writeFile(SUBSCRIPTIONS_FILE, JSON.stringify(store, null, 2));
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { endpoint } = body;

    if (!endpoint) {
      return NextResponse.json(
        { error: "Endpoint required" },
        { status: 400 }
      );
    }

    const store = await readSubscriptions();
    
    const initialLength = store.subscriptions.length;
    store.subscriptions = store.subscriptions.filter(
      (s) => s.endpoint !== endpoint
    );

    if (store.subscriptions.length === initialLength) {
      return NextResponse.json({
        success: true,
        message: "Subscription not found (already removed)",
      });
    }

    await writeSubscriptions(store);

    console.log(`[Push] Subscription removed`);

    return NextResponse.json({
      success: true,
      message: "Subscription removed",
    });
  } catch (error) {
    console.error("[Push] Unsubscribe error:", error);
    return NextResponse.json(
      { error: "Failed to remove subscription" },
      { status: 500 }
    );
  }
}
