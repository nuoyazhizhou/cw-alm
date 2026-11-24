<!-- requirements-cw:begin -->
## 需求分析与拆解工作流（requirements-cw 技能）

- 模糊需求、新功能、新项目、技术选型、需求拆解类请求，使用 `requirements-cw` 技能（位于 `~/.codex/skills/requirements-cw/`，先读其 SKILL.md 再行动）：R0 澄清 ≤3 轮 → （新项目）技术栈选型门禁 → 可视化 → 符号锚定 → contract 卡片 + 设计门禁 + 基线冻结 → 注入 callwarden 任务单 → 开发 → 收口与 feature 级验收。
- 每个评审门禁必须产出四件套（方案对比 ≥2 / 被否决理由 / 异常场景矩阵 8 类 / 未决项三态），hotfix 豁免须满足单文件 + 无新增符号 + 已有测试覆盖三条。
- 追溯主线：REQ 编号 → 卡片 → task_id → AC → 证据（`.design/<feature>/evidence/`）。证据缺失即验收不通过。
- 已有代码的审查交给 `code-review-cw`，不要用本技能。
- callwarden MCP 不可用时，只做 R0-R3 出方案并如实声明"未建单、未验收"，不得假称已建单或已闭环。
<!-- requirements-cw:end -->
