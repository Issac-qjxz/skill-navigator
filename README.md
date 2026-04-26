# skill-navigator

对 65+ 个已安装 AI coding assistant skill 的智能推荐入口。
输入自然语言描述的任务需求，自动匹配最合适的 skill 并给出调用命令和简介。

注意：这个65+是我自己用的skills建立的索引，本skill自带重建索引功能，
    启用skill-navigator后对你自己的skills进行重建索引即可正常使用，教程见下部分。

## 平台支持

| 平台 | 入口 | 说明 |
|---|---|---|
| Claude Code | `/skill-navigator <需求描述>` | 原生支持，完整交互流程 |
| OpenClaw | `/skill-navigator <需求描述>` | 与 Claude Code 完全兼容 |
| Codex CLI | 自然语言触发 | 通过 `.codexclinerules` 加载规则 |

## 快速开始

### 安装

```bash
# 通过 npx skills（推荐）
npx skills add Issac-qjxz/skill-navigator

# 或手动复制
git clone https://github.com/Issac-qjxz/skill-navigator
cp -r skill-navigator ~/.claude/skills/skill-navigator
```

### 首次使用前重建索引

```bash
cd ~/.claude/skills/skill-navigator

# 本地重建（推荐，零网络，< 1s）
python3 scripts/scan-local.py

# 或 GitHub 重建（更完整，包含父 skill 和别名命令）
python3 scripts/scan-github.py
```

### 使用示例

```
/skill-navigator 我想写一篇论文综述
```

输出：

```
╭─ 推荐结果 ──────────────────────────────────╮
│                                             │
│ 1. deep-research                            │
│    命令: /deep-research <主题>               │
│    用途: 系统性学术文献综述，6 阶段流程       │
│    分类: 科研与论文工作流                     │
│                                             │
│ 2. literature-search                        │
│    命令: /literature-search <关键词>         │
│    用途: 使用 Semantic Scholar 搜索论文      │
│    分类: 科研与论文工作流                     │
│                                             │
╰─────────────────────────────────────────────╯
```

## 重建模式

| 模式 | 命令 | 网络 | 速度 | 覆盖度 |
|---|---|---|---|---|
| 本地重建 | `python3 scripts/scan-local.py` | 无需 | < 1s | 有 SKILL.md 的 skill |
| GitHub 重建 | `python3 scripts/scan-github.py` | 需要 | 慢 | 全部含父 skill 和别名 |

## 项目结构

```
skill-navigator/
├── SKILL.md                    # Claude Code / OpenClaw 入口
├── .codexclinerules            # Codex CLI 入口
├── skills_index.json           # 技能索引（由重建脚本生成）
├── scripts/
│   ├── check-consistency.py   # 一致性检查脚本
│   ├── scan-local.py           # 本地重建脚本
│   └── scan-github.py          # GitHub 重建脚本
├── README.md
└── LICENSE
```

## 依赖

- **Python >= 3.6** — 必需。用于运行重建脚本（仅 stdlib，无第三方包）
- **gh CLI** — 可选。GitHub 重建模式使用，未安装时自动降级为 REST API

## 许可证

MIT
