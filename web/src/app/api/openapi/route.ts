import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const OPENAPI_FILE = path.join(process.cwd(), "openapi.yaml");

export async function GET() {
  try {
    const spec = await fs.readFile(OPENAPI_FILE, "utf-8");
    
    return new NextResponse(spec, {
      headers: {
        "Content-Type": "application/yaml; charset=utf-8",
        "Cache-Control": "public, max-age=3600", // Cache for 1 hour
      },
    });
  } catch (error) {
    console.error("OpenAPI spec error:", error);
    return NextResponse.json(
      { error: "OpenAPI specification not found" },
      { status: 404 }
    );
  }
}
