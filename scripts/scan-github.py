#!/usr/bin/env python3
"""skill-navigator: GitHub 重建脚本
遍历 ~/.claude/skills/*/，通过 gh CLI（首选）或 GitHub REST API（降级）
获取仓库信息，生成带分类和链接的 skills_index.json。
"""
import os
import json
import sys
import subprocess
import glob
import re
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_DIR, "skills_index.json")
SKILLS_DIR = os.path.expanduser("~/.claude/skills")
COMMANDS_DIR = os.path.expanduser("~/.claude/commands")

# 已知的父 skill 仓库映射
PARENT_REPOS = {
    "superpowers-zh": ("jnMetaCode/superpowers-zh", "工程工作流与代码协作"),
    "agent-research-skills": ("lingzhi227/agent-research-skills", "科研与论文工作流"),
    "anthropics/skills": ("anthropics/skills", "官方文档技能"),
}

# 子 skill 到父 skill 的映射
SUB_SKILL_PARENTS = {
    "superpowers-zh": [
        "brainstorming", "chinese-code-review", "chinese-commit-conventions",
        "chinese-documentation", "chinese-git-workflow", "dispatching-parallel-agents",
        "executing-plans", "finishing-a-development-branch", "mcp-builder",
        "receiving-code-review", "requesting-code-review", "subagent-driven-development",
        "systematic-debugging", "test-driven-development", "using-git-worktrees",
        "using-superpowers", "verification-before-completion", "workflow-runner",
        "writing-plans", "writing-skills",
    ],
    "agent-research-skills": [
        "algorithm-design", "atomic-decomposition", "backward-traceability",
        "citation-management", "code-debugging", "data-analysis", "deep-research",
        "excalidraw-skill", "experiment-code", "experiment-design", "figure-generation",
        "github-research", "idea-generation", "latex-formatting", "literature-review",
        "literature-search", "math-reasoning", "novelty-assessment", "paper-assembly",
        "paper-compilation", "paper-revision", "paper-to-code", "paper-writing-section",
        "rebuttal-writing", "related-work-writing", "research-planning", "self-review",
        "slide-generation", "survey-generation", "symbolic-equation", "table-generation",
    ],
}

# 已知的独立 skill 仓库
STANDALONE_REPOS = {
    "book2skill": "zhliu0106/book2skill",
    "darwin-skill": "alchaincyf/darwin-skill",
    "docx": "anthropics/skills/tree/main/skills/docx",
    "excalidraw-skill": None,
    "huashu-nuwa": "alchaincyf/nuwa-skill",
    "humanizer-zh": "op7418/Humanizer-zh",
    "pdf": "anthropics/skills/tree/main/skills/pdf",
    "planning-with-files": "OthmanAdi/planning-with-files",
    "planning-with-files-zh": "OthmanAdi/planning-with-files/tree/main/skills/planning-with-files-zh",
    "pptx": "anthropics/skills/tree/main/skills/pptx",
    "ralph-loop": "PageAI-Pro/ralph-loop",
    "skill-creator": "anthropics/skills/tree/main/skills/skill-creator",
    "vercel-react-view-transitions": "vercel-labs/react-view-transitions-skill",
    "xlsx": "anthropics/skills/tree/main/skills/xlsx",
    "zhangxuefeng-skill": "alchaincyf/zhangxuefeng-skill",
}


