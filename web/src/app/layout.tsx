import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "EdgeSignals - AI News → Prediction Market Edge",
  description: "Real-time AI news monitoring for prediction market traders. Get actionable signals before prices adjust.",
  keywords: ["prediction markets", "polymarket", "kalshi", "AI trading", "trading signals", "market intelligence"],
  openGraph: {
    title: "EdgeSignals - AI News → Prediction Market Edge",
    description: "Real-time AI news monitoring for prediction market traders. Get actionable signals before prices adjust.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "EdgeSignals - AI News → Prediction Market Edge",
    description: "Real-time AI news monitoring for prediction market traders.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-black`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
