import { NextRequest, NextResponse } from "next/server";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();

    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Invalid email address" },
        { status: 400 }
      );
    }

    try {
      await prisma.waitlist.create({
        data: {
          email,
          source: "landing-page",
        },
      });
    } catch (e: any) {
      // P2002 = Unique constraint failed (email already exists)
      if (e.code === 'P2002') {
        return NextResponse.json(
          { message: "Already on waitlist", alreadyExists: true },
          { status: 200 }
        );
      }
      throw e;
    }

    const count = await prisma.waitlist.count();

    return NextResponse.json(
      { message: "Successfully joined waitlist", count },
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
    const count = await prisma.waitlist.count();
    return NextResponse.json({ count });
  } catch (error) {
    console.error("Waitlist error:", error);
    // Fallback if DB is down/not configured
    return NextResponse.json({ count: 0 });
  }
}
