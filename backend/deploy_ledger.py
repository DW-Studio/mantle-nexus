#!/usr/bin/env python3
"""
MANTLE-NEXUS | NexusLedger Contract Deployer
Compiles NexusLedger.sol and deploys it to Mantle Sepolia.
"""

import os
import stat

import requests
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

# --- Solidity compiler ---
import solcx
from solcx.install import get_solcx_install_folder

# ──────────────────────────────────────────────
#  1. Load environment
# ──────────────────────────────────────────────
load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise RuntimeError("[!] PRIVATE_KEY not found in .env")

RPC_URL = "https://rpc.sepolia.mantle.xyz"
CHAIN_ID = 5003  # Mantle Sepolia

# ──────────────────────────────────────────────
#  2. Install Solidity compiler (0.8.19)
#     solc-bin.ethereum.org is unreliable on some
#     networks, so we download from GitHub releases.
# ──────────────────────────────────────────────
SOLC_VERSION = "0.8.19"
solc_bin_path = get_solcx_install_folder().joinpath(f"solc-v{SOLC_VERSION}")

if not solc_bin_path.exists():
    print(f"  [MANTLE-NEXUS] Downloading solc {SOLC_VERSION} from GitHub releases...")
    url = (
        f"https://github.com/ethereum/solidity/releases/download/"
        f"v{SOLC_VERSION}/solc-static-linux"
    )
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(solc_bin_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    # Mark as executable
    st = os.stat(solc_bin_path)
    os.chmod(solc_bin_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  [MANTLE-NEXUS] solc {SOLC_VERSION} downloaded → {solc_bin_path}")
else:
    print(f"  [MANTLE-NEXUS] solc {SOLC_VERSION} already cached at {solc_bin_path}")

solcx.set_solc_version(SOLC_VERSION)
print(f"  [MANTLE-NEXUS] solc version: {solcx.get_solc_version()}")

# ──────────────────────────────────────────────
#  3. Compile NexusLedger.sol
# ──────────────────────────────────────────────
CONTRACT_PATH = "../contracts/NexusLedger.sol"
print(f"  [MANTLE-NEXUS] Compiling {CONTRACT_PATH} ...")

compiled = solcx.compile_files(
    [CONTRACT_PATH],
    output_values=["abi", "bin"],
)

# solcx.compile_files returns keys as absolute paths
contract_id = f"{os.path.abspath(CONTRACT_PATH)}:NexusLedger"
contract_data = compiled[contract_id]

abi = contract_data["abi"]
bytecode = contract_data["bin"]

print(f"  [MANTLE-NEXUS] Compilation OK — ABI + Bytecode extracted")
print(f"  [MANTLE-NEXUS] Bytecode length: {len(bytecode)} hex chars")

# ──────────────────────────────────────────────
#  4. Connect to Mantle Sepolia
# ──────────────────────────────────────────────
print(f"  [MANTLE-NEXUS] Connecting to {RPC_URL} ...")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
# Mantle Sepolia uses Clique (POA) — inject POA middleware
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

assert w3.is_connected(), "[!] Failed to connect to Mantle Sepolia RPC"
print(f"  [MANTLE-NEXUS] Connected!  Chain ID: {w3.eth.chain_id}")
print(f"  [MANTLE-NEXUS] Latest block: {w3.eth.block_number}")

# ──────────────────────────────────────────────
#  5. Load deployer account
# ──────────────────────────────────────────────
acct = w3.eth.account.from_key(PRIVATE_KEY)
deployer_addr = acct.address
balance_wei = w3.eth.get_balance(deployer_addr)
balance_mnt = w3.from_wei(balance_wei, "ether")

print(f"  [MANTLE-NEXUS] Deployer:     {deployer_addr}")
print(f"  [MANTLE-NEXUS] Balance:      {balance_mnt:.6f} MNT (Sepolia)")

if balance_wei == 0:
    raise RuntimeError(
        "[!] Deployer wallet has zero balance. "
        "Fund it via https://faucet.sepolia.mantle.xyz/ and retry."
    )

# ──────────────────────────────────────────────
#  6. Build & sign deployment transaction
# ──────────────────────────────────────────────
NexusLedger = w3.eth.contract(abi=abi, bytecode=bytecode)

# Estimate max fee via eth_gasPrice (or fallback to a manual value)
gas_price = w3.eth.gas_price  # wei
print(f"  [MANTLE-NEXUS] Current gas price: {w3.from_wei(gas_price, 'gwei'):.2f} Gwei")

# Build the constructor-less deployment tx
construct_txn = NexusLedger.constructor().build_transaction({
    "from": deployer_addr,
    "nonce": w3.eth.get_transaction_count(deployer_addr),
    "gas": 0,          # will be estimated
    "gasPrice": gas_price,
    "chainId": CHAIN_ID,
})

# Estimate gas
estimated_gas = w3.eth.estimate_gas(construct_txn)
construct_txn["gas"] = estimated_gas
print(f"  [MANTLE-NEXUS] Estimated gas: {estimated_gas}")

# Sign
signed_txn = acct.sign_transaction(construct_txn)

# ──────────────────────────────────────────────
#  7. Broadcast & wait for receipt
# ──────────────────────────────────────────────
print(f"\n  [MANTLE-NEXUS] Broadcasting deployment transaction...")
# In web3 v6 the attribute is camelCase: rawTransaction
tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
print(f"  [MANTLE-NEXUS] Tx hash: {tx_hash.hex()}")

print(f"  [MANTLE-NEXUS] Waiting for confirmation...")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

contract_address = receipt["contractAddress"]
print(f"\n{'=' * 60}")
print(f"  [MANTLE-NEXUS] Contract deployed! Permanent Address: {contract_address}")
print(f"{'=' * 60}")
print(f"\n  Block #:       {receipt['blockNumber']}")
print(f"  Gas used:      {receipt['gasUsed']}")
print(f"  Tx hash:       {tx_hash.hex()}")
print(f"  Explorer:      https://explorer.sepolia.mantle.xyz/address/{contract_address}")
