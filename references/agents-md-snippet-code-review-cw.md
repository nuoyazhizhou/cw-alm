<!-- code-review-cw:begin -->
## Code Review 工作流（code-review-cw 技能）

- 任何代码审查请求（"review 这个 PR / diff / 模块 / 提交"），使用 `code-review-cw` 技能（位于 `~/.codex/skills/code-review-cw/`，先读其 SKILL.md 再行动）：先图谱驱动选靶，再只读审查出带优先级的报告；每个需动作的发现建为 callwarden 任务单，全部建单完成后才统一修复，四阶段严格串行。
- callwarden MCP 工具不可用时，按技能内「工具不可用兜底」降级为纯审查模式，并如实声明任务单未推进。
<!-- code-review-cw:end -->
