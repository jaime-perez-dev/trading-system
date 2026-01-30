import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import fs from "fs/promises";
import path from "path";

const WEBHOOK_SECRET = process.env.LEMON_SQUEEZY_WEBHOOK_SECRET || "";
const SUBSCRIBERS_FILE = path.join(process.cwd(), "..", "data", "subscribers.json");

interface Subscriber {
  id: string;
  email: string;
  plan: string;
  lemonSqueezyCustomerId: string;
  lemonSqueezySubscriptionId: string;
  status: string;
  variantId: string;
  productName: string;
  createdAt: string;
  updatedAt: string;
}

async function getSubscribers(): Promise<Subscriber[]> {
  try {
    const data = await fs.readFile(SUBSCRIBERS_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return [];
  }
}

async function saveSubscribers(subscribers: Subscriber[]): Promise<void> {
  await fs.mkdir(path.dirname(SUBSCRIBERS_FILE), { recursive: true });
  await fs.writeFile(SUBSCRIBERS_FILE, JSON.stringify(subscribers, null, 2));
}

function verifySignature(payload: string, signature: string): boolean {
  if (!WEBHOOK_SECRET) {
    console.warn("No webhook secret configured - skipping verification");
    return true;
  }

  const hmac = crypto.createHmac("sha256", WEBHOOK_SECRET);
  const digest = hmac.update(payload).digest("hex");
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(digest)
  );
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  const signature = request.headers.get("x-signature") || "";
  const eventName = request.headers.get("x-event-name") || "";

  // Verify signature
  if (WEBHOOK_SECRET && !verifySignature(body, signature)) {
    console.error("Invalid webhook signature");
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  try {
    const payload = JSON.parse(body);
    const { meta, data } = payload;
    const attributes = data?.attributes || {};

    console.log(`Lemon Squeezy webhook: ${eventName}`, { id: data?.id });

    switch (eventName) {
      case "order_created": {
        // One-time purchase or first subscription order
        const subscribers = await getSubscribers();
        const customData = meta?.custom_data || {};
        
        const newSubscriber: Subscriber = {
          id: data.id,
          email: attributes.user_email || "",
          plan: customData.plan || "pro",
          lemonSqueezyCustomerId: String(attributes.customer_id),
          lemonSqueezySubscriptionId: "", // Will be set by subscription_created
          status: "active",
          variantId: String(attributes.first_order_item?.variant_id || ""),
          productName: attributes.first_order_item?.product_name || "",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        const existingIndex = subscribers.findIndex(
          (s) => s.email === newSubscriber.email
        );

        if (existingIndex >= 0) {
          subscribers[existingIndex] = {
            ...subscribers[existingIndex],
            ...newSubscriber,
            updatedAt: new Date().toISOString(),
          };
        } else {
          subscribers.push(newSubscriber);
        }

        await saveSubscribers(subscribers);
        console.log(`New order: ${newSubscriber.email} - ${newSubscriber.plan}`);
        break;
      }

      case "subscription_created": {
        // New subscription
        const subscribers = await getSubscribers();
        const customData = meta?.custom_data || {};

        const newSubscriber: Subscriber = {
          id: data.id,
          email: attributes.user_email || "",
          plan: customData.plan || "pro",
          lemonSqueezyCustomerId: String(attributes.customer_id),
          lemonSqueezySubscriptionId: String(data.id),
          status: attributes.status || "active",
          variantId: String(attributes.variant_id),
          productName: attributes.product_name || "",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        const existingIndex = subscribers.findIndex(
          (s) => s.email === newSubscriber.email
        );

        if (existingIndex >= 0) {
          subscribers[existingIndex] = {
            ...subscribers[existingIndex],
            ...newSubscriber,
            lemonSqueezySubscriptionId: String(data.id),
            updatedAt: new Date().toISOString(),
          };
        } else {
          subscribers.push(newSubscriber);
        }

        await saveSubscribers(subscribers);
        console.log(`New subscription: ${newSubscriber.email} - ${newSubscriber.plan}`);
        break;
      }

      case "subscription_updated": {
        // Subscription changed (plan change, payment method update, etc)
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.lemonSqueezySubscriptionId === String(data.id)
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = attributes.status || subscribers[subIndex].status;
          subscribers[subIndex].variantId = String(attributes.variant_id);
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription updated: ${subscribers[subIndex].email} - status: ${attributes.status}`);
        }
        break;
      }

      case "subscription_cancelled":
      case "subscription_expired": {
        // Subscription ended
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.lemonSqueezySubscriptionId === String(data.id)
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = "canceled";
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription ${eventName}: ${subscribers[subIndex].email}`);
        }
        break;
      }

      case "subscription_resumed":
      case "subscription_payment_success":
      case "subscription_payment_recovered": {
        // Subscription reactivated or successful payment
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.lemonSqueezySubscriptionId === String(data.id)
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = "active";
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription ${eventName}: ${subscribers[subIndex].email}`);
        }
        break;
      }

      case "subscription_paused": {
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.lemonSqueezySubscriptionId === String(data.id)
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = "paused";
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription paused: ${subscribers[subIndex].email}`);
        }
        break;
      }

      case "subscription_payment_failed": {
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.lemonSqueezySubscriptionId === String(data.id)
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = "past_due";
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Payment failed: ${subscribers[subIndex].email}`);
        }
        break;
      }

      default:
        console.log(`Unhandled Lemon Squeezy event: ${eventName}`);
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error("Webhook processing error:", error);
    return NextResponse.json(
      { error: "Webhook processing failed" },
      { status: 500 }
    );
  }
}