def parse_frontmatter(filepath):
    """从 SKILL.md 中解析 YAML frontmatter，返回 dict。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None
        raw = match.group(1)
        result = {}
        for line in raw.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
        return result
    except Exception:
        return None


def get_local_description(name):
    """从本地 SKILL.md 获取某个 skill 的描述。"""
    skill_md = os.path.join(SKILLS_DIR, name, "SKILL.md")
    if os.path.isfile(skill_md):
        fm = parse_frontmatter(skill_md)
        if fm and fm.get("description"):
            desc = fm["description"]
            return desc.split("。")[0] + "。" if "。" in desc else desc
    return ""


def infer_skill_info(name):
    """推断 skill 的父包、类型、分类和 GitHub URL。"""
    # 检查是否是子 skill
    for parent, children in SUB_SKILL_PARENTS.items():
        if name in children:
            repo, category = PARENT_REPOS.get(parent, ("", ""))
            url = f"https://github.com/{repo}/tree/main/skills/{name}" if repo else ""
            return parent, "child-skill", category, url

    # 检查是否是已知独立 skill
    if name in STANDALONE_REPOS:
        repo = STANDALONE_REPOS[name]
        if repo:
            url = f"https://github.com/{repo}"
        else:
            url = ""
        return None, "standalone", "", url

    # 检查是否是父包名本身
    if name in PARENT_REPOS:
        repo, category = PARENT_REPOS[name]
        url = f"https://github.com/{repo}"
        return None, "parent-skill", category, url

    return None, "standalone", "", ""


def check_gh_available():
    """检查 gh CLI 是否可用且已登录。"""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
            errors="replace"
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def gh_fetch_repo(repo):
    """通过 gh CLI 获取仓库信息。"""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", repo, "--json", "description,url"],
            capture_output=True, text=True, timeout=15,
            errors="replace"
        )
        return json.loads(result.stdout), None
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        return None, str(e)


def curl_fetch_repo(repo):
    """通过 GitHub REST API 获取仓库信息（gh 不可用时的降级方案）。"""
    url = f"https://api.github.com/repos/{repo}"
    req = Request(url, headers={"User-Agent": "skill-navigator/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return {
            "description": data.get("description", ""),
            "url": data.get("html_url", f"https://github.com/{repo}"),
        }, None
    except HTTPError as e:
        if e.code == 403:
            return None, "API 速率限制已耗尽"
        elif e.code == 404:
            return None, "仓库未找到"
        return None, f"HTTP {e.code}"
    except URLError:
        return None, "网络不可达"


def build_skill_entry(name):
    """构建单个 skill 的索引条目。"""
    parent, skill_type, category, known_url = infer_skill_info(name)

    parent_repo = None
    if parent and parent in PARENT_REPOS:
        parent_repo = PARENT_REPOS[parent][0]

    description = get_local_description(name)

    entry = {
        "name": name,
        "category": category,
        "description": description,
        "command": f"/{name}",
        "parent": parent,
        "type": skill_type,
        "github_url": known_url,
        "sub_commands": [],
    }

    return entry


def scan_with_gh():
    """使用 gh CLI 扫描所有 skill。"""
    print("  → 使用 gh CLI...")
    all_skills = []
    not_found = []

    for skill_dir in sorted(glob.glob(os.path.join(SKILLS_DIR, "*"))):
        if not os.path.isdir(skill_dir):
            continue
        name = os.path.basename(skill_dir)
        entry = build_skill_entry(name)

        # 尝试通过 gh 获取更精确的信息
        if entry["parent"] and entry["parent"] in PARENT_REPOS:
            repo = PARENT_REPOS[entry["parent"]][0]
            data, err = gh_fetch_repo(repo)
            if err:
                not_found.append((name, err))
            elif data:
                entry["github_url"] = data.get("url", entry["github_url"])
                # 子 skill 追加子路径
                if entry["type"] == "child-skill":
                    entry["github_url"] += f"/tree/main/skills/{name}"

        all_skills.append(entry)

    return all_skills, not_found


def scan_with_curl():
    """使用 urllib 降级扫描。"""
    print("  → 使用 GitHub REST API（降级模式）...")
    all_skills = []
    not_found = []
    rate_limited = False

    for skill_dir in sorted(glob.glob(os.path.join(SKILLS_DIR, "*"))):
        if not os.path.isdir(skill_dir):
            continue
        name = os.path.basename(skill_dir)
        entry = build_skill_entry(name)

        # 尝试通过 API 获取仓库信息
        if entry["parent"] and entry["parent"] in PARENT_REPOS:
            repo = PARENT_REPOS[entry["parent"]][0]
            data, err = curl_fetch_repo(repo)
            if err:
                if "速率限制" in err:
                    rate_limited = True
                not_found.append((name, err))
            elif data:
                entry["github_url"] = data.get("url", entry["github_url"])
                if entry["type"] == "child-skill":
                    entry["github_url"] += f"/tree/main/skills/{name}"

        all_skills.append(entry)
        time.sleep(0.3)  # 避免触发限流

    return all_skills, not_found, rate_limited


def scan_commands():
    """扫描 ~/.claude/commands/*.md 补充命令条目。"""
    if not os.path.isdir(COMMANDS_DIR):
        return []

    commands = []
    for cmd_file in sorted(glob.glob(os.path.join(COMMANDS_DIR, "*.md"))):
        name = os.path.splitext(os.path.basename(cmd_file))[0]
        fm = parse_frontmatter(cmd_file)
        desc = ""
        if fm and fm.get("description"):
            desc = fm["description"].split("。")[0] + "。" if "。" in fm["description"] else fm["description"]

        commands.append({
            "name": name,
            "category": "命令别名",
            "description": desc,
            "command": f"/{name}",
            "parent": None,
            "type": "command",
            "github_url": "",
            "sub_commands": [],
        })

    return commands


def main():
    print("=" * 50)
    print("  skill-navigator: GitHub 重建")
    print("=" * 50)

    # Python 版本检查
    if sys.version_info < (3, 6):
        print(f"ERROR: 需要 Python >= 3.6，当前版本: {sys.version}")
        sys.exit(1)

    # 检查 skill 目录
    if not os.path.isdir(SKILLS_DIR):
        print(f"ERROR: skill 安装目录不存在: {SKILLS_DIR}")
        print("请确认已通过 'npx skills add' 安装至少一个 skill。")
        sys.exit(1)

    # 判断重建方式
    print("\n[检查] GitHub CLI 可用性...")
    use_gh = check_gh_available()

    if use_gh:
        print("  [OK] gh CLI 已安装且已登录")
        all_skills, not_found = scan_with_gh()
    else:
        print("  [WARN] gh CLI 不可用或未登录")
        gh_installed = False
        try:
            subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=5, errors="replace")
            gh_installed = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            gh_installed = False

        if not gh_installed:
            print("    提示: 安装 gh CLI 可获取更完整的重建体验")
            print("    Windows: winget install GitHub.cli")
            print("    macOS: brew install gh")
            print("    Linux: apt install gh")
        else:
            print("    提示: 请执行 'gh auth login' 完成认证")
        print("  尝试使用 GitHub REST API 降级...")

        all_skills, not_found, rate_limited = scan_with_curl()
        if rate_limited:
            print("  [WARN] API 速率限制已耗尽，部分仓库信息可能缺失")

    # 补充命令别名
    print("\n[扫描] 命令别名...")
    commands = scan_commands()
    all_skills.extend(commands)
    if commands:
        print(f"  [OK] 发现 {len(commands)} 个命令别名")

    # 去重
    seen = set()
    deduped = []
    for s in all_skills:
        if s["name"] not in seen:
            seen.add(s["name"])
            deduped.append(s)
    all_skills = deduped

    # 写入
    index = {
        "version": 1,
        "updated_at": "",
        "skills": all_skills
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 50}")
    print(f"  完成: {len(all_skills)} 个条目")
    print(f"  输出: {OUTPUT_PATH}")
    print(f"{'=' * 50}")

    if not_found:
        print(f"\n以下 {len(not_found)} 个 skill 的 GitHub 信息获取失败:")
        for name, err in not_found:
            print(f"  - {name}: {err}")
        print("  这些 skill 已使用本地信息纳入索引。")


if __name__ == "__main__":
    main()
