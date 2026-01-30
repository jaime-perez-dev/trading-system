import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import fs from "fs/promises";
import path from "path";

const WEBHOOK_SECRET = process.env.DODO_PAYMENTS_WEBHOOK_SECRET || "";
const SUBSCRIBERS_FILE = path.join(process.cwd(), "..", "data", "subscribers.json");

interface Subscriber {
  id: string;
  email: string;
  plan: string;
  dodoCustomerId: string;
  dodoSubscriptionId: string;
  dodoPaymentId: string;
  status: string;
  productId: string;
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

function verifySignature(payload: string, signature: string, timestamp: string): boolean {
  if (!WEBHOOK_SECRET) {
    console.warn("No webhook secret configured - skipping verification");
    return true;
  }

  // Dodo Payments signature format: "v1,<base64_signature>"
  const signedPayload = `${timestamp}.${payload}`;
  const expectedSignature = crypto
    .createHmac("sha256", WEBHOOK_SECRET)
    .update(signedPayload)
    .digest("base64");

  // Extract signature from "v1,signature" format
  const providedSig = signature.split(",")[1] || "";

  try {
    return crypto.timingSafeEqual(
      Buffer.from(expectedSignature),
      Buffer.from(providedSig)
    );
  } catch {
    return false;
  }
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  const signature = request.headers.get("webhook-signature") || "";
  const timestamp = request.headers.get("webhook-timestamp") || "";
  const webhookId = request.headers.get("webhook-id") || "";

  // Verify signature
  if (WEBHOOK_SECRET && !verifySignature(body, signature, timestamp)) {
    console.error("Invalid webhook signature");
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  // Check timestamp to prevent replay attacks (5 minute tolerance)
  if (timestamp) {
    const eventTime = parseInt(timestamp) * 1000;
    if (Math.abs(Date.now() - eventTime) > 300000) {
      console.error("Webhook timestamp too old");
      return NextResponse.json({ error: "Timestamp too old" }, { status: 401 });
    }
  }

  try {
    const event = JSON.parse(body);
    const eventType = event.type;
    const data = event.data || {};

    console.log(`Dodo Payments webhook: ${eventType}`, { webhookId, businessId: event.business_id });

    switch (eventType) {
      case "payment.succeeded": {
        // Payment completed successfully
        const subscribers = await getSubscribers();
        const customer = data.customer || {};
        const metadata = data.metadata || {};

        const newSubscriber: Subscriber = {
          id: webhookId || data.payment_id,
          email: customer.email || "",
          plan: metadata.plan || "pro",
          dodoCustomerId: customer.customer_id || "",
          dodoSubscriptionId: data.subscription_id || "",
          dodoPaymentId: data.payment_id || "",
          status: "active",
          productId: data.product_id || "",
          productName: data.product_name || "",
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
        console.log(`Payment succeeded: ${newSubscriber.email} - ${newSubscriber.plan}`);
        break;
      }

      case "payment.failed": {
        // Payment attempt failed
        const customer = data.customer || {};
        console.log(`Payment failed for ${customer.email}: ${data.error_message || "Unknown error"}`);
        break;
      }

      case "subscription.active": {
        // Subscription is now active
        const subscribers = await getSubscribers();
        const customer = data.customer || {};
        const metadata = data.metadata || {};

        const newSubscriber: Subscriber = {
          id: data.subscription_id,
          email: customer.email || "",
          plan: metadata.plan || "pro",
          dodoCustomerId: customer.customer_id || "",
          dodoSubscriptionId: data.subscription_id || "",
          dodoPaymentId: "",
          status: "active",
          productId: data.product_id || "",
          productName: data.product_name || "",
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
            dodoSubscriptionId: data.subscription_id,
            status: "active",
            updatedAt: new Date().toISOString(),
          };
        } else {
          subscribers.push(newSubscriber);
        }

        await saveSubscribers(subscribers);
        console.log(`Subscription active: ${newSubscriber.email} - ${newSubscriber.plan}`);
        break;
      }

      case "subscription.updated":
      case "subscription.plan_changed": {
        // Subscription changed (plan change, update, etc)
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.dodoSubscriptionId === data.subscription_id
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = data.status || subscribers[subIndex].status;
          subscribers[subIndex].productId = data.product_id || subscribers[subIndex].productId;
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription updated: ${subscribers[subIndex].email} - status: ${data.status}`);
        }
        break;
      }

      case "subscription.cancelled":
      case "subscription.expired": {
        // Subscription ended
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.dodoSubscriptionId === data.subscription_id
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = "canceled";
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription ${eventType}: ${subscribers[subIndex].email}`);
        }
        break;
      }

      case "subscription.renewed": {
        // Subscription renewed successfully
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.dodoSubscriptionId === data.subscription_id
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = "active";
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription renewed: ${subscribers[subIndex].email}`);
        }
        break;
      }

      case "subscription.on_hold":
      case "subscription.failed": {
        // Subscription payment failed or on hold
        const subscribers = await getSubscribers();
        const subIndex = subscribers.findIndex(
          (s) => s.dodoSubscriptionId === data.subscription_id
        );

        if (subIndex >= 0) {
          subscribers[subIndex].status = eventType === "subscription.on_hold" ? "past_due" : "failed";
          subscribers[subIndex].updatedAt = new Date().toISOString();
          await saveSubscribers(subscribers);
          console.log(`Subscription ${eventType}: ${subscribers[subIndex].email}`);
        }
        break;
      }

      case "refund.succeeded": {
        // Refund processed
        console.log(`Refund succeeded: ${data.refund_id} for payment ${data.payment_id}`);
        break;
      }

      case "dispute.opened": {
        // Dispute received
        console.log(`Dispute opened: ${data.dispute_id} for payment ${data.payment_id}`);
        break;
      }

      default:
        console.log(`Unhandled Dodo Payments event: ${eventType}`);
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
