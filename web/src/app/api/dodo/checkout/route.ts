import { NextRequest, NextResponse } from "next/server";

// Dodo Payments API configuration
const DODO_API_URL = "https://api.dodopayments.com";
const API_KEY = process.env.DODO_PAYMENTS_API_KEY;

// Product IDs for each plan - set these in your Dodo Payments dashboard
const PRODUCT_IDS = {
  pro: process.env.DODO_PRODUCT_PRO || "",
  enterprise: process.env.DODO_PRODUCT_ENTERPRISE || "",
};

export async function POST(request: NextRequest) {
  try {
    const { plan, email, userId } = await request.json();

    if (!plan || !["pro", "enterprise"].includes(plan)) {
      return NextResponse.json(
        { error: "Invalid plan selected" },
        { status: 400 }
      );
    }

    const productId = PRODUCT_IDS[plan as keyof typeof PRODUCT_IDS];

    // Check if Dodo Payments is configured
    if (!API_KEY || !productId) {
      return NextResponse.json(
        {
          error: "Payment system not configured",
          message: "Payments coming soon! Join the waitlist to be notified.",
          waitlist: true,
        },
        { status: 503 }
      );
    }

    // Create checkout session via Dodo Payments API
    const response = await fetch(`${DODO_API_URL}/checkout_sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${API_KEY}`,
      },
      body: JSON.stringify({
        product_cart: [
          {
            product_id: productId,
            quantity: 1,
          },
        ],
        customer: email
          ? {
              email,
              name: undefined,
            }
          : undefined,
        return_url: `${request.nextUrl.origin}/dashboard?success=true`,
        metadata: {
          user_id: userId || undefined,
          plan,
        },
        feature_flags: {
          allow_discount_code: true,
        },
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Dodo Payments API error:", errorData);
      return NextResponse.json(
        { error: "Failed to create checkout" },
        { status: 500 }
      );
    }

    const data = await response.json();
    const checkoutUrl = data.checkout_url;

    if (!checkoutUrl) {
      console.error("No checkout URL in response:", data);
      return NextResponse.json(
        { error: "Failed to get checkout URL" },
        { status: 500 }
      );
    }

    return NextResponse.json({ url: checkoutUrl, sessionId: data.session_id });
  } catch (error) {
    console.error("Checkout error:", error);
    return NextResponse.json(
      { error: "Failed to create checkout session" },
      { status: 500 }
    );
  }
}
