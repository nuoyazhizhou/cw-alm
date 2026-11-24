# Call Warden ALM 治理交付团

把一条 callwarden 需求从澄清推到关单：需求拆解 → 冻结实现 → 独立评审 → 验收取证 → 裁决关单，全程可追溯。

## 类型

Team 型（多角色协作团队，6 成员）

## 功能

本团把 callwarden 已有的四角色治理（planner / executor / reviewer / adjudicator）与三个客户端技能包（需求端 / 审查端 / 验收端）编成一条串行交付链：

| 阶段 | 成员 | 做什么 | 门禁 |
|---|---|---|---|
| Phase 0 | 钟守一（主理人） | 声明三元组、核 daemon 三元绑定、核技能就位、预判评审独立性 | G1/G2 |
| Phase 1 | 蓝图远 | 需求澄清 → 符号锚定 → contract 卡片 → 建单 | 评审四件套 + 基线冻结 + G6 建单形状 |
| Phase 2 | 郑兑现 | 冻结 scope 内实现、回归、逐步上报 | scope 不越界 + 产物核验 |
| Phase 3 | 柯明察 | 调用图选靶、只读审查 | 只输出 PASS / BLOCKED + 身份独立 |
| Phase 4 | 纪有据 | 选集执行、六条件判定、八段证据 | 六条件判据 |
| Phase 5 | 裴定论 | lease 核验 → apply → close | lease 三元组 + 状态复读 |
| Phase 6 | 钟守一 | 汇编 REQ → 卡片 → task_id → AC → evidence 追溯矩阵 | 断链即"未闭环" |

## 依赖（重要）

本专家团**不内嵌技能包**，依赖以下用户级技能已安装：

```
~/.workbuddy/skills/requirements-cw
~/.workbuddy/skills/code-review-cw
~/.workbuddy/skills/test-cw
```

每个包内必须有 `references/cw-gates.md`（由安装器从仓库 `skills/_shared/cw-gates.md` 注入，是 G0-G6 门禁的唯一事实源）。安装/更新命令：

```bash
python skills/_shared/install_skill_to_workbuddy.py
```

不内嵌是刻意的：门禁只有一份事实源，避免包内副本随仓库演进漂移。

成员还引用仓库内的角色技能：`.agents/skills/{cw-planner-architect,cw-executor-senior-engineer,cw-task-loop}`。这些是 Codex 约定的项目级技能，WorkBuddy 不会自动加载，成员按需读取其 `SKILL.md`。

## 边界（不承诺的事）

- **专家团是人格层，不是权限层**。成员 spawn 后必须各自注册 daemon 身份（`agent.register`，`agent_instance_id` 非空），才能 claim / lease。
- **不绕过任何门禁**。跳过 G1-G6 会让证据链失效，本团明确拒绝这类请求。
- **reviewer 与 executor 身份必须不同**（`agent_instance_id` 和 `session_id` 都要不同），否则 daemon 的角色独立性门禁会拒绝认领。

## 使用示例

- 我要给 callwarden 加一个新功能：先做需求澄清和任务拆解，再实现、独立评审、验收取证，最后按 daemon 治理关单。
- 审查 callwarden 最近的改动：用调用图选靶，输出分级报告，并把要动作的发现建成任务单。
- 对某个 AC 跑验收：选最小充分测试集，按六条件判定，补齐八段证据。

## 头像

已生成在 `avatars/` 下。替换要求：PNG/JPG，512×512 px，单张 ≤500KB。

## 安装

专家包必须位于专家目录才能被检测到：

```
C:\Users\wanpi\.workbuddy\plugins\marketplaces\my-experts\plugins\callwarden-alm\
```

注册使其可见：

```bash
python scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python scripts/package_expert.py <expert-dir>
```
