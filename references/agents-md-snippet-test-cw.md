<!-- test-cw:begin -->
## 测试验收工作流（test-cw 技能）

- 遇到"跑测试 / 验收 AC / 回填证据 / 执行 test-plan"类请求，使用 `test-cw` 技能（位于 `~/.codex/skills/test-cw/`，先读其 SKILL.md 再行动）：读 `ac-map.md` → 三源反查选最小充分测试集 → 本地批跑并留 junit → 六条件判据 → 写 `evidence/<AC-id>.md` → 缺口与失败按 REQ 建单。
- 判据不许只看 `rc=0`：required nodeid 必须全 passed、required 集 skip/xfail 必须为 0、`collected` 必须等于 required 数。
- `N/A` 只在 `test-plan.md` 执行前标 `level=manual` 时合法；`GAP`（可自动化但无测试）判 FAIL 并建 P1 单。
- 不写测试、不修代码、不 retry 刷绿、不改断言让红变绿；不执行 apply/close。
- 证据骨架必须由 junit 解析生成，禁止手抄 nodeid 表。已有代码审查交 `code-review-cw`，需求拆解交 `requirements-cw`。
<!-- test-cw:end -->
