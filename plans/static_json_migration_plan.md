# Static JSON Migration Plan (Integrated Approach)

## 背景

Vercel Serverless 环境无法打包 `better-sqlite3`（原生 Node 模块），导致 API 路由在部署时返回 404。解决方案是完全绕过 Serverless API，采用静态 JSON 文件架构。

同时，为了本地 Demo 的实时体验，JSON 导出逻辑直接集成到 [`backend/mantle_sniper.py`](backend/mantle_sniper.py) 中，每次新交易写入 DB 后自动刷新 JSON。

## 目标架构

```
┌─────────────┐     fetch(/insights.json)      ┌───────────────────┐
│  浏览器      │ ──────────────────────────►  │ 静态 JSON 文件     │
│ (page.tsx)   │    每 5 秒轮询                │ (public/ 目录)     │
└─────────────┘                               └───────────────────┘
                                                  ✔ Vercel 静态托管
                                                  ✔ 本地实时更新

┌───────────────────────────────────────────────────┐
│  backend/mantle_sniper.py                          │
│                                                    │
│  主循环:                                            │
│    1. 扫描区块 → 找到 MNT 转账                       │
│    2. DeepSeek AI 评估                               │
│    3. 写入 SQLite DB                                 │
│    4. 上链存证                                       │
│    5. export_insights_to_json(conn)  ← 新增         │
│       └─ 查询最新 20 条 → 写入 frontend/public/     │
└───────────────────────────────────────────────────┘
```

## 执行步骤

### 步骤 1：卸载 better-sqlite3 依赖

在 `frontend/` 目录下运行 `npm uninstall better-sqlite3 @types/better-sqlite3`。

### 步骤 2：删除 API 路由目录

删除 `frontend/app/api/` 整个目录。

### 步骤 3：清理 next.config.ts

移除 `serverExternalPackages` 配置，因为不再需要。

### 步骤 4：集成 JSON 导出到 mantle_sniper.py

在 [`backend/mantle_sniper.py`](backend/mantle_sniper.py) 中：

**新增函数：**
```python
def export_insights_to_json(conn):
    """Query latest 20 insights and write to frontend/public/insights.json"""
    cursor = conn.execute(
        "SELECT id, tx_hash, sender, receiver, amount_mnt, ai_assessment, timestamp "
        "FROM insights ORDER BY timestamp DESC LIMIT 20"
    )
    rows = cursor.fetchall()
    # Convert to list of dicts
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
    # Resolve path relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "frontend", "public", "insights.json")
    with open(output_path, "w") as f:
        json.dump(insights, f, indent=2)
    print(f"  [MANTLE-NEXUS] JSON exported to {output_path}")
```

**调用位置：** 在 `save_insight()` 之后、上链操作之后立即调用：
```python
# 原代码：保存到 SQLite
save_insight(conn, tx_hash, sender, receiver, value_mnt, assessment)

# 新增：导出 JSON
export_insights_to_json(conn)

# 原代码：上链存证
try:
    tx = contract.functions.recordInsight(...)
    ...
```

### 步骤 5：重写 page.tsx

将 [`frontend/app/page.tsx`](frontend/app/page.tsx) 第 39 行的 `fetch("/api/insights")` 改为 `fetch("/insights.json")`。其余代码完全不变。

### 步骤 6：运行 + 部署

1. 启动 `mantle_sniper.py`：它会自动持续生成 `frontend/public/insights.json`
2. `git add -A && git commit -m "refactor: migrate to static JSON architecture for Vercel compatibility" && git push`
3. Vercel 自动重新部署，直接托管静态 JSON

## 涉及的文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| [`frontend/package.json`](frontend/package.json) | 修改 | 移除 better-sqlite3 和 @types/better-sqlite3 |
| [`frontend/app/api/`](frontend/app/api/) | 删除 | 整个 api 目录 |
| [`frontend/next.config.ts`](frontend/next.config.ts) | 修改 | 移除 serverExternalPackages |
| [`backend/mantle_sniper.py`](backend/mantle_sniper.py) | 修改 | 新增 `export_insights_to_json()` 函数并调用 |
| [`frontend/app/page.tsx`](frontend/app/page.tsx) | 修改 | fetch URL 改为 /insights.json |
