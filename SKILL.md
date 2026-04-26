---
name: skill-navigator
description: "对 65+ 个已安装 skill 的智能推荐入口。输入自然语言描述的任务需求，自动匹配最合适的 skill 并给出调用命令和简介。支持 Claude Code 和 OpenClaw。也兼容 Codex CLI（通过 .codexclinerules）。"
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep"
---

# skill-navigator

65+ 个已安装 skill 的统一推荐入口。你说想做什么，我告诉你怎么调用。

## 流程

### 第一步：一致性检查

执行以下命令：

```bash
PYTHON=""
command -v python3 &>/dev/null && PYTHON="python3" || command -v python &>/dev/null && PYTHON="python"

if [ -z "$PYTHON" ]; then
  echo "PYTHON_MISSING"
  exit 0
fi

SKILL_DIR="$HOME/.claude/skills/skill-navigator"
"$PYTHON" "$SKILL_DIR/scripts/check-consistency.py"
```

根据输出结果判断：

- `{"status": "PYTHON_VERSION_TOO_OLD", ...}` → "Python 版本过低，请安装 Python >= 3.6"
- `{"status": "INDEX_MISSING", ...}` → 进入第二步（询问用户是否重建）
- `{"status": "INDEX_CORRUPT", ...}` → 进入第二步（询问用户是否重建）
- `{"status": "INDEX_OK", ...}` → 直接跳到第三步（推荐引擎）
- `{"status": "INDEX_MISMATCH", ...}` → 进入第二步，并向用户展示差异

### 第二步：询问用户是否重建

如果索引缺失、损坏或不一致，向用户展示差异详情，然后给出选项。

```bash
PYTHON=""
command -v python3 &>/dev/null && PYTHON="python3" || command -v python &>/dev/null && PYTHON="python"
SKILL_DIR="$HOME/.claude/skills/skill-navigator"
```

> **技能索引与实际情况不一致，请选择：**
>
> **A: 本地重建（推荐）** — 扫描本地 SKILL.md 文件，零网络，快速。
>   局限：可能漏掉无独立 SKILL.md 的父 skill（如 `/plan` 等别名命令）。
>
> **B: GitHub 重建** — 去 GitHub 拉取仓库信息，更完整。
>   需要 gh CLI（未安装会自动降级为 REST API）。较慢但更完整。
>
> **C: 跳过重建** — 用现有索引继续推荐，未收录的 skill 不会被推荐。
>
> **D: 放弃** — 不执行任何操作。
>
> 你的选择是？

等待用户输入后，根据选择执行：

- **A** → `"$PYTHON" "$SKILL_DIR/scripts/scan-local.py"`
- **B** → `"$PYTHON" "$SKILL_DIR/scripts/scan-github.py"`
- **C** → 直接进入第三步（推荐引擎）
- **D** → "已取消。"

如果索引不存在且用户也没选 A/B，输出：
> "未找到 skill 索引文件，skill-navigator 无法使用。请先执行本地重建或 GitHub 重建。"

### 第三步：推荐引擎

1. 读取 `skills_index.json` 统计总数

```bash
"$PYTHON" -c "
import os, json
path = os.path.expanduser('~/.claude/skills/skill-navigator/skills_index.json')
with open(path, encoding='utf-8') as f:
    data = json.load(f)
skills = data.get('skills', [])
print(f'共 {len(skills)} 个 skill 可推荐')
"
```

2. 将 `skills_index.json` 的全部内容加载到会话上下文作为知识库。

3. 根据用户输入的 `<需求描述>`，结合每条记录的 `name` + `description` + `category` 做语义匹配。

4. 输出最相关的前 1-3 个 skill，格式如下：

```
╭─ 推荐结果 ──────────────────────────────────╮
│                                             │
│ 1. <skill-name>                             │
│    命令: <command>                           │
│    用途: <description>                       │
│    分类: <category>                          │
│    (所属: <parent>)                         │
│                                             │
│ 2. <skill-name>                             │
│    ...                                      │
│                                             │
╰─────────────────────────────────────────────╯
```

### 第四步：无匹配处理

如果没有任何 skill 与用户需求匹配：

> "当前 N 个已安装 skill 中未找到与你需求匹配的条目。你可以尝试以下方向：
> - 工程工作流与代码协作
> - 科研与论文工作流
> - 官方文档技能
> - 中文写作辅助
> - 规划与项目管理
>
> 请补充更多描述后重试。"

## 注意事项

1. 执行 `python3` 前必须检测 `command -v python3` 或 `command -v python`，都不可用时提示用户安装 Python。
2. 重建脚本的 stdout/stderr 直接呈现给用户，不要加工修改。
3. 所有提示保持中文输出。
4. 如果用户选 B 但 gh 不可用，告知用户正在使用 REST API 降级方案。
5. 调用时保证先完成一致性和重建流程（如果需要），然后再读取索引推荐。
