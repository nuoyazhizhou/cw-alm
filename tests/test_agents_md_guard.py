"""AGENTS.md 注入段单一源守卫。

回归锚：三个 install.ps1 原各存一份注入正文，其中 code-review-cw 段用了单反引号，
被 PowerShell here-string 吃掉，落到 ~/.codex/AGENTS.md 后 Markdown 代码标记全丢；
另外两段用双反引号才侥幸写对。现在正文只存仓根 references/agents-md-snippet-*.md，
install.ps1 与 mount.py 都读它，本测试锁住「不回流成副本」与「读写编码正确」。
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TOOL = _REPO_ROOT / "tools" / "mount.py"

_spec = importlib.util.spec_from_file_location("cw_mount_agents", _TOOL)
mount = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = mount
_spec.loader.exec_module(mount)

SNIPPET_DIR = _REPO_ROOT / "references"


@pytest.fixture
def snippets(tmp_path, monkeypatch):
    """临时造三份合法 snippet，并让 mount 从临时目录读。"""
    root = tmp_path / "references"
    root.mkdir()
    for pkg in mount.PACKAGES:
        (root / f"agents-md-snippet-{pkg}.md").write_text(
            f"<!-- {pkg}:begin -->\n## {pkg}\n\n- body `{pkg}`\n<!-- {pkg}:end -->\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(mount, "SNIPPETS", root)
    return root


def _pkg_snippet_lines(pkg: str) -> list[str]:
    return [line for line in (SNIPPET_DIR / f"agents-md-snippet-{pkg}.md").read_text(encoding="utf-8").splitlines() if line.strip()]


def test_all_three_snippets_exist_with_markers():
    for pkg in mount.PACKAGES:
        text = mount.snippet_text(pkg)
        assert text.startswith(f"<!-- {pkg}:begin -->")
        assert text.endswith(f"<!-- {pkg}:end -->")


@pytest.mark.parametrize("pkg", ["requirements-cw", "code-review-cw", "test-cw"])
def test_install_script_reads_snippet_instead_of_embedding(pkg):
    """安装脚本不得再把正文写进 here-string：只准引用单一源。"""
    script = (_REPO_ROOT / "skills" / pkg / "install.ps1").read_text(encoding="utf-8-sig")
    # 三个脚本共用同一段插值模板，文件名由 $SkillName 决定
    assert "agents-md-snippet-$SkillName.md" in script
    assert "Get-Content -Path $snippet -Raw -Encoding UTF8" in script
    # PowerShell 把 `$SkillName:begin` 的冒号当作用域语法，插值成空串；必须花括号。
    assert "<!-- ${SkillName}:begin -->" in script
    assert "$SkillName:" not in script
    # 正文标题只允许出现在单一源里；here-string (@" ... "@) 已删除
    assert "@\"" not in script
    assert f"## {pkg}" not in script and "## 需求分析与拆解工作流" not in script


def test_snippet_missing_raises(snippets, monkeypatch):
    (snippets / "agents-md-snippet-test-cw.md").unlink()
    with pytest.raises(OSError, match="注入单一源"):
        mount.snippet_text("test-cw")


def test_snippet_bad_marker_raises(snippets):
    (snippets / "agents-md-snippet-test-cw.md").write_text("no markers", encoding="utf-8")
    with pytest.raises(ValueError, match="marker"):
        mount.snippet_text("test-cw")


def test_diff_reports_missing_unclosed_and_changed(snippets, tmp_path):
    dest = tmp_path / "AGENTS.md"
    dest.write_text("header\n\n" + mount.snippet_text("requirements-cw") + "\n", encoding="utf-8")
    problems = mount.agents_diff(dest)
    assert any("缺失注入段 code-review-cw" in p for p in problems)
    assert any("缺失注入段 test-cw" in p for p in problems)
    assert not any("requirements-cw" in p for p in problems)

    dest.write_text(
        mount.snippet_text("requirements-cw") + "\n" + "<!-- code-review-cw:begin -->\nstale\n",
        encoding="utf-8",
    )
    problems = mount.agents_diff(dest)
    assert any("未闭合 code-review-cw" in p for p in problems)

    dest.write_text(
        mount.snippet_text("requirements-cw").replace("- body", "- CHANGED")
        + "\n"
        + mount.snippet_text("code-review-cw")
        + "\n"
        + mount.snippet_text("test-cw"),
        encoding="utf-8",
    )
    assert any("内容不同 requirements-cw" in p for p in mount.agents_diff(dest))


def test_apply_is_idempotent_and_preserves_user_content(snippets, tmp_path):
    dest = tmp_path / "AGENTS.md"
    dest.write_text("# 用户自己的内容\n\n保留我\n", encoding="utf-8")
    assert mount.agents_apply(dest) == 3
    first = dest.read_text(encoding="utf-8")
    assert first.startswith("# 用户自己的内容\n\n保留我\n")
    for pkg in mount.PACKAGES:
        assert mount.snippet_text(pkg) in first
    mount.agents_apply(dest)
    assert dest.read_text(encoding="utf-8") == first  # 幂等
    assert mount.agents_diff(dest) == []


def test_legacy_gbk_file_is_readable(snippets, tmp_path):
    """旧 AGENTS.md 由 PowerShell 默认编码写成 GBK，不能因解码失败而假报漂移。"""
    dest = tmp_path / "AGENTS.md"
    dest.write_text("中文标题\n", encoding="gbk")
    assert mount._read_text_any(dest) == "中文标题\n"
    mount.agents_apply(dest)
    assert "中文标题" in dest.read_text(encoding="utf-8")  # 统一写回 UTF-8
    assert mount.agents_diff(dest) == []


def test_real_agents_md_has_backticks_restored():
    """真实缺陷回归：code-review 段的 `...` 标记必须存在于单一源。"""
    text = mount.snippet_text("code-review-cw")
    assert "`code-review-cw`" in text
    assert "`~/.codex/skills/code-review-cw/`" in text
