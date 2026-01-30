"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export interface Signal {
  id: string;
  date: string;
  headline: string;
  market: string;
  signal: string;
  confidence: string;
  priceAtSignal: string;
  currentPrice?: string;
  pnl?: string;
  status: "open" | "closed" | "pending";
}

export interface SignalsResponse {
  signals: Signal[];
  meta: {
    tier: string;
    count: number;
    delayed: boolean;
    timestamp: string;
  };
}

export interface UseRealTimeSignalsOptions {
  tier: "free" | "pro" | "enterprise";
  pollInterval?: number; // ms - default 10s for pro, 60s for free
  onNewSignal?: (signal: Signal) => void;
  enabled?: boolean;
}

export interface UseRealTimeSignalsResult {
  signals: Signal[];
  loading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  isLive: boolean;
  newSignalIds: Set<string>;
  refresh: () => Promise<void>;
  clearNewIndicators: () => void;
}

export function useRealTimeSignals({
  tier,
  pollInterval,
  onNewSignal,
  enabled = true,
}: UseRealTimeSignalsOptions): UseRealTimeSignalsResult {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [newSignalIds, setNewSignalIds] = useState<Set<string>>(new Set());
  
  const previousSignalIds = useRef<Set<string>>(new Set());
  const isFirstLoad = useRef(true);
  
  // Default poll intervals: 10s for pro/enterprise, 60s for free
  const effectivePollInterval = pollInterval ?? (tier === "free" ? 60000 : 10000);

  const fetchSignals = useCallback(async () => {
    if (!enabled) return;
    
    try {
      const response = await fetch(`/api/signals?tier=${tier}&limit=50`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data: SignalsResponse = await response.json();
      
      if (data.signals) {
        // Detect new signals (only after first load)
        if (!isFirstLoad.current) {
          const newIds = new Set<string>();
          data.signals.forEach((signal) => {
            if (!previousSignalIds.current.has(signal.id)) {
              newIds.add(signal.id);
              onNewSignal?.(signal);
            }
          });
          
          if (newIds.size > 0) {
            setNewSignalIds((prev) => new Set([...prev, ...newIds]));
          }
        }
        
        // Update previous signal IDs
        previousSignalIds.current = new Set(data.signals.map((s) => s.id));
        isFirstLoad.current = false;
        
        setSignals(data.signals);
        setError(null);
        setIsLive(true);
      }
      
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch signals");
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  }, [tier, enabled, onNewSignal]);

  // Initial fetch
  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  // Polling
  useEffect(() => {
    if (!enabled || tier === "free") return; // No polling for free tier (delayed anyway)
    
    const interval = setInterval(fetchSignals, effectivePollInterval);
    return () => clearInterval(interval);
  }, [enabled, tier, effectivePollInterval, fetchSignals]);

  // Clear "new" indicators after 30 seconds
  useEffect(() => {
    if (newSignalIds.size === 0) return;
    
    const timeout = setTimeout(() => {
      setNewSignalIds(new Set());
    }, 30000);
    
    return () => clearTimeout(timeout);
  }, [newSignalIds]);

  const clearNewIndicators = useCallback(() => {
    setNewSignalIds(new Set());
  }, []);

  return {
    signals,
    loading,
    error,
    lastUpdate,
    isLive,
    newSignalIds,
    refresh: fetchSignals,
    clearNewIndicators,
  };
}
