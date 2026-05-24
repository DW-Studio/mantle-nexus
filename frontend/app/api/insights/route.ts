import { NextResponse } from "next/server";
import Database from "better-sqlite3";
import path from "path";
import fs from "fs";

export async function GET() {
  try {
    // Resolve absolute path to the SQLite database
    const dbPath = path.join(process.cwd(), "../backend/mantle_nexus.db");

    // Check if database file exists before attempting to connect
    if (!fs.existsSync(dbPath)) {
      return NextResponse.json(
        { error: "Database not found", details: `No database file at ${dbPath}` },
        { status: 500 }
      );
    }

    // Open database in read-only mode
    const db = new Database(dbPath, { readonly: true });

    // Query the latest 20 insights ordered by timestamp descending
    const rows = db
      .prepare("SELECT * FROM insights ORDER BY timestamp DESC LIMIT 20")
      .all();

    db.close();

    return NextResponse.json(rows);
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to fetch insights",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}
