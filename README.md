# cw-alm · Call Warden ALM 交付层

把「需求 → 契约 → 验收 → 证据」这套 ALM 方法与 callwarden 治理环的**客户端交付层**收成
一个独立仓，供多个宿主（WorkBuddy / Codex / Claude Code / Trae CN）与多个项目共用。

**仓库 = 源，宿主 = 投影。** 任何挂载点与仓库不一致，`tools/mount.py --check` 会报 2。

## 为什么独立成仓

这些内容原先散在 callwarden 仓的 `skills/` 下，只有该仓能用：换一个项目要手抄，换一个
宿主再抄一遍，抄完两边就开始漂。同目录的 `agent-commons` 就是这个状态的样本——它与派生出的
专家包靠人工拷贝维持，副本晚一天生成，当前一致纯属运气。

## 目录

```
cw-alm/
├── kernel/cw-gates.md          门禁唯一事实源（G1–G6），安装期注入各包，包内不留副本
├── skills/
│   ├── requirements-cw/        需求端 R0→R4（澄清→可视化→符号锚定→契约卡→注入）
│   ├── code-review-cw/         审查端（图谱选靶→只读审查→建单，PASS/BLOCKED）
│   └── test-cw/                验收端（六条件判据 + 八段证据 + 冻结冒烟集）
├── experts/callwarden-alm/     WorkBuddy 专家团：6 人格 + plugin.json + 头像
├── tools/
│   ├── check_packages.py       结构自检（frontmatter / references / 门禁单一源 / smoke / 注入）
│   └── mount.py                挂载与漂移检测（--check / --apply）
├── tests/test_packages_guard.py  自检器单测（20 例，hermetic fixture）
├── smoke.target                一行：smoke.txt 的路径基准仓（见下）
└── README.md
```

## 与 callwarden 仓的边界

| 内容 | 所在 | 为什么 |
|---|---|---|
| 本仓：内核、三个客户端技能包、专家团、挂载工具 | `cw-alm` | 与 daemon 无代码耦合，可跨宿主/跨项目复用 |
| `.agents/skills/*`（角色环协议） | **callwarden** | 被 `tests/test_role_prompt_skill.py` 跨产物契约锁定：与 4 份 role 模板、`AGENTS.md`、`docs/agent-usage-guide.md`、`scripts/validate_template_compliance.py` 同源校验。搬走会让该门禁退化成假门禁 |
| daemon / RPC / error code | **callwarden** | 服务端行为 |

人格文件里对角色技能的引用是**活体路径引用**（指向 callwarden 仓），不复制副本——
与 `novel-architect` 引用 `C:\git_work\大纲` 的做法一致：改了原著，约束自动同步。

## 挂载矩阵

| 宿主 | 落点 | 命令 |
|---|---|---|
| WorkBuddy 技能 | `~/.workbuddy/skills/<pkg>/` | `python tools/mount.py --apply --host skills` |
| WorkBuddy 专家团 | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/callwarden-alm/` + `plugins/cache/my-experts/callwarden-alm/<ver>/` | `python tools/mount.py --apply --host expert` |
| OpenAI Codex | `~/.codex/skills/<pkg>/` + `~/.codex/AGENTS.md` 注入段 | `powershell -File skills/<pkg>/install.ps1` |
| Claude Code | `~/.claude/skills/<pkg>/` | 同上 |
| Trae CN | `~/.trae-cn/skills/<pkg>/`（目录存在才装） | 同上 |

专家团必须**两处都写**：应用实际加载的是 `cache/` 副本，只写 `marketplaces/` 不生效。
`mount.py` 已按 `plugin.json` 的 version 自动算出 cache 目录名。

## 校验

```bash
python tools/check_packages.py          # 结构自检，三态 0/2/64
python -m pytest tests/ -q              # 20 例守卫单测
python tools/mount.py --check           # 漂移检测，0=一致 2=漂移 64=用法错
python tools/mount.py --check --json    # CI 解析用
```

专家包另有官方校验器，但它要求包**位于专家市场目录下**，故只能对挂载点跑：

```bash
python <expert-manager>/scripts/validate_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/callwarden-alm
```

## 跨仓依赖：`smoke.target`

`skills/test-cw/references/smoke.txt` 是一份 **FROZEN** 冒烟集（2026-11-22 r2 签字，
6 文件 / 167 例），里面记的是 **callwarden 仓**的测试文件路径。技能包搬到这里后不再与那些
文件同仓，若仍按本仓根解析会把正常跨仓引用全判成断链。

因此用仓库根一行 `smoke.target`（当前为 `../callwarden`）声明基准仓。目标仓不存在时自检器报
`SMOKE_TARGET_MISSING` 并以 2 退出——**不静默跳过**，因为 smoke 是「所有 AC 全绿但主链路已断」
的唯一兜底。声明独立成文件，是为了不改动那份冻结资产。

## 已知债务

1. **两个挂载入口**：`mount.py` 管 WorkBuddy，`install.ps1` 管另外三个宿主。宿主集合互不重叠，
   所以内容仍是单一源；但收敛成一个入口更好——届时把各包 `install.ps1` 里的 AGENTS.md 注入段
   抽成 `references/agents-md-snippet.md`，两边都读它。
2. **专家包版本号停在 1.0.0**：没有安装/更新脚本驱动真实升级，只改 `plugin.json` 版本号会
   制造「市场注册表 vs 包」的静默不一致。
3. **设计溯源留在 callwarden 仓** `.design/skillpkg-guard/` 与 `.design/parking-lot.md`：
   那是该仓的历史记录，不随代码迁移。
