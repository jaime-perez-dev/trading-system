import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const PAPER_TRADES_FILE = path.join(process.cwd(), "..", "data", "paper_trades.json");

interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  version: string;
  uptime: number;
  checks: {
    api: "ok" | "error";
    dataFiles: "ok" | "error";
    memory: {
      used: number;
      total: number;
      percentage: number;
    };
  };
}

const startTime = Date.now();

async function checkDataFiles(): Promise<"ok" | "error"> {
  try {
    await fs.access(PAPER_TRADES_FILE);
    return "ok";
  } catch {
    return "error";
  }
}

export async function GET() {
  const memoryUsage = process.memoryUsage();
  const heapUsedMB = Math.round(memoryUsage.heapUsed / 1024 / 1024);
  const heapTotalMB = Math.round(memoryUsage.heapTotal / 1024 / 1024);
  
  const dataFilesStatus = await checkDataFiles();
  
  const checks = {
    api: "ok" as const,
    dataFiles: dataFilesStatus,
    memory: {
      used: heapUsedMB,
      total: heapTotalMB,
      percentage: Math.round((heapUsedMB / heapTotalMB) * 100),
    },
  };

  const allOk = checks.api === "ok" && checks.dataFiles === "ok";
  const memoryOk = checks.memory.percentage < 90;

  const health: HealthStatus = {
    status: allOk && memoryOk ? "healthy" : allOk ? "degraded" : "unhealthy",
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || "1.0.0",
    uptime: Math.round((Date.now() - startTime) / 1000),
    checks,
  };

  const statusCode = health.status === "healthy" ? 200 : health.status === "degraded" ? 200 : 503;

  return NextResponse.json(health, {
    status: statusCode,
    headers: {
      "Cache-Control": "no-cache, no-store, must-revalidate",
    },
  });
}
