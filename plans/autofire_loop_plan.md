# Auto-Fire 持续轮询模式 — 改造计划

## 目标

将 [`backend/mantle_sniper.py`](backend/mantle_sniper.py) 从一次性脚本升级为持续运行的轮询机器人（Auto-Fire 模式），定期扫描 Mantle RPC 的新区块并自动处理。

## 当前状态

- `time` 模块已在第 11 行导入 — ✅ 无需修改
- `main()` 目前是线性的一次性流程：取最新块 → 过滤交易 → 调用 LLM → 保存 → 退出
- 没有循环、没有自动重扫、没有优雅退出机制

## 变更概览

对 `main()` 函数进行重构，将核心逻辑包装在 `while True:` 循环中，并加入区块去重和优雅退出处理。

---

## 详细步骤

### 步骤 1：初始化 `last_processed_block`

在 `main()` 中，在打印 banner 之后、循环开始之前，添加：

```python
last_processed_block = None
```

**位置**：大约在第 111 行（`print("=" * 60)` 横幅之后，当前的第 121 行 `# --- Fetch the latest block ---` 之前）。

### 步骤 2：用 `while True:` 包装核心逻辑

将现有的获取块、过滤交易、LLM 分析、DB 持久化逻辑整体移入 `while True:` 循环体。

### 步骤 3：在每个迭代中获取 `latest` 块

保持现有的 RPC 调用方式：

```python
block = send_rpc("eth_getBlockByNumber", ["latest", False])
block_data = block.get("result", {})
```

### 步骤 4：将块号从十六进制转换为整数

保持现有的转换逻辑：

```python
block_number_hex = block_data.get("number", "0x0")
block_number = int(block_number_hex, 16)
```

### 步骤 5：区块去重逻辑

在获取并解析区块号后，添加：

```
如果 last_processed_block 不为 None 且 新区块号 <= last_processed_block:
    time.sleep(2)
    continue    # 等待下一个新区块
否则:
    更新 last_processed_block = 新区块号
    打印 "[MANTLE-NEXUS] Scanning Block #<number>..."
    继续执行现有的交易过滤逻辑
```

### 步骤 6：循环限速

在循环末尾（所有处理完成后）添加 `time.sleep(2)` 以防止 RPC 节点过载。

### 步骤 7：优雅退出（KeyboardInterrupt）

将整个 `while True:` 循环包装在 `try...except KeyboardInterrupt:` 块中：

```python
try:
    while True:
        # ... 所有逻辑 ...
except KeyboardInterrupt:
    print("\n  [MANTLE-NEXUS] Shutting down gracefully. Goodbye!")
```

---

## 转换后的 `main()` 函数结构（伪代码）

```python
def main():
    load_dotenv()
    # ... banner 打印 ...
    # ... API key 检查 ...

    last_processed_block = None

    try:
        while True:
            block = send_rpc("eth_getBlockByNumber", ["latest", False])
            block_data = block.get("result", {})

            block_number_hex = block_data.get("number", "0x0")
            block_number = int(block_number_hex, 16)

            if last_processed_block is not None and block_number <= last_processed_block:
                time.sleep(2)
                continue

            last_processed_block = block_number
            print(f"\n  [MANTLE-NEXUS] Scanning Block #{block_number}...")

            # --- 此处放现有交易过滤逻辑（tx_hashes 遍历等）---
            # --- LLM 分析 ---
            # --- DB 保存 ---

            time.sleep(2)
    except KeyboardInterrupt:
        print("\n  [MANTLE-NEXUS] Shutting down gracefully. Goodbye!")
        print("=" * 60)
```

## 无需修改的现有逻辑

- `send_rpc()` — RPC 调用函数（保持不变）
- `get_ip_for_host()` — DNS 诊断（保持不变）
- `init_db()` — 数据库初始化（保持不变）
- `save_insight()` — 数据持久化（保持不变）
- 交易过滤规则：`0xdead` / `0x4200` 系统合约跳过、零值交易跳过（保持不变）
- LLM 调用和 prompt（保持不变）
- `if __name__ == "__main__":` 入口（保持不变）

## 注意事项

1. `send_rpc("eth_getBlockByNumber", ["latest", False])` 始终获取最新块，这是预期行为 — 机器人不会追溯历史块。
2. 相同区块号连续出现时，`time.sleep(2)` + `continue` 跳过处理，避免重复工作。
3. `time.sleep(2)` 置于循环末尾（成功处理后）也防止高频率请求。
4. 所有 `return` 语句（原脚本中 3 处：API key 缺失、无交易、无 MNT 转账）需要改为不退出循环，仅跳过当前迭代。具体处理：
   - **API key 缺失**：这仍应退出程序（无法恢复），保持 `return`。
   - **无交易/无 MNT 转账**：应改为 `time.sleep(2); continue` 继续下一轮扫描。

## 变更影响范围

只修改 `backend/mantle_sniper.py` 一个文件中的 `main()` 函数。无需修改其他文件、无需新增依赖、无需修改数据库 schema。
