"use client";

import { useState, useCallback, useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RefreshCw, Wifi, WifiOff, Sparkles } from "lucide-react";
import { useRealTimeSignals, Signal } from "@/hooks/useRealTimeSignals";
import { NotificationToggle } from "@/components/NotificationToggle";
import { showLocalNotification } from "@/lib/notifications";

export default function Dashboard() {
  const { data: session, status } = useSession();
  const [showNewBadge, setShowNewBadge] = useState(false);
  
  // Get tier from session or default to free
  const tier = (session?.user?.tier || "free") as "free" | "pro" | "enterprise";

  // Handle new alert notification
  const handleNewSignal = useCallback((signal: Signal) => {
    setShowNewBadge(true);
    
    // Show browser notification for new alerts
    if (tier !== "free") {
      showLocalNotification(`New Alert: ${signal.signal}`, {
        body: `${signal.headline}\n${signal.market}`,
        tag: `signal-${signal.id}`,
        data: { signalId: signal.id },
      });
    }
    
    // Hide badge after 10 seconds
    setTimeout(() => setShowNewBadge(false), 10000);
  }, [tier]);

  // Real-time alerts hook
  const {
    signals,
    loading,
    error,
    lastUpdate,
    isLive,
    newSignalIds,
    refresh,
    clearNewIndicators,
  } = useRealTimeSignals({
    tier,
    onNewSignal: handleNewSignal,
    enabled: status !== "loading",
  });

  // Filter alerts
  const activeAlerts = signals.filter(s => s.status === "open");
  const resolvedAlerts = signals.filter(s => s.status === "closed");
  const pendingAlerts = signals.filter(s => s.status === "pending");

  // Calculate stats - sentiment change tracking
  const totalChange = signals
    .filter(s => s.pnl)
    .reduce((acc, s) => {
      const changeMatch = s.pnl?.match(/[\-\+]?\$?([\d.]+)%?/);
      const value = changeMatch ? parseFloat(changeMatch[1]) : 0;
      return acc + (s.pnl?.includes("-") ? -value : value);
    }, 0);

  const accurateCount = resolvedAlerts.filter(s => s.pnl && !s.pnl.includes("-")).length;
  const accuracyRate = resolvedAlerts.length > 0 
    ? Math.round((accurateCount / resolvedAlerts.length) * 100) 
    : 0;

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation */}
      <nav className="border-b border-zinc-800 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-4">
            <a href="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600" />
              <span className="text-xl font-bold">EdgeSignals</span>
            </a>
            
            {/* Tier badge */}
            <Badge 
              variant="secondary" 
              className={
                tier === "free" 
                  ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                  : tier === "pro"
                  ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                  : "bg-purple-500/10 text-purple-400 border-purple-500/20"
              }
            >
              {tier === "free" ? "Free (15-min delay)" : tier.toUpperCase()}
            </Badge>
            
            {/* Live indicator */}
            <div className="flex items-center gap-1.5">
              {isLive ? (
                <>
                  <Wifi className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-green-400">Live</span>
                  {showNewBadge && (
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30 animate-pulse">
                      <Sparkles className="h-3 w-3 mr-1" />
                      New
                    </Badge>
                  )}
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-zinc-500" />
                  <span className="text-xs text-zinc-500">Offline</span>
                </>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Push notification toggle */}
            <NotificationToggle 
              tier={tier} 
              userId={session?.user?.id}
            />
            
            {/* Refresh button */}
            <Button 
              variant="outline" 
              size="sm"
              className="gap-2 border-zinc-700 hover:bg-zinc-800"
              onClick={() => refresh()}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </Button>
            
            {session?.user?.email && (
              <span className="text-sm text-zinc-400 hidden md:block">{session.user.email}</span>
            )}
            
            {tier === "free" && (
              <Button variant="outline" className="border-zinc-700 hover:bg-zinc-800" asChild>
                <a href="/#pricing">Upgrade</a>
              </Button>
            )}
            
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
                <a href="/login">Sign In</a>
              </Button>
            )}
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {/* Error banner */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
            Failed to load alerts: {error}. Using cached data.
          </div>
        )}
        
        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Sentiment Change</CardDescription>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${totalChange >= 0 ? "text-green-400" : "text-red-400"}`}>
                {totalChange >= 0 ? "+" : ""}{totalChange.toFixed(1)}%
              </div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Analysis Accuracy</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-400">{accuracyRate}%</div>
              <div className="text-sm text-zinc-500">{accurateCount}/{resolvedAlerts.length} resolved</div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Active Alerts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-400">{activeAlerts.length}</div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Last Update</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-zinc-400">
                {lastUpdate ? lastUpdate.toLocaleTimeString() : "—"}
              </div>
              {tier === "free" && (
                <div className="text-sm text-yellow-500">15-min delay</div>
              )}
              {tier !== "free" && (
                <div className="text-sm text-green-500">Real-time (10s)</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Alerts Tabs */}
        <Tabs defaultValue="all" className="space-y-4" onValueChange={() => clearNewIndicators()}>
          <TabsList className="bg-zinc-900 border border-zinc-800">
            <TabsTrigger value="all" className="data-[state=active]:bg-zinc-800">
              All Alerts ({signals.length})
            </TabsTrigger>
            <TabsTrigger value="active" className="data-[state=active]:bg-zinc-800">
              Active ({activeAlerts.length})
            </TabsTrigger>
            <TabsTrigger value="resolved" className="data-[state=active]:bg-zinc-800">
              Resolved ({resolvedAlerts.length})
            </TabsTrigger>
            {pendingAlerts.length > 0 && (
              <TabsTrigger value="pending" className="data-[state=active]:bg-zinc-800">
                Pending ({pendingAlerts.length})
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="all">
            <AlertsTable alerts={signals} loading={loading} tier={tier} newAlertIds={newSignalIds} />
          </TabsContent>
          <TabsContent value="active">
            <AlertsTable alerts={activeAlerts} loading={loading} tier={tier} newAlertIds={newSignalIds} />
          </TabsContent>
          <TabsContent value="resolved">
            <AlertsTable alerts={resolvedAlerts} loading={loading} tier={tier} newAlertIds={newSignalIds} />
          </TabsContent>
          <TabsContent value="pending">
            <AlertsTable alerts={pendingAlerts} loading={loading} tier={tier} newAlertIds={newSignalIds} />
          </TabsContent>
        </Tabs>

        {/* Upgrade CTA for free users */}
        {tier === "free" && (
          <Card className="mt-8 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/30">
            <CardContent className="flex items-center justify-between p-6">
              <div>
                <CardTitle className="text-white mb-2">Want real-time alerts?</CardTitle>
                <CardDescription className="text-zinc-400">
                  Upgrade to Pro for instant push notifications, real-time updates, and no delays.
                </CardDescription>
              </div>
              <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
                <a href="/#pricing">Upgrade to Pro — $49/mo</a>
              </Button>
            </CardContent>
          </Card>
        )}
        
        {/* Disclaimer */}
        <div className="mt-8 text-center">
          <p className="text-xs text-zinc-600">
            For informational purposes only. Not financial advice. Users should conduct their own research.
          </p>
        </div>
      </main>
    </div>
  );
}

function AlertsTable({ 
  alerts, 
  loading, 
  tier,
  newAlertIds,
}: { 
  alerts: Signal[]; 
  loading: boolean; 
  tier: string;
  newAlertIds: Set<string>;
}) {
  if (loading && alerts.length === 0) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-8 text-center text-zinc-400">
          <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
          Loading alerts...
        </CardContent>
      </Card>
    );
  }

  if (alerts.length === 0) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-8 text-center text-zinc-400">
          No alerts in this category yet.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <Table>
        <TableHeader>
          <TableRow className="border-zinc-800 hover:bg-transparent">
            <TableHead className="text-zinc-400">Date</TableHead>
            <TableHead className="text-zinc-400">News / Event</TableHead>
            <TableHead className="text-zinc-400">Related Market</TableHead>
            <TableHead className="text-zinc-400">Sentiment</TableHead>
            <TableHead className="text-zinc-400">Confidence</TableHead>
            <TableHead className="text-zinc-400">At Alert</TableHead>
            <TableHead className="text-zinc-400">Current</TableHead>
            <TableHead className="text-zinc-400 text-right">Change</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {alerts.map((alert) => {
            const isNew = newAlertIds.has(alert.id);
            return (
              <TableRow 
                key={alert.id} 
                className={`border-zinc-800 transition-colors ${
                  isNew 
                    ? "bg-green-500/10 animate-pulse" 
                    : "hover:bg-zinc-800/50"
                }`}
              >
                <TableCell className="font-mono text-sm text-zinc-400">
                  <div className="flex items-center gap-2">
                    {isNew && (
                      <span className="h-2 w-2 rounded-full bg-green-400 animate-ping" />
                    )}
                    {alert.date}
                  </div>
                </TableCell>
                <TableCell className="max-w-xs truncate text-white">
                  {alert.headline}
                </TableCell>
                <TableCell className="text-zinc-400 max-w-xs truncate">
                  {alert.market}
                </TableCell>
                <TableCell>
                  <Badge className={
                    alert.signal.includes("BUY") || alert.signal.includes("BULLISH")
                      ? "bg-green-500/20 text-green-400 border-green-500/30"
                      : alert.signal.includes("SELL") || alert.signal.includes("BEARISH")
                      ? "bg-red-500/20 text-red-400 border-red-500/30"
                      : "bg-blue-500/20 text-blue-400 border-blue-500/30"
                  }>
                    {alert.signal.replace("BUY ", "").replace("SELL ", "")}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className={
                    alert.confidence === "HIGH"
                      ? "bg-green-500/10 text-green-400 border-green-500/20"
                      : alert.confidence === "MEDIUM"
                      ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                      : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                  }>
                    {alert.confidence}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-white">
                  {alert.priceAtSignal}
                </TableCell>
                <TableCell className="font-mono text-white">
                  {alert.currentPrice || "—"}
                </TableCell>
                <TableCell className={`font-mono text-right font-bold ${
                  alert.pnl?.includes("-") ? "text-red-400" : "text-green-400"
                }`}>
                  {alert.pnl || "—"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      
      {tier === "free" && (
        <div className="border-t border-zinc-800 p-4 text-center text-sm text-yellow-500">
          ⚠️ Free tier alerts are delayed by 15 minutes. Upgrade to Pro for real-time access.
        </div>
      )}
    </Card>
  );
}
