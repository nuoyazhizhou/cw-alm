# -*- coding: utf-8 -*-
"""把本仓的技能包与专家团挂载到 WorkBuddy，并检出轨。

为什么需要它：WorkBuddy 只从固定路径加载（`~/.workbuddy/skills`、
`~/.workbuddy/plugins/marketplaces/*/plugins/*` → `cache`），**仓库本身不能当加载路径**。
于是形态只能是「仓库 = 源，挂载点 = 投影」，而手工拷贝必然漂移——`agent-commons`
与它派生的专家包就是这么漂的（副本晚一天生成，靠运气保持一致）。

`--check` 是主入口：只读比对哈希，不落盘，可进 CI。发现漂移返 2。

用法：
    python tools/mount.py --check              # 只报告（CI 用）
    python tools/mount.py --apply              # 全部宿主写入
    python tools/mount.py --apply --host expert
    python tools/mount.py --check --json

退出码（与仓库既有三态一致）：0=一致/成功，2=漂移或前置缺失，64=用法错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_VIOLATION = 2
EXIT_USAGE = 64

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
GATES = REPO_ROOT / "kernel" / "cw-gates.md"
EXPERT_ROOT = REPO_ROOT / "experts" / "callwarden-alm"

WB_HOME = Path.home() / ".workbuddy"
WB_SKILLS = WB_HOME / "skills"
WB_MARKET = WB_HOME / "plugins" / "marketplaces" / "my-experts" / "plugins"
WB_CACHE = WB_HOME / "plugins" / "cache" / "my-experts"

# Codex 的 AGENTS.md 注入段也收敛到仓根同一份单一源：
# 以前三个 install.ps1 各存一份正文，改了技能却忘了改常驻指令是常态。
CODEX_HOME = Path.home() / ".codex"
CODEX_AGENTS = CODEX_HOME / "AGENTS.md"
SNIPPETS = REPO_ROOT / "references"

PACKAGES = ("requirements-cw", "code-review-cw", "test-cw")
ASSET_DIRS = ("references", "scripts", "assets")
EXTRA_FILES = ("README.md",)
GATES_NAME = "cw-gates.md"
EXPERT_NAME = "callwarden-alm"
EXPERT_PLUGIN = Path(".codebuddy-plugin") / "plugin.json"

# `.in_use/<pid>` 是应用运行时的占用标记，不是包内容；参与比对会制造假漂移。
SKIP_DIRS = frozenset({"__pycache__", ".in_use"})
SKIP_SUFFIXES = frozenset({".pyc", ".pyo"})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ignored(path: Path) -> bool:
    """是否属于运行时产物（目录名或后缀）。"""
    return bool(set(path.parts) & SKIP_DIRS) or path.suffix in SKIP_SUFFIXES


def _skill_plan(pkg: str) -> dict[str, Path]:
    """一个技能包的「应有文件」映射：相对路径 → 源文件。

    注入的 ``references/cw-gates.md`` 也在计划内——它不是包内副本，而是安装期
    从 ``kernel/`` 拷入的投影，故必须参与漂移比对（否则门禁改了不报）。
    """
    src = SKILLS_ROOT / pkg
    plan: dict[str, Path] = {"SKILL.md": src / "SKILL.md"}
    for extra in EXTRA_FILES:
        if (src / extra).is_file():
            plan[extra] = src / extra
    for name in ASSET_DIRS:
        base = src / name
        if not base.is_dir():
            continue
        for item in sorted(base.rglob("*")):
            if item.is_file() and not _ignored(item.relative_to(base)):
                plan[f"{name}/{item.relative_to(base).as_posix()}"] = item
    plan[f"references/{GATES_NAME}"] = GATES
    return plan


def _expert_plan() -> dict[str, Path]:
    """专家团的「应有文件」映射。"""
    if not EXPERT_ROOT.is_dir():
        return {}
    return {
        item.relative_to(EXPERT_ROOT).as_posix(): item
        for item in sorted(EXPERT_ROOT.rglob("*"))
        if item.is_file() and not _ignored(item.relative_to(EXPERT_ROOT))
    }


def expert_version() -> str:
    """从 plugin.json 读版本号；读不到返回空串（缓存目录名依赖它）。"""
    try:
        data = json.loads((EXPERT_ROOT / EXPERT_PLUGIN).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ""
    return str(data.get("version") or "")


def diff(plan: dict[str, Path], dest: Path) -> list[str]:
    """比对计划与落点，返回差异描述（空列表 = 一致）。"""
    problems: list[str] = []
    existing = (
        {
            item.relative_to(dest).as_posix()
            for item in dest.rglob("*")
            if item.is_file() and not _ignored(item.relative_to(dest))
        }
        if dest.is_dir()
        else set()
    )
    for rel, src in sorted(plan.items()):
        target = dest / rel
        if not target.is_file():
            problems.append(f"缺失 {rel}")
        elif sha256(target) != sha256(src):
            problems.append(f"内容不同 {rel}")
    for rel in sorted(existing - set(plan)):
        problems.append(f"多余 {rel}")
    return problems


def apply(plan: dict[str, Path], dest: Path) -> int:
    """把计划写入落点，删掉计划外文件；返回写入文件数。

    不做「先 rmtree 再铺」：专家团的 cache 目录里有应用运行时写的 ``.in_use``，
    整目录删除会把正在使用的会话踢掉。
    """
    dest.mkdir(parents=True, exist_ok=True)
    for item in list(dest.rglob("*")):
        if item.is_file() and not _ignored(item.relative_to(dest)):
            if item.relative_to(dest).as_posix() not in plan:
                item.unlink()
    for rel, src in sorted(plan.items()):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return len(plan)


def snippet_text(pkg: str) -> str:
    """读一个 AGENTS.md 注入段的单一源；marker 必须成对且包住整段。

    正文里不再有 PowerShell 的双反引号转义——那是为了喂 here-string 才存在的，
    存成普通 Markdown 后由 install.ps1 与 mount.py 各自原样使用。
    """
    path = SNIPPETS / f"agents-md-snippet-{pkg}.md"
    if not path.is_file():
        raise OSError(f"找不到注入单一源：{path}")
    text = path.read_text(encoding="utf-8-sig").rstrip("\r\n")
    begin, end = f"<!-- {pkg}:begin -->", f"<!-- {pkg}:end -->"
    if not (text.startswith(begin) and text.endswith(end)):
        raise ValueError(f"注入源 marker 不完整（须 begin 开头 / end 结尾）：{path}")
    return text


def _read_text_any(path: Path) -> str:
    """兼容历史编码：现有 Codex AGENTS.md 由 PowerShell 默认编码写成 GBK。

    读回来后统一以 UTF-8 写回，之后 install.ps1 与 mount.py 都显式指定 UTF8，
    不再依赖宿主默认编码——静默用错编码会把中文指令写成乱码。
    """
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise OSError(f"无法解码 {path}（已试 utf-8 / gbk）")


def agents_diff(dest: Path = CODEX_AGENTS) -> list[str]:
    """比对 Codex AGENTS.md 的三个注入段与仓内单一源。"""
    problems: list[str] = []
    content = _read_text_any(dest) if dest.is_file() else ""
    for pkg in PACKAGES:
        section = snippet_text(pkg)
        begin, end = f"<!-- {pkg}:begin -->", f"<!-- {pkg}:end -->"
        start = content.find(begin)
        stop = content.find(end, start + 1) if start >= 0 else -1
        if start < 0:
            problems.append(f"缺失注入段 {pkg}")
        elif stop < 0:
            problems.append(f"注入段未闭合 {pkg}")
        elif content[start : stop + len(end)] != section:
            problems.append(f"注入段内容不同 {pkg}")
    return problems


def agents_apply(dest: Path = CODEX_AGENTS) -> int:
    """幂等写入三个注入段；marker 之外的用户内容原样保留。返回写入段数。"""
    content = _read_text_any(dest) if dest.is_file() else ""
    for pkg in PACKAGES:
        section = snippet_text(pkg)
        begin, end = f"<!-- {pkg}:begin -->", f"<!-- {pkg}:end -->"
        start = content.find(begin)
        stop = content.find(end, start + 1) if start >= 0 else -1
        if start >= 0 and stop >= 0:
            content = content[:start] + section + content[stop + len(end) :]
        else:
            content = content.rstrip() + "\n\n" + section + "\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return len(PACKAGES)


def targets(host: str) -> list[tuple[str, Path, dict[str, Path]]]:
    """组装 (标签, 落点, 计划) 三元组。host 取 all/skills/expert。"""
    out: list[tuple[str, Path, dict[str, Path]]] = []
    if host in ("all", "skills"):
        for pkg in PACKAGES:
            out.append((f"workbuddy-skills/{pkg}", WB_SKILLS / pkg, _skill_plan(pkg)))
    if host in ("all", "expert"):
        version = expert_version()
        plan = _expert_plan()
        out.append((f"workbuddy-market/{EXPERT_NAME}", WB_MARKET / EXPERT_NAME, plan))
        if version:
            # 实际加载的是 cache 副本；只写 marketplaces 不生效（已实测）。
            out.append((f"workbuddy-cache/{EXPERT_NAME}@{version}", WB_CACHE / EXPERT_NAME / version, plan))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="挂载技能包与专家团到 WorkBuddy，并检出轨")
    parser.add_argument("--check", action="store_true", help="只比对不落盘（默认行为）")
    parser.add_argument("--apply", action="store_true", help="写入落点")
    parser.add_argument(
        "--host",
        default="all",
        choices=("all", "skills", "expert", "codex"),
        help="只处理某类目标（codex=AGENTS.md 注入段）",
    )
    parser.add_argument(
        "--check-source",
        action="store_true",
        help="只校验仓内源可合成（不依赖宿主落点，CI 用）",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON（CI 解析用）")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help → 0；用法错 → argparse 抛 2，统一转 64
        return EXIT_OK if not exc.code else EXIT_USAGE

    if not GATES.is_file():
        print(f"失败：找不到门禁唯一源 {GATES}", file=sys.stderr)
        return EXIT_VIOLATION
    if not SKILLS_ROOT.is_dir():
        print(f"失败：找不到技能根 {SKILLS_ROOT}", file=sys.stderr)
        return EXIT_VIOLATION
    if args.host in ("all", "expert") and not EXPERT_ROOT.is_dir():
        print(f"失败：找不到专家团 {EXPERT_ROOT}", file=sys.stderr)
        return EXIT_VIOLATION
    if args.host in ("all", "codex") and not SNIPPETS.is_dir():
        print(f"失败：找不到 AGENTS.md 注入单一源 {SNIPPETS}", file=sys.stderr)
        return EXIT_VIOLATION

    if args.check_source:
        # CI 上没有 ~/.workbuddy 落点，--check 会全报缺失；这里只验证「仓内源能合成出
        # 完整包」，覆盖门禁文件、技能包与专家团声明的完整性，不产生假红。
        try:
            plans = {pkg: _skill_plan(pkg) for pkg in PACKAGES}
            plans[EXPERT_NAME] = _expert_plan()
        except (OSError, ValueError) as exc:
            print(f"失败：{exc}", file=sys.stderr)
            return EXIT_VIOLATION
        for name, plan in plans.items():
            missing = [rel for rel, src in plan.items() if not src.is_file()]
            if missing:
                print(f"失败：{name} 源文件不存在：{', '.join(missing)}", file=sys.stderr)
                return EXIT_VIOLATION
            print(f"SOURCE OK {name:<24} files={len(plan)}")
        return EXIT_OK

    results = []
    drifted = 0
    if args.host in ("all", "codex"):
        try:
            problems = agents_diff()
        except (OSError, ValueError) as exc:
            print(f"失败：{exc}", file=sys.stderr)
            return EXIT_VIOLATION
        drifted += bool(problems)
        results.append(
            {
                "target": "codex/AGENTS.md",
                "path": str(CODEX_AGENTS),
                "files": len(PACKAGES),
                "ok": not problems,
                "problems": problems,
            }
        )
        if args.apply:
            written = agents_apply()
            print(f"APPLY {'codex/AGENTS.md':<46} sections={written}")

    for label, dest, plan in targets(args.host):
        problems = diff(plan, dest)
        drifted += bool(problems)
        results.append(
            {"target": label, "path": str(dest), "files": len(plan), "ok": not problems, "problems": problems}
        )
        if args.apply:
            written = apply(plan, dest)
            print(f"APPLY {label:<46} files={written}")

    if args.json:
        print(json.dumps({"ok": not drifted, "targets": results}, ensure_ascii=False, indent=2))
    elif not args.apply:
        for r in results:
            print(f"{'OK   ' if r['ok'] else 'DRIFT'} {r['target']:<46} files={r['files']}")
        for r in results:
            for p in r["problems"]:
                print(f"       - {r['target']}: {p}", file=sys.stderr)

    if args.apply:
        print(f"\n挂载完成：{len(results)} 个落点 → {WB_HOME}")
        print("重启宿主会话后生效（技能列表按目录签名缓存，会自动重建）。")
        return EXIT_OK

    if drifted:
        print(f"\n{drifted} 个落点与仓库不一致；跑 --apply 同步。", file=sys.stderr)
        return EXIT_VIOLATION
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
