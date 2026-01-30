"use client";

import { useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// Example alerts - these would come from API in production
const exampleAlerts = [
  {
    id: 1,
    date: "2026-01-28 14:32",
    headline: "OpenAI announces ads coming to ChatGPT",
    market: "ChatGPT Ads by Mar 31",
    sentiment: "BULLISH",
    confidence: "HIGH",
    marketSentiment: "72%",
    currentSentiment: "96%",
    change: "+24%",
  },
  {
    id: 2,
    date: "2026-01-27 09:15",
    headline: "Google DeepMind announces Gemini 2.5 release",
    market: "Gemini 2.5 by Feb 28",
    sentiment: "BULLISH",
    confidence: "MEDIUM",
    marketSentiment: "45%",
    currentSentiment: "68%",
    change: "+23%",
  },
  {
    id: 3,
    date: "2026-01-26 16:45",
    headline: "Anthropic raises $2B Series D",
    market: "Anthropic $100B by Q2",
    sentiment: "BULLISH",
    confidence: "HIGH",
    marketSentiment: "31%",
    currentSentiment: "47%",
    change: "+16%",
  },
];

export default function LandingPage() {
  const { data: session, status } = useSession();
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  const handleCheckout = async (plan: "pro" | "enterprise") => {
    setCheckoutLoading(plan);
    try {
      const response = await fetch("/api/dodo/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan, email: email || undefined }),
      });
      
      const data = await response.json();
      
      if (data.waitlist) {
        // Payment not configured yet - redirect to waitlist
        alert("Payment coming soon! Join the waitlist below.");
        setCheckoutLoading(null);
        return;
      }
      
      if (data.url) {
        window.location.href = data.url;
      } else {
        console.error("No checkout URL returned");
      }
    } catch (error) {
      console.error("Checkout error:", error);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      
      if (response.ok) {
        setSubmitted(true);
        setEmail("");
      }
    } catch (error) {
      console.error("Failed to join waitlist:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation */}
      <nav className="border-b border-zinc-800 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600" />
            <span className="text-xl font-bold">EdgeSignals</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="/track-record" className="text-zinc-400 hover:text-white transition-colors">
              Analysis History
            </a>
            <a href="/dashboard" className="text-zinc-400 hover:text-white transition-colors">
              Dashboard
            </a>
            {status === "authenticated" ? (
              <Button 
                variant="outline" 
                className="border-zinc-700 hover:bg-zinc-800"
                onClick={() => signOut({ callbackUrl: "/" })}
              >
                Sign Out
              </Button>
            ) : (
              <Button variant="outline" className="border-zinc-700 hover:bg-zinc-800" asChild>
                <a href="/auth/signin">Sign In</a>
              </Button>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <Badge variant="secondary" className="mb-6 bg-blue-500/10 text-blue-400 border-blue-500/20">
            🚀 Early Access — First 100 users get 50% off
          </Badge>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6">
            AI News → <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">Real-Time Intelligence</span>
          </h1>
          <p className="text-xl text-zinc-400 mb-8 max-w-2xl mx-auto">
            We monitor 50+ AI news sources in real-time and analyze how events 
            <strong className="text-white"> impact market sentiment</strong>. 
            Stay informed about Polymarket, Kalshi, and information markets.
          </p>
          
          {/* Waitlist Form */}
          {!submitted ? (
            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-zinc-900 border-zinc-700 text-white placeholder:text-zinc-500"
              />
              <Button 
                type="submit" 
                disabled={isSubmitting}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
              >
                {isSubmitting ? "Joining..." : "Join Waitlist"}
              </Button>
            </form>
          ) : (
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 max-w-md mx-auto">
              <p className="text-green-400">✓ You&apos;re on the list! We&apos;ll notify you when we launch.</p>
            </div>
          )}
          
          <p className="text-sm text-zinc-500 mt-4">
            No spam, ever. Unsubscribe anytime.
          </p>
        </div>
      </section>

      {/* Stats Section */}
      <section className="px-6 py-12 border-y border-zinc-800 bg-zinc-900/50">
        <div className="mx-auto max-w-4xl grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <div className="text-3xl font-bold text-blue-400">50+</div>
            <div className="text-sm text-zinc-500">News Sources Monitored</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-400">24/7</div>
            <div className="text-sm text-zinc-500">Real-Time Analysis</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-400">23</div>
            <div className="text-sm text-zinc-500">AI Topics Tracked</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-orange-400">&lt;5min</div>
            <div className="text-sm text-zinc-500">Avg Alert Latency</div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center mb-4">
                  <span className="text-2xl">📰</span>
                </div>
                <CardTitle className="text-white">1. AI News Monitoring</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-zinc-400">
                  We scan 50+ sources in real-time: TechCrunch, The Verge, official blogs, 
                  Twitter/X, and more. Our AI filters for significant AI industry events.
                </CardDescription>
              </CardContent>
            </Card>
            
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-purple-500/10 flex items-center justify-center mb-4">
                  <span className="text-2xl">🔍</span>
                </div>
                <CardTitle className="text-white">2. Sentiment Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-zinc-400">
                  Our system analyzes how news might impact public sentiment on information markets. 
                  We calculate confidence levels based on historical patterns.
                </CardDescription>
              </CardContent>
            </Card>
            
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-green-500/10 flex items-center justify-center mb-4">
                  <span className="text-2xl">🔔</span>
                </div>
                <CardTitle className="text-white">3. Instant Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-zinc-400">
                  Premium subscribers get real-time alerts via Telegram, email, or API. 
                  Free tier gets delayed alerts (15-min delay).
                </CardDescription>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Recent Alerts */}
      <section className="px-6 py-20 bg-zinc-900/50">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <Badge variant="secondary" className="mb-4 bg-green-500/10 text-green-400 border-green-500/20">
              News Intelligence
            </Badge>
            <h2 className="text-3xl font-bold">Recent Alerts</h2>
            <p className="text-zinc-400 mt-2">Sample analysis from our monitoring system</p>
          </div>
          
          <div className="space-y-4">
            {exampleAlerts.map((alert) => (
              <Card key={alert.id} className="bg-zinc-900 border-zinc-800">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge 
                          variant="secondary" 
                          className={alert.confidence === "HIGH" 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                          }
                        >
                          {alert.confidence} CONFIDENCE
                        </Badge>
                        <span className="text-sm text-zinc-500">{alert.date}</span>
                      </div>
                      <h3 className="font-semibold text-white mb-1">{alert.headline}</h3>
                      <p className="text-sm text-zinc-400">Related Market: {alert.market}</p>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-center">
                        <div className="text-sm text-zinc-500">Sentiment</div>
                        <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                          {alert.sentiment}
                        </Badge>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-zinc-500">At Alert</div>
                        <div className="font-mono text-white">{alert.marketSentiment}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-zinc-500">Current</div>
                        <div className="font-mono text-white">{alert.currentSentiment}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-zinc-500">Change</div>
                        <div className="font-mono text-green-400 font-bold">{alert.change}</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          
          <div className="text-center mt-8">
            <Button variant="outline" className="border-zinc-700 hover:bg-zinc-800" asChild>
              <a href="/dashboard">View All Alerts →</a>
            </Button>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold">Simple Pricing</h2>
            <p className="text-zinc-400 mt-2">Choose the plan that fits your research needs</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {/* Free Tier */}
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-white">Free</CardTitle>
                <CardDescription className="text-zinc-400">
                  Get started with delayed alerts
                </CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold text-white">$0</span>
                  <span className="text-zinc-500">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-sm text-zinc-400">
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> 15-min delayed alerts
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Email notifications
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Dashboard access
                  </li>
                  <li className="flex items-center gap-2 text-zinc-600">
                    <span>✗</span> Real-time alerts
                  </li>
                  <li className="flex items-center gap-2 text-zinc-600">
                    <span>✗</span> Telegram notifications
                  </li>
                  <li className="flex items-center gap-2 text-zinc-600">
                    <span>✗</span> API access
                  </li>
                </ul>
                <Separator className="my-6 bg-zinc-800" />
                <Button variant="outline" className="w-full border-zinc-700 hover:bg-zinc-800" asChild>
                  <a href="/dashboard">Get Started Free</a>
                </Button>
              </CardContent>
            </Card>

            {/* Pro Tier */}
            <Card className="bg-gradient-to-b from-blue-500/10 to-purple-500/10 border-blue-500/30 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge className="bg-gradient-to-r from-blue-500 to-purple-600">
                  Most Popular
                </Badge>
              </div>
              <CardHeader>
                <CardTitle className="text-white">Pro</CardTitle>
                <CardDescription className="text-zinc-400">
                  Stay informed first with real-time alerts
                </CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold text-white">$49</span>
                  <span className="text-zinc-500">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-sm text-zinc-400">
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> <strong className="text-white">Real-time alerts</strong>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> <strong className="text-white">Telegram notifications</strong>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Email notifications
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Dashboard access
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Priority support
                  </li>
                  <li className="flex items-center gap-2 text-zinc-600">
                    <span>✗</span> API access
                  </li>
                </ul>
                <Separator className="my-6 bg-zinc-800" />
                <Button 
                  className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                  onClick={() => handleCheckout("pro")}
                  disabled={checkoutLoading === "pro"}
                >
                  {checkoutLoading === "pro" ? "Processing..." : "Get Pro Access"}
                </Button>
              </CardContent>
            </Card>

            {/* Enterprise Tier */}
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-white">Enterprise</CardTitle>
                <CardDescription className="text-zinc-400">
                  Full API access for developers
                </CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold text-white">$299</span>
                  <span className="text-zinc-500">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-sm text-zinc-400">
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Everything in Pro
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> <strong className="text-white">Full API access</strong>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> <strong className="text-white">Webhook integrations</strong>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Custom alert rules
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Historical data export
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span> Dedicated support
                  </li>
                </ul>
                <Separator className="my-6 bg-zinc-800" />
                <Button 
                  variant="outline" 
                  className="w-full border-zinc-700 hover:bg-zinc-800"
                  onClick={() => handleCheckout("enterprise")}
                  disabled={checkoutLoading === "enterprise"}
                >
                  {checkoutLoading === "enterprise" ? "Processing..." : "Get Enterprise Access"}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-6 py-20 bg-gradient-to-b from-zinc-900 to-black">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to stay informed?</h2>
          <p className="text-zinc-400 mb-8">
            Join 100+ researchers already on the waitlist. Be first to access 
            real-time AI news intelligence when we launch.
          </p>
          {!submitted ? (
            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-zinc-900 border-zinc-700 text-white placeholder:text-zinc-500"
              />
              <Button 
                type="submit" 
                disabled={isSubmitting}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
              >
                {isSubmitting ? "Joining..." : "Join Waitlist"}
              </Button>
            </form>
          ) : (
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 max-w-md mx-auto">
              <p className="text-green-400">✓ You&apos;re on the list!</p>
            </div>
          )}
        </div>
      </section>

      {/* Disclaimer */}
      <section className="px-6 py-8 bg-zinc-950">
        <div className="mx-auto max-w-4xl text-center">
          <p className="text-xs text-zinc-600 leading-relaxed">
            <strong>Disclaimer:</strong> EdgeSignals is an information service that provides news analysis and market sentiment data for research purposes only. 
            This is not financial advice, investment advice, or a recommendation to buy, sell, or hold any securities or participate in any markets. 
            All information is provided &quot;as is&quot; without warranty. Past performance does not guarantee future results. 
            Users should conduct their own research and consult with qualified professionals before making any decisions.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 px-6 py-8">
        <div className="mx-auto max-w-6xl flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600" />
            <span className="font-bold">EdgeSignals</span>
          </div>
          <p className="text-sm text-zinc-500">
            © 2026 EdgeSignals. AI News Intelligence Service.
          </p>
          <div className="flex gap-4 text-sm text-zinc-500">
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
