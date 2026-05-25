#!/usr/bin/env python3
"""
MANTLE-NEXUS | Smart Money Sniper (Auto-Fire Mode)
Connects to Mantle RPC, sniffs the latest block,
extracts target transaction hashes, and analyzes them via LLM.
Runs continuously in a polling loop until Ctrl+C.
"""

import json
import os
import sqlite3
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv
from openai import OpenAI
from web3 import Web3

RPC_URL = "https://rpc.mantle.xyz"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds, will be multiplied by retry count (exponential backoff)

# Minimal ABI for NexusLedger.recordInsight(string,string)
MINIMAL_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_targetTx", "type": "string"},
            {"internalType": "string", "name": "_aiAssessment", "type": "string"},
        ],
        "name": "recordInsight",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def send_rpc(method, params=None):
    """Send JSON-RPC request with retry logic for transient network errors."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or []
    }).encode()
    req = urllib.request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            last_error = e
            reason = e.reason
            print(f"  [!] RPC connection attempt {attempt}/{MAX_RETRIES} failed: {reason}")
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY * attempt  # exponential backoff
                print(f"  [!] Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"\n  [!] All {MAX_RETRIES} attempts failed.")
                print(f"  [!] Target: {RPC_URL}")
                print(f"  [!] DNS resolves to: {get_ip_for_host()}")
                print(f"  [!] Error: {reason}")
                print(f"  [!] Possible causes:")
                print(f"  [!]   1. Network / proxy / VPN configuration issue in WSL")
                print(f"  [!]   2. RPC endpoint temporarily unavailable")
                print(f"  [!]   3. Firewall blocking outbound HTTPS (port 443)")
                print(f"  [!] Try running: curl -v --connect-timeout 5 {RPC_URL}")
                raise


def get_ip_for_host():
    """Resolve RPC hostname to IP for diagnostic purposes."""
    try:
        import socket
        return socket.gethostbyname("rpc.mantle.xyz")
    except Exception:
        return "unknown"


def init_db():
    """Initialize SQLite database and ensure the insights table exists."""
    conn = sqlite3.connect("mantle_nexus.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY,
            tx_hash TEXT UNIQUE,
            sender TEXT,
            receiver TEXT,
            amount_mnt REAL,
            ai_assessment TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def save_insight(conn, tx_hash, sender, receiver, amount_mnt, assessment):
    """Insert a transaction insight into the database, ignoring duplicates."""
    try:
        conn.execute(
            "INSERT INTO insights (tx_hash, sender, receiver, amount_mnt, ai_assessment) "
            "VALUES (?, ?, ?, ?, ?)",
            (tx_hash, sender, receiver, amount_mnt, assessment),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Duplicate tx_hash — skip silently
        pass


def export_insights_to_json(conn):
    """Query the latest 20 insights and overwrite ../frontend/public/insights.json."""
    cursor = conn.execute(
        "SELECT id, tx_hash, sender, receiver, amount_mnt, ai_assessment, timestamp "
        "FROM insights ORDER BY timestamp DESC LIMIT 20"
    )
    rows = cursor.fetchall()

    insights = []
    for row in rows:
        insights.append({
            "id": row[0],
            "tx_hash": row[1],
            "sender": row[2],
            "receiver": row[3],
            "amount_mnt": row[4],
            "ai_assessment": row[5],
            "timestamp": row[6],
        })

    # Resolve path relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "frontend", "public", "insights.json")

    with open(output_path, "w") as f:
        json.dump(insights, f, indent=2)

    print(f"  [MANTLE-NEXUS] JSON exported ({len(insights)} insights) → {output_path}")


def main():
    load_dotenv()

    # --- Web3 connection to Mantle Sepolia for on-chain writes ---
    from web3.middleware import geth_poa_middleware
    SEPOLIA_RPC = "https://rpc.sepolia.mantle.xyz"
    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("\n  [!] ERROR: PRIVATE_KEY not found in .env file.")
        print("  [!] On-chain writing will be disabled.")
        return

    account = w3.eth.account.from_key(private_key)
    print(f"  [MANTLE-NEXUS] Web3 account: {account.address}")

    contract_address = os.getenv("MANTLE_CONTRACT_ADDRESS")
    if not contract_address:
        print("\n  [!] ERROR: MANTLE_CONTRACT_ADDRESS not found in .env file.")
        print("  [!] On-chain writing will be disabled.")
        return

    contract = w3.eth.contract(address=contract_address, abi=MINIMAL_ABI)
    print(f"  [MANTLE-NEXUS] Contract loaded: {contract_address}")

    print("=" * 60)
    print("  [MANTLE-NEXUS] Initializing smart money sniper (Auto-Fire)...")
    print("  [MANTLE-NEXUS] RPC target: https://rpc.mantle.xyz")
    print("=" * 60)

    # --- Check for DeepSeek API key ---
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("\n  [!] ERROR: DEEPSEEK_API_KEY not found in .env file.")
        print("  [!] Please create a .env file in the backend/ directory with:")
        print('  [!]   DEEPSEEK_API_KEY=sk-your_deepseek_api_key_here')
        print("\n" + "=" * 60)
        return

    last_processed_block = None

    last_processed_block = None

    try:
        while True:
            try:
                # --- Fetch the latest block ---
                block = send_rpc("eth_getBlockByNumber", ["latest", False])
                block_data = block.get("result", {})

                block_number_hex = block_data.get("number", "0x0")
                block_number = int(block_number_hex, 16)
                tx_hashes = block_data.get("transactions", [])

                # --- Block dedup: skip if we've already processed this block ---
                if last_processed_block is not None and block_number <= last_processed_block:
                    time.sleep(2)
                    continue

                last_processed_block = block_number
                print(f"\n  [MANTLE-NEXUS] Scanning Block #{block_number} ({block_number_hex})")
                print(f"  [+] Transactions in block: {len(tx_hashes)}")
                print("-" * 60)

                if not tx_hashes:
                    print("\n  [!] No transactions found in this block.")
                    print("-" * 60)
                    time.sleep(2)
                    continue

                # --- Loop through transactions to find a real native MNT transfer ---
                SYSTEM_PREFIXES = ("0xdead", "0x4200")

                target_tx = None
                tx_hash = None

                for tx_hash_str in tx_hashes:
                    try:
                        tx_detail = send_rpc("eth_getTransactionByHash", [tx_hash_str])
                    except Exception as rpc_err:
                        # Single transaction lookup failed — skip this tx, try next
                        print(f"  [!] RPC error fetching tx {tx_hash_str}: {rpc_err}")
                        continue
                    tx_data = tx_detail.get("result", {})

                    if not tx_data:
                        continue

                    sender_addr = tx_data.get("from", "").lower()

                    # Skip system contracts (0xdead... or 0x4200...)
                    if sender_addr.startswith(SYSTEM_PREFIXES):
                        continue

                    # Skip contract creations (to is None) or system contract receivers
                    receiver_addr = tx_data.get("to")
                    if receiver_addr is None:
                        continue
                    if receiver_addr.lower().startswith(SYSTEM_PREFIXES):
                        continue

                    # Skip zero-value transactions (no native MNT transfer)
                    value_hex = tx_data.get("value", "0x0")
                    value_wei = int(value_hex, 16)
                    if value_wei == 0:
                        continue

                    # Real native MNT transfer — target acquired!
                    target_tx = tx_data
                    tx_hash = tx_hash_str
                    break

                if target_tx is None:
                    print("\n  [MANTLE-NEXUS] No native MNT transfers in this block. Skipping...")
                    print("-" * 60)
                    time.sleep(2)
                    continue

                print(f"\n  [MANTLE-NEXUS] Target Acquired: {tx_hash}")

                sender = target_tx.get("from", "unknown")
                receiver = target_tx.get("to", "unknown")
                value_hex = target_tx.get("value", "0x0")
                value_wei = int(value_hex, 16)
                value_mnt = value_wei / 1e18

                print(f"  [MANTLE-NEXUS] Sender:   {sender}")
                print(f"  [MANTLE-NEXUS] Receiver: {receiver}")
                print(f"  [MANTLE-NEXUS] Value:    {value_mnt:.18f} MNT")
                print("-" * 60)

                # --- Construct the LLM prompt ---
                prompt = (
                    f"An on-chain transaction just occurred on Mantle Network. "
                    f"Sender: {sender}, Receiver: {receiver}, Amount: {value_mnt} MNT. "
                    f"As a Web3 data analyst, give a 1-sentence quick assessment of "
                    f"whether this is a whale movement, regular user activity, "
                    f"or contract interaction.\n\n"
                    f"CRITICAL FORMATTING RULE: You MUST wrap the core classification "
                    f"in double asterisks. For example: **Whale Movement**, "
                    f"**Regular User Activity**, or **Contract Interaction**. "
                    f"Do not omit the asterisks — they are required for frontend parsing."
                )

                # --- Call DeepSeek API (OpenAI-compatible) ---
                print("  [MANTLE-NEXUS] Requesting AI assessment from DeepSeek...")
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com"
                )

                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=30
                )

                assessment = response.choices[0].message.content.strip()
                print(f"\n  [MANTLE-NEXUS AI INSIGHT] {assessment}")

                # --- Persist to local SQLite ---
                conn = init_db()
                save_insight(conn, tx_hash, sender, receiver, value_mnt, assessment)
                print("  [MANTLE-NEXUS] Data saved to local SQLite DB.")

                # --- Export latest insights to static JSON for frontend ---
                export_insights_to_json(conn)

                conn.close()

                # --- Stamp insight on-chain via NexusLedger ---
                try:
                    tx = contract.functions.recordInsight(tx_hash, assessment).build_transaction({
                        "from": account.address,
                        "nonce": w3.eth.get_transaction_count(account.address),
                    })
                    signed_tx = account.sign_transaction(tx)
                    tx_hash_onchain = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash_onchain)
                    print(f"  [MANTLE-NEXUS] 🔗 AI Insight permanently stamped on-chain! Tx: {tx_hash_onchain.hex()}")
                except Exception as e:
                    print(f"  [MANTLE-NEXUS] ⚠️ On-chain write skipped (RPC rate-limit or error): {e}")

                print("\n" + "-" * 60)
                print("  [MANTLE-NEXUS] Cycle complete. Waiting for next block...")
                print("-" * 60)

                time.sleep(2)

            except Exception as cycle_err:
                # Catch any transient error (DNS, RPC timeout, etc.) and keep the loop alive
                print(f"\n  [!] ⚡ Transient error, restarting cycle in 5s: {cycle_err}")
                print("-" * 60)
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n  [MANTLE-NEXUS] Shutting down gracefully. Goodbye!")
        print("=" * 60)


if __name__ == "__main__":
    main()
