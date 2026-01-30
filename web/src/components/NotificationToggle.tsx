"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Bell, BellOff, BellRing, Loader2 } from "lucide-react";
import {
  isNotificationSupported,
  getNotificationPermission,
  requestNotificationPermission,
  registerServiceWorker,
  subscribeToPush,
  unsubscribeFromPush,
  getPushSubscription,
  saveSubscriptionToServer,
  removeSubscriptionFromServer,
} from "@/lib/notifications";

interface NotificationToggleProps {
  userId?: string;
  tier: "free" | "pro" | "enterprise";
  onStatusChange?: (enabled: boolean) => void;
}

type NotificationState = "unsupported" | "denied" | "disabled" | "enabled" | "loading";

export function NotificationToggle({ 
  userId, 
  tier,
  onStatusChange 
}: NotificationToggleProps) {
  const [state, setState] = useState<NotificationState>("loading");
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);

  // Check current notification state on mount
  useEffect(() => {
    async function checkState() {
      const supported = await isNotificationSupported();
      if (!supported) {
        setState("unsupported");
        return;
      }

      const permission = await getNotificationPermission();
      if (permission === "denied") {
        setState("denied");
        return;
      }

      // Register service worker
      const reg = await registerServiceWorker();
      if (!reg) {
        setState("unsupported");
        return;
      }
      setRegistration(reg);

      // Check if already subscribed
      const subscription = await getPushSubscription(reg);
      setState(subscription ? "enabled" : "disabled");
    }

    checkState();
  }, []);

  const enableNotifications = useCallback(async () => {
    if (!registration) return;
    
    setState("loading");

    try {
      // Request permission if needed
      const permission = await requestNotificationPermission();
      if (permission !== "granted") {
        setState("denied");
        return;
      }

      // Subscribe to push
      const subscription = await subscribeToPush(registration);
      if (!subscription) {
        setState("disabled");
        return;
      }

      // Save to server
      const saved = await saveSubscriptionToServer(subscription, userId);
      if (!saved) {
        console.warn("Failed to save subscription to server");
      }

      setState("enabled");
      onStatusChange?.(true);
    } catch (error) {
      console.error("Failed to enable notifications:", error);
      setState("disabled");
    }
  }, [registration, userId, onStatusChange]);

  const disableNotifications = useCallback(async () => {
    if (!registration) return;
    
    setState("loading");

    try {
      const subscription = await getPushSubscription(registration);
      if (subscription) {
        await removeSubscriptionFromServer(subscription.endpoint);
        await unsubscribeFromPush(registration);
      }
      
      setState("disabled");
      onStatusChange?.(false);
    } catch (error) {
      console.error("Failed to disable notifications:", error);
      setState("enabled"); // Revert
    }
  }, [registration, onStatusChange]);

  // For free tier, show upgrade prompt
  if (tier === "free") {
    return (
      <Button 
        variant="outline" 
        size="sm"
        className="gap-2 border-zinc-700 hover:bg-zinc-800 text-zinc-400"
        disabled
        title="Push notifications are a Pro feature"
      >
        <BellOff className="h-4 w-4" />
        <span className="hidden sm:inline">Pro only</span>
      </Button>
    );
  }

  // Render based on state
  switch (state) {
    case "loading":
      return (
        <Button 
          variant="outline" 
          size="sm"
          className="gap-2 border-zinc-700"
          disabled
        >
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="hidden sm:inline">Loading...</span>
        </Button>
      );

    case "unsupported":
      return (
        <Button 
          variant="outline" 
          size="sm"
          className="gap-2 border-zinc-700 text-zinc-500"
          disabled
          title="Notifications not supported in this browser"
        >
          <BellOff className="h-4 w-4" />
          <span className="hidden sm:inline">Unsupported</span>
        </Button>
      );

    case "denied":
      return (
        <Button 
          variant="outline" 
          size="sm"
          className="gap-2 border-red-900 text-red-400"
          disabled
          title="Notifications blocked. Enable in browser settings."
        >
          <BellOff className="h-4 w-4" />
          <span className="hidden sm:inline">Blocked</span>
        </Button>
      );

    case "disabled":
      return (
        <Button 
          variant="outline" 
          size="sm"
          className="gap-2 border-zinc-700 hover:bg-zinc-800 hover:text-green-400 hover:border-green-900"
          onClick={enableNotifications}
          title="Enable push notifications for new signals"
        >
          <Bell className="h-4 w-4" />
          <span className="hidden sm:inline">Enable alerts</span>
        </Button>
      );

    case "enabled":
      return (
        <Button 
          variant="outline" 
          size="sm"
          className="gap-2 border-green-900 bg-green-500/10 text-green-400 hover:bg-red-500/10 hover:text-red-400 hover:border-red-900"
          onClick={disableNotifications}
          title="Disable push notifications"
        >
          <BellRing className="h-4 w-4" />
          <span className="hidden sm:inline">Alerts on</span>
        </Button>
      );
  }
}
