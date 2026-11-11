# 有机反应科学知识建模实训规格

## 2026-11-11 批量扩展（用户已授权实施和验证）

- 保留原单篇入门流程；新增 `batch-*` 命令、第四本Notebook、跨文献手册及人工回传表。
- 实际已取得4篇Suzuki论文，选定40条结果：NC2019 16条、NC2022 13条、JACS2024 4条、NC2025 7条；最后一篇作增量留出。原8–10篇是扩展目标，不宣称已达成。
- 4次真实DeepSeek图文调用结果原样保存供免费回放；不是ReactionSeek原提示词/基准原样复现。来源文件、选页、原图和prompt哈希可重建。
- 化合物通过保守别名字典与明确结构标识关联；转化按反应物多重集与产物分组；不同文献/条件记录不去重。催化剂样品带来源限定标识。
- JACS产物8为五次合并结果，不能拆成五条93%。ORD原生量不混用单次投料与五次总产物，完整信息仍保存于课程metadata。
- NC2025 4s、4v分别存在89/80与98/99的来源冲突；单一产率为空，双方说法保留等待审校。
- 新增幂等且事务化的增量导入，同ID不同内容拒绝覆盖；重新导入已处理批次不会冲掉修订。
- 软件验收与科学审校分开；真实文件完整性、ORD诊断、查询回归、同物异名、同产物不同原料、来源冲突、合并量和历史分别检查。
- 实际测试范围、学生命令与教师回传材料见BATCH_MANUAL.md、MANUAL_REVIEW.md和VERIFICATION.md。

以下是仍保留的原单篇实验规格。

用户已于 2026-11-10 确认三板块、CPU、本科生、中文逐步手册、真实 API 与真实结果回放两条路径，并授权开始制作。

## 目标与边界

同一资料贯穿 ReactionSeek 信息抽取、化合物标识关联与独立实验记录组织、ORD 规则校验、原文核对、可追溯修订与查询更新。必做案例为 Organic Syntheses 102:114–127 (2025)，DOI 10.15227/orgsyn.102.0114；其两次实验各自保留。其余四篇上游样例作为尚未逐条来源核对的扩展素材，不宣称为已验证知识。

代码固定使用 ReactionSeek commit 6d42c4a1c5e47e1a5544b67a5b3ce9b00dbf8f6a 的提示词与真实输出作为起点。DeepSeek 替换原 GLM 调用属于模型适配；单位规则、记录分层、SQLite、原文核对与修订为课程实现。ORD 使用真实 ord-schema 0.9.6。RXN Filter 为独立可选实验。

## 环境、结构、命令

- Python 3.12，CPU；当前主机实际验证 macOS arm64，核心流程已通过 GitHub Actions 的 Windows、macOS、Ubuntu 检查；具体范围见 docs/VERIFICATION.md，未跑过的选做和环境不标已验证。
- 包：`src/reaction_knowledge_lab/`；资料：`data/`；教程：`docs/`、`notebooks/`；验证：`tests/`。
- `python -m pip install -e ".[dev]"` 安装；`python -m reaction_knowledge_lab demo --workdir runs/demo` 回放全过程；`python -m pytest` 验收。
- 分步命令：`fetch`、`extract --mode replay|api`、`align`、`validate`、`build`、`query`、`revise`、`verify`；所有输出写到用户指定目录。
- JSON UTF-8，函数与字段 snake_case；原字段与归一值并存；不得把未知写成零，把温度区间平均化，或把 overnight 固定成时长。

## 模块与依赖

| 模块 | 输入 | 输出 | 验收 |
|---|---|---|---|
| extraction | 固定上游资料/提示词；或真实回放 CSV | 原始反应候选、运行信息 | 回放逐字对应上游；真实 API 保存 usage、模型、提示词哈希 |
| alignment | 候选及有出处的名称/结构缓存 | 统一化合物、独立记录 | 别名关联；不同实验不按相同 SMILES 合并；不猜测未解析名称 |
| validation | 记录、课程参考、原文证据定位 | ORD 导出与诊断、参考差异 | 发现漏掉第二次实验、错误事实；规则通过不等于文献一致 |
| revision | SQLite 资源、含依据的修订 | 新版本和旧版本、重新查询 | 修订有依据；重放不重复插入；查询随有效修订改变 |

## 最小记录契约

文件为 `{"schema_version": 1, "records": [...]}`。一条记录示例结构：

```json
{
  "record_id": "orgsyn-102-0114-run-1",
  "source_id": "volume102article22",
  "raw_record_id": "volume102article22_1_1",
  "experiment_label": "run-1",
  "status": "extracted",
  "inputs": [{"name":"1,1-diphenylethene", "role":"reactant", "entity_id":"...", "smiles":"...", "amount":{"value":20.0,"unit":"mmol"}, "raw_amount":"3.61 g (20.0 mmol)"}],
  "solvents": [{"name":"acetonitrile", "entity_id":"...", "smiles":"CC#N"}],
  "product": {"name":"Benzophenone", "entity_id":"...", "smiles":"...", "mass_g":2.63, "yield_percent":72.0, "purity_percent":null},
  "conditions": {"raw_time":"36 hours", "time_minutes":2160.0, "raw_temperature":"30-35°C", "temperature_c":{"min":30.0,"max":35.0}},
  "source": {"doi":"10.15227/orgsyn.102.0114", "url":"https://www.orgsyn.org/demo.aspx?prep=v102p0114", "locator":"Procedure; first run"},
  "notes": [],
  "raw": {}
}
```

第二次实验原文没有逐项重述条件/投料：空 inputs、null 时间与温度并说明未重述；保留与同一 procedure 的关联，不能伪装成独立报告事实。字段出处放在课程参考/patch 的 evidence；未来源核对的抽取记录保持 extracted 状态。

`data/reference/case22.json` 格式：`{"source_id":..., "records":[与上述契约一致的按原文核对的课程参考记录], "evidence":[{"record_id":...,"field":点路径,"source_id":...,"start":整数,"end":整数,"text":短片段}], "procedure_sha256":...}`。`data/reference/aliases.json` 格式：`{"entities":[{"entity_id":稳定ID,"preferred_name":...,"aliases":[...],"smiles":...,"pubchem_cid":整数或null,"sources":[URL]}]}`。

## 测试与成功标准

1. 无 API 密钥也能从分发的真实回放结果跑通必做流程；无自动网络调用。
2. 安装后能下载固定上游文件并核 SHA-256；完整原文不重新授权或冒充原创。
3. 同物异名指向同一实体；run-1 与 run-2 共享实体但记录 ID 不同；第二轮缺失条件保持未知。
4. 校验器发现上游漏抽 run-2；修订后实验数从 1 变 2，质量查询显示 2.63g 与 2.62g。
5. 明确标记的教学错误（如把第一轮产率写为 27%）在 ORD 范围校验后仍能被原文参考检查发现；恢复 72% 后对应查询同步改变。
6. 修订前后均可读取；重复应用同一 patch 不制造新版本；错误 patch 不留下部分修改。
7. 原值、来源、修订证据可查询；密钥不进入仓库、Notebook 输出、日志或发布包。
8. 真正运行 ORD 与 Notebook；记录实际平台、依赖、结果；API 实测预算最多 1 元估算高峰价，未验证部分明确标注。

## 不在范围内

不训练大模型、不做湿实验、不部署完整自动实验室、不复现论文全数据指标、不宣称结构合理性得分可验证实验事实。不建设额外网页产品。GitHub 发布前需要明确目标账户及仓库可见性；先完成可审阅的本地仓库。
