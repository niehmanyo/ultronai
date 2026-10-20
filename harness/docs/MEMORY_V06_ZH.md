# Ultron V0.6 — Memory Engine（中文操作与验收）

本阶段增加 **SQLite 文件型长期记忆**：跨 Session 持久化、关键词检索、记忆候选提案、用户批准、更正、删除和 JSON 导出。不要求 Postgres、pgvector、Mem0 或新的 API Key，不会自动阅读/写入此前全部聊天。

## 1. 获取代码（不要合并 main）

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/v0.6-memory-engine
git pull --ff-only origin feature/v0.6-memory-engine
cd harness
python3 --version
python3 -m unittest discover -s memory/tests -v
```

必须有 Python 3（macOS 可用 `python3`），CLI 仅使用标准库，无需 `pip install`。默认记忆文件写到 `$DSH_HOME/memory/ultron.sqlite3`（若未设置 `DSH_HOME`，则是 `~/.ultron-dsh/memory/ultron.sqlite3`）。项目代码和 Git 仓库里不会存真实私人记忆。

## 2. 直接在终端验收

### (a) 新建一条记忆提案（此时不会写入正式记忆）

```bash
python3 memory/cli.py propose --action add --category preference --scope global \
  --text "回答后端技术问题时优先用中文，并保留英文术语。"
python3 memory/cli.py proposals
python3 memory/cli.py search "中文"
```

第一条输出 `proposal_id`。第二条能看到 `pending`；第三条应返回 `[]`，说明未获批准不会进入检索结果。

### (b) 你决定是否批准

```bash
python3 memory/cli.py approve --proposal-id <粘贴上一条 proposal_id>
python3 memory/cli.py search "中文"
python3 memory/cli.py list
```

批准后 `search` 能找到该记录，`list` 显示正式 `id`。如果不想保存，改用 `reject --proposal-id ...`。

### (c) 更正与删除也要批准

```bash
python3 memory/cli.py propose --action update --id <正式记忆id> \
  --text "回答技术问题时优先用中文，英文术语放在括号中。"
python3 memory/cli.py approve --proposal-id <新提案id>
python3 memory/cli.py propose --action forget --id <正式记忆id>
python3 memory/cli.py approve --proposal-id <删除提案id>
```

删除之前不会影响正式记忆。删除后 `list` 不再显示。**注意**：SQLite 删除不等于取证意义的安全擦除；旧备份、文件系统快照、SSD 底层历史可能存在副本。

### (d) 导出（隐私注意）

```bash
python3 memory/cli.py export
```

导出的 JSON 含真实私人记忆，不要复制进 GitHub Issue、PR、日志或者公开聊天。

## 3. 在 Ultron Agent 网页验收

1. 正常运行 `bash start-local.sh`，浏览器进入本地 dsh，选中 `harness/ultron-workspace`。
2. 新建 Session，发送：**“请使用 memory Skill 查询我已批准的技术回答偏好。调用实际工具，并说明检索结果。”**
3. 看工具日志确认调用 `python3 ../memory/cli.py search`，且结果和终端一致。该文件位于 workspace 的上级目录，若出现写入/执行权限请求，严格检查后再决定是否授权。
4. 再新建 Session 重复查询，确认记忆仍存在。**跨 Session 需实际工具调用才算成功**，不是模型凭当前上下文推测。
5. 测试口头记忆：**“我想记住 X，请先给出提案，不要保存。”**，应只看到 `pending`；明确批准提案后才会进入正式记忆。
6. 重启 dsh，确认记忆仍然可用。

## 4. CLI 命令速查

| 命令 | 用途 |
| --- | --- |
| `propose --action add --text "..."` | 建立待批准候选 |
| `propose --action update --id ID --text "..."` | 建立更正候选 |
| `propose --action forget --id ID` | 建立删除候选 |
| `proposals` | 查看待批准候选 |
| `approve --proposal-id ID` | 批准特定候选 |
| `reject --proposal-id ID` | 拒绝候选 |
| `search "关键词"` | 关键词检索正式记忆 |
| `list` | 列出正式记忆 |
| `export` | JSON 导出 |

## 5. 限制与安全

- **V0.6 是显式同意 + 关键词检索**。不支持向量语义搜索、自动摘要、自动抽取用户历史或后台 Memory Agent。
- `approved.md` 是旧版兼容文件；**不会自动迁移**为 SQLite。
- 不应存密码、API Key、敏感健康/金融身份数据；CLI 内置基础敏感凭据模式检测，但不是完整 DLP。
- User confirmation 是 Agent/Skill 使用规范，不是独立的强身份校验：有本机文件或 CLI 执行权限的进程仍可以直接批准操作。不要把工具执行界面开放到公网。
- 本地 DB 默认只为 macOS 当前账户提供基本文件权限；并未加密静态数据库。若 Mac 与他人共享账号，请使用系统磁盘加密和独立系统账户。
- 改代码分支不会自动删除记忆。想重置须先备份并自行处理 `$DSH_HOME/memory/`；不要误删所有 Session。
- OpenAI 仍通过现有代理启动配置，无额外模型消耗；文本检索不调用 API。
- 如果用户最新说明与已存记忆矛盾，应优先采纳最新说明，并提示发起 update 提案。

**验收后告诉我结果，我再按你的指令提交 PR/MR。**
