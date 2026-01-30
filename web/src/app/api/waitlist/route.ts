import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const WAITLIST_FILE = path.join(process.cwd(), "..", "data", "waitlist.json");

interface WaitlistEntry {
  email: string;
  timestamp: string;
  source: string;
}

async function getWaitlist(): Promise<WaitlistEntry[]> {
  try {
    const data = await fs.readFile(WAITLIST_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return [];
  }
}

async function saveWaitlist(entries: WaitlistEntry[]): Promise<void> {
  await fs.writeFile(WAITLIST_FILE, JSON.stringify(entries, null, 2));
}

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();

    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Invalid email address" },
        { status: 400 }
      );
    }

    const waitlist = await getWaitlist();

    // Check if already on waitlist
    if (waitlist.some((entry) => entry.email === email)) {
      return NextResponse.json(
        { message: "Already on waitlist", alreadyExists: true },
        { status: 200 }
      );
    }

    // Add to waitlist
    waitlist.push({
      email,
      timestamp: new Date().toISOString(),
      source: "landing-page",
    });

    await saveWaitlist(waitlist);

    return NextResponse.json(
      { message: "Successfully joined waitlist", count: waitlist.length },
      { status: 200 }
    );
  } catch (error) {
    console.error("Waitlist error:", error);
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const waitlist = await getWaitlist();
    return NextResponse.json({ count: waitlist.length });
  } catch (error) {
    console.error("Waitlist error:", error);
    return NextResponse.json({ count: 0 });
  }
}
