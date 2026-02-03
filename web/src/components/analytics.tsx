'use client';

import { useAnalytics } from '@/hooks/useAnalytics';
import { GoogleAnalytics } from '@/lib/analytics';

export function Analytics() {
  useAnalytics();
  
  const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;
  
  return <GoogleAnalytics GA_MEASUREMENT_ID={GA_MEASUREMENT_ID} />;
}