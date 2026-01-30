import { NextRequest, NextResponse } from "next/server";

// Lemon Squeezy API configuration
const LEMONSQUEEZY_API_URL = "https://api.lemonsqueezy.com/v1";
const API_KEY = process.env.LEMON_SQUEEZY_API_KEY;
const STORE_ID = process.env.LEMON_SQUEEZY_STORE_ID;

// Variant IDs for each plan - set these in your Lemon Squeezy dashboard
const VARIANT_IDS = {
  pro: process.env.LEMON_SQUEEZY_VARIANT_PRO || "",
  enterprise: process.env.LEMON_SQUEEZY_VARIANT_ENTERPRISE || "",
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

    const variantId = VARIANT_IDS[plan as keyof typeof VARIANT_IDS];

    // Check if Lemon Squeezy is configured
    if (!API_KEY || !STORE_ID || !variantId) {
      return NextResponse.json(
        {
          error: "Payment system not configured",
          message: "Payments coming soon! Join the waitlist to be notified.",
          waitlist: true,
        },
        { status: 503 }
      );
    }

    // Create checkout via Lemon Squeezy API
    const response = await fetch(`${LEMONSQUEEZY_API_URL}/checkouts`, {
      method: "POST",
      headers: {
        Accept: "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        Authorization: `Bearer ${API_KEY}`,
      },
      body: JSON.stringify({
        data: {
          type: "checkouts",
          attributes: {
            checkout_data: {
              email: email || undefined,
              custom: {
                user_id: userId || undefined,
                plan,
              },
            },
            checkout_options: {
              embed: false,
              media: true,
              logo: true,
              desc: true,
              discount: true,
              button_color: "#7C3AED", // Purple to match our branding
            },
            product_options: {
              redirect_url: `${request.nextUrl.origin}/dashboard?success=true`,
            },
          },
          relationships: {
            store: {
              data: {
                type: "stores",
                id: STORE_ID,
              },
            },
            variant: {
              data: {
                type: "variants",
                id: variantId,
              },
            },
          },
        },
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Lemon Squeezy API error:", errorData);
      return NextResponse.json(
        { error: "Failed to create checkout" },
        { status: 500 }
      );
    }

    const data = await response.json();
    const checkoutUrl = data.data.attributes.url;

    return NextResponse.json({ url: checkoutUrl });
  } catch (error) {
    console.error("Checkout error:", error);
    return NextResponse.json(
      { error: "Failed to create checkout session" },
      { status: 500 }
    );
  }
}
