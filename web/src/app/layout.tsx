import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import { Analytics } from "@/components/analytics";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://edgesignals.ai";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#10b981",
};

export const metadata: Metadata = {
  metadataBase: new URL(baseUrl),
  title: {
    default: "EdgeSignals - AI News Intelligence for Prediction Markets",
    template: "%s | EdgeSignals",
  },
  description:
    "Real-time AI news monitoring for prediction market research. Get actionable insights from 50+ sources before sentiment shifts. Track AI industry developments with precision.",
  keywords: [
    "prediction markets",
    "polymarket",
    "kalshi",
    "AI news",
    "trading signals",
    "market intelligence",
    "sentiment analysis",
    "news monitoring",
    "AI research",
    "market research",
  ],
  authors: [{ name: "EdgeSignals" }],
  creator: "EdgeSignals",
  publisher: "EdgeSignals",
  formatDetection: {
    email: false,
    telephone: false,
    address: false,
  },
  openGraph: {
    type: "website",
    siteName: "EdgeSignals",
    title: "EdgeSignals - AI News Intelligence for Prediction Markets",
    description:
      "Real-time AI news monitoring for prediction market research. Get actionable insights from 50+ sources.",
    url: baseUrl,
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "EdgeSignals - AI News Intelligence",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "EdgeSignals - AI News Intelligence for Prediction Markets",
    description:
      "Real-time AI news monitoring for prediction market research. Track AI developments with precision.",
    images: ["/og-image.png"],
    creator: "@JaimeBuildsAI",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  alternates: {
    canonical: baseUrl,
    types: {
      "application/rss+xml": [{ url: "/api/feed", title: "EdgeSignals RSS Feed" }],
    },
  },
  category: "technology",
};

// JSON-LD structured data
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "EdgeSignals",
  description:
    "AI-powered news intelligence service for prediction market research",
  url: baseUrl,
  applicationCategory: "BusinessApplication",
  operatingSystem: "Any",
  offers: [
    {
      "@type": "Offer",
      name: "Free Tier",
      price: "0",
      priceCurrency: "USD",
      description: "15-minute delayed alerts",
    },
    {
      "@type": "Offer",
      name: "Pro",
      price: "49",
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        price: "49",
        priceCurrency: "USD",
        billingDuration: "P1M",
      },
      description: "Real-time alerts + Telegram notifications",
    },
    {
      "@type": "Offer",
      name: "Enterprise",
      price: "299",
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        price: "299",
        priceCurrency: "USD",
        billingDuration: "P1M",
      },
      description: "Full API access + webhooks + priority support",
    },
  ],
  creator: {
    "@type": "Organization",
    name: "EdgeSignals",
    url: baseUrl,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-black`}
      >
        <Providers>{children}</Providers>
        <Analytics />
      </body>
    </html>
  );
}
