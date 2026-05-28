# 👁️ MANTLE-NEXUS 

**The AI-Powered On-Chain Intelligence Matrix for Mantle Network.**
Built for the Turing Test Hackathon.

[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](#) 
[![Powered by DeepSeek](https://img.shields.io/badge/AI-DeepSeek-blue?logo=openai)](#) 
[![Network](https://img.shields.io/badge/Network-Mantle_Sepolia-green?logo=ethereum)](#)

## 🔗 Live Links & Hackathon Bounties

- **Live Cyberpunk Dashboard:** https://mantle-nexus-eight.vercel.app *(Optimized for both Desktop & Mobile)*
- **Demo Video :** https://youtu.be/B5gCbhbmJ8M

### 🏆 Proof for "20 Project Deployment Award"
Mantle-Nexus permanently stamps AI-generated transaction insights onto the Mantle Sepolia Testnet, fulfilling the exact requirement of "AI inference result written on-chain".
- **Smart Contract Address (Mantle Sepolia):** `0x641c523a96Fb3561063dC9d386587B50f21512DD`
- **Proof of AI Inference On-Chain (Tx Hash):** `0xbd9252c5675c4c5d6709b26d67410aa0c0b30794bbf1f7695a5da65d0cd2cef6`

---

## 💡 The Problem & The Alpha

In Web3, raw transaction data is infinite and meaningless. High-frequency trading bots get eaten by friction costs, and retail investors drown in the noise of `0xdead...` hashes. 

**Mantle-Nexus is a low-maintenance, high-density information filtering tool.** It acts as an automated sniper that monitors the Mantle Network, intercepts real MNT transfers, and uses LLMs to translate raw hexadecimal data into human-readable, actionable commercial intelligence (e.g., distinguishing a $50 regular transfer from a massive Whale Movement or a Contract Interaction).

---

## 🏗️ Architecture: CQRS for Web3 x AI

We intentionally decoupled the heavy-lifting AI backend from the lightweight frontend to achieve zero-latency public delivery.

1. **The Sniper (Python Backend):** A continuous daemon polling Mantle RPC nodes. It filters noise, extracts real value transfers, and prompts the DeepSeek AI API for human-like analysis.
2. **The Notary (Solidity Smart Contract):** Once an AI insight is generated, the Python daemon autonomously signs a transaction to stamp the AI's verdict directly onto the Mantle Sepolia blockchain.
3. **The Window (Next.js + Tailwind):** A serverless, purely static Vercel frontend. It consumes a dynamically generated `insights.json`, delivering a blazing-fast, auto-refreshing cyberpunk dashboard to end-users without database bottlenecks.

---

## 🚀 Key Features

- **AI-Driven Assessment:** Real-time fiat valuation estimation and behavior classification via Prompt Engineering.
- **On-Chain Permanence:** AI conclusions are not just stored locally; they are immortalized as immutable events on Mantle.
- **Cyberpunk Dark-Mode UI:** High-contrast, hacker-vibe interface with Regex-powered Markdown parsing for maximum scannability.
- **Serverless Resilience:** 100% immune to Vercel timeout errors via local-to-static JSON injection.

---

## 🛠️ Quick Start (Local Demo)

To run the full stack locally:

```bash
# 1. Start the Frontend (Port 3000)
cd frontend
npm install
npm run dev

# 2. Start the AI Sniper (In a separate terminal)
cd backend
pip install -r requirements.txt
# Ensure .env is configured with RPC, DeepSeek API, and Wallet Private Key
python mantle_sniper.py
