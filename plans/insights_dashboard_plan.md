# Mantle-Nexus Insight Dashboard 实施计划

## 概述

为 Mantle-Nexus Web3 AI Smart Money Tracker 构建前端 Insight Dashboard，从本地 SQLite 数据库读取交易洞察数据，以赛博朋克/黑客风格展示。

## 项目结构关系

```
/home/dw/projects/mantle-nexus/
├── backend/
│   ├── mantle_sniper.py        # 后端数据采集脚本
│   └── mantle_nexus.db         # SQLite 数据库文件（目标数据源）
├── frontend/
│   ├── package.json            # Next.js 项目配置
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # 待重写的仪表盘页面
│   │   ├── globals.css         # 全局样式
│   │   ├── api/
│   │   │   └── insights/
│   │   │       └── route.ts    # 新建 API 路由
│   │   └── ...
│   └── ...
└── plans/
    └── insights_dashboard_plan.md
```

## 数据库模型

`insights` 表结构（来自 `backend/mantle_sniper.py:76-86`）：

| 列名 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增ID |
| `tx_hash` | TEXT UNIQUE | 交易哈希 |
| `sender` | TEXT | 发送方地址 |
| `receiver` | TEXT | 接收方地址 |
| `amount_mnt` | REAL | 转账金额(MNT) |
| `ai_assessment` | TEXT | AI 分析评估 |
| `timestamp` | DATETIME | 默认 CURRENT_TIMESTAMP |

## 实施步骤

### 步骤 1: 安装 better-sqlite3 依赖

在 `frontend/` 目录下执行：

```bash
cd /home/dw/projects/mantle-nexus/frontend && npm install better-sqlite3
cd /home/dw/projects/mantle-nexus/frontend && npm install -D @types/better-sqlite3
```

### 步骤 2: 创建 API 路由

**文件**: `frontend/app/api/insights/route.ts`

职责：
- 使用 `better-sqlite3` 连接 SQLite 数据库
- 数据库路径：`path.join(process.cwd(), '../backend/mantle_nexus.db')`
- 查询最新 20 条 insights 记录，按 `timestamp DESC` 排序
- 返回 JSON 响应
- 错误处理：若数据库文件不存在或查询失败，返回 500 + 错误信息

**关键代码设计**：
```typescript
import { NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

export async function GET() {
  try {
    const dbPath = path.join(process.cwd(), '../backend/mantle_nexus.db');
    const db = new Database(dbPath, { readonly: true });
    const rows = db.prepare('SELECT * FROM insights ORDER BY timestamp DESC LIMIT 20').all();
    db.close();
    return NextResponse.json(rows);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch insights', details: String(error) },
      { status: 500 }
    );
  }
}
```

### 步骤 3: 重写 `app/page.tsx`

**文件**: `frontend/app/page.tsx`

设计要求：
- **组件类型**: Client Component (`"use client"`)
- **自动刷新**: `useEffect` 每 5 秒轮询 API
- **背景**: `bg-black` 纯黑
- **配色方案**:
  - 标题/边框: `text-green-400` 霓虹绿
  - 数据值: `text-cyan-400` 青色
  - 正文: `text-zinc-300` / `text-white`
- **字体**: 等宽/monospace (`font-mono`)
- **布局**:
  - 居中标题: `MANTLE-NEXUS // INTELLIGENCE FEED`
  - 垂直列表/网格展示 insights
- **卡片设计**:
  - 深色背景卡片 `bg-zinc-950/90` + 左边框霓虹绿 `border-l-2 border-l-green-400`
  - `tx_hash` 截断显示前6后4字符
  - `sender` 截断显示
  - `receiver` 截断显示
  - `amount_mnt` 保留4位小数
  - `ai_assessment` 突出显示（白色粗体或特殊样式）
- **无过度动画**，只使用 Tailwind 工具类

**组件状态管理**：
```typescript
interface Insight {
  id: number;
  tx_hash: string;
  sender: string;
  receiver: string;
  amount_mnt: number;
  ai_assessment: string;
  timestamp: string;
}

// 状态
const [insights, setInsights] = useState<Insight[]>([]);
const [error, setError] = useState<string | null>(null);
const [loading, setLoading] = useState(true);
```

**辅助函数**：
```typescript
const truncateHash = (hash: string, prefix = 6, suffix = 4) =>
  `${hash.slice(0, prefix)}...${hash.slice(-suffix)}`;

const truncateAddress = (addr: string) =>
  `${addr.slice(0, 6)}...${addr.slice(-4)}`;

const formatMNT = (amount: number) => amount.toFixed(4);
```

### 步骤 4: 验证与运行

```bash
cd /home/dw/projects/mantle-nexus/frontend && npm run dev
```

## 数据流

```
[SQLite DB] <- [API Route (better-sqlite3)] <- [Next.js GET /api/insights]
                                                      |
                                                      v
                                         [Dashboard Page (poll every 5s)]
```

## 错误边界

- API 路由：捕获 DB 连接失败、查询失败，返回 500 + 错误详情
- Dashboard：显示错误状态 `text-red-400`，不崩溃
- 空数据：显示 "No insights available" 占位信息
