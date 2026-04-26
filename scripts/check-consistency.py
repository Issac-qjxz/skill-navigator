#!/usr/bin/env python3
"""skill-navigator: 一致性检查
比较 skills_index.json 与 ~/.claude/skills/*/ 目录列表，输出 JSON 结果。
"""
import os
import json
import sys


SKILLS_DIR = os.path.expanduser("~/.claude/skills")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "skills_index.json")


def main():
    # Python 版本检查
    if sys.version_info < (3, 6):
        _output("PYTHON_VERSION_TOO_OLD",
                "skill-navigator 需要 Python >= 3.6。下载地址：https://python.org")
        return

    # 检查索引文件
    if not os.path.isfile(INDEX_PATH):
        _output("INDEX_MISSING", f"索引文件不存在: {INDEX_PATH}")
        return

    # 读取索引
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        _output("INDEX_CORRUPT", f"索引文件解析失败: {e}")
        return

    # 提取索引中的 skill name（排除 command 类型）
    index_names = set()
    for s in data.get("skills", []):
        if s.get("type") != "command":
            index_names.add(s["name"])

    # 扫描实际安装的 skill 目录
    actual_names = set()
    if os.path.isdir(SKILLS_DIR):
        for entry in sorted(os.listdir(SKILLS_DIR)):
            entry_path = os.path.join(SKILLS_DIR, entry)
            if os.path.isdir(entry_path):
                actual_names.add(entry)

    # 比较
    only_in_index = index_names - actual_names
    only_in_actual = actual_names - index_names

    if only_in_index or only_in_actual:
        _output("INDEX_MISMATCH", "", {
            "index_count": len(index_names),
            "actual_count": len(actual_names),
            "only_in_index": sorted(only_in_index),
            "only_in_actual": sorted(only_in_actual),
        })
    else:
        _output("INDEX_OK", f"一致: {len(index_names)} 个 skill",
                {"count": len(index_names)})


def _output(status, message, extra=None):
    result = {"status": status, "message": message}
    if extra:
        result.update(extra)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
