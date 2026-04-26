#!/usr/bin/env python3
"""skill-navigator: 本地重建脚本
遍历 ~/.claude/skills/*/SKILL.md，解析 frontmatter，生成 skills_index.json。
零网络依赖，仅需 Python >= 3.6。
"""
import os
import json
import re
import glob


SKILLS_DIR = os.path.expanduser("~/.claude/skills")
COMMANDS_DIR = os.path.expanduser("~/.claude/commands")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "skills_index.json")


def parse_frontmatter(filepath):
    """从 SKILL.md 中解析 YAML frontmatter，返回 dict。"""
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


def scan_skills():
    """扫描所有 skill 目录，提取信息。"""
    if not os.path.isdir(SKILLS_DIR):
        print(f"WARN: skill 安装目录不存在: {SKILLS_DIR}")
        return [], []

    skills = []
    skipped = []

    for skill_dir in sorted(glob.glob(os.path.join(SKILLS_DIR, "*"))):
        if not os.path.isdir(skill_dir):
            continue
        name = os.path.basename(skill_dir)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            skipped.append((name, "缺少 SKILL.md"))
            continue

        fm = parse_frontmatter(skill_md)
        if not fm:
            skipped.append((name, "frontmatter 解析失败"))
            continue

        desc = fm.get("description", "") or ""
        # 取第一句作为简洁描述
        first_sentence = desc.split("。")[0] + "。" if "。" in desc else desc

        skills.append({
            "name": name,
            "category": "",
            "description": first_sentence,
            "command": f"/{name}",
            "parent": None,
            "type": "standalone",
            "github_url": "",
            "sub_commands": []
        })

    return skills, skipped


def scan_commands():
    """扫描 ~/.claude/commands/*.md 补充命令条目。"""
    if not os.path.isdir(COMMANDS_DIR):
        return [], []

    commands = []
    skipped = []

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
            "sub_commands": []
        })

    return commands, skipped


def main():
    print("=" * 50)
    print("  skill-navigator: 本地重建")
    print("=" * 50)

    # 检查 Python 版本
    import sys
    if sys.version_info < (3, 6):
        print("ERROR: 需要 Python >= 3.6，当前版本: " + sys.version)
        sys.exit(1)

    all_skills = []
    all_skipped = []

    # 扫描 skills
    print("\n[1/2] 扫描 skill 目录...")
    skills, skipped = scan_skills()
    all_skills.extend(skills)
    all_skipped.extend(skipped)
    print(f"      发现 {len(skills)} 个 skill")

    # 扫描 commands
    print("\n[2/2] 扫描命令目录...")
    cmds, cmd_skipped = scan_commands()
    all_skills.extend(cmds)
    all_skipped.extend(cmd_skipped)
    if cmds:
        print(f"      发现 {len(cmds)} 个命令别名")

    # 去重（按 name）
    seen = set()
    deduped = []
    for s in all_skills:
        if s["name"] not in seen:
            seen.add(s["name"])
            deduped.append(s)
    all_skills = deduped

    # 写入索引
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

    if all_skipped:
        print(f"\n警告: {len(all_skipped)} 个条目被跳过:")
        for name, reason in all_skipped:
            print(f"  - {name}: {reason}")


if __name__ == "__main__":
    main()
