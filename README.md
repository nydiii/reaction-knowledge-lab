# 有机反应科学知识建模实训

让学生把有机合成文献中的信息，逐步变成**可关联、可检查、可修订、可追溯的知识库**。现有单篇入门实验之外，新增 **Suzuki 跨文献实验：4篇论文、40条选定结果记录**，包含真实图文抽取回放、跨论文融合和增量更新。

适合具备基础 Python 能力的本科生。必做实验使用普通电脑 CPU；**回放路径不需要 API Key，也不会产生模型费用**。真实调用路径使用学生自行配置的 DeepSeek API。

GitHub 仓库：[nydiii/reaction-knowledge-lab](https://github.com/nydiii/reaction-knowledge-lab)。

## 从这里开始

- **[跨文献批量操作手册](docs/BATCH_MANUAL.md)**：本次新增的主线，三篇初始导入，再加入第四篇；普通电脑、免费回放。
- **[教师人工核查表](docs/MANUAL_REVIEW.md)** · **[可填写回传单](docs/REVIEW_RETURN.md)**：尚待教师审校的化学内容与一键运行回传方法。
- **[H02逐项核查表](docs/H02_CHECKLIST.md)** · **[Excel可填写版](outputs/h02-20261113/H02-review.xlsx)**：40条记录逐项列出当前值、原文位置和资料链接，填写结果即可回传。
- **[H03产率差异核查教程](docs/H03_GUIDE.md)**：正文与SI的逐步对照方法、人工回传模板，以及可交给其他AI的完整任务说明。
- **[完整操作手册](docs/MANUAL.md)**：环境安装、下载资料、逐条命令、预期结果、常见问题。
- **[教师说明与参考答案](docs/TEACHER_GUIDE.md)**：验收标准、教学错误与讨论问题。
- **[数据和来源](docs/DATA_SOURCES.md)**：原文、固定版本、证据位置、已知抽取问题。
- **[实际验证记录](docs/VERIFICATION.md)**：测试平台、真实 API 用量、通过与未覆盖的范围。
- **[RXN Filter 选做](optional/rxn_filter/README.md)**：CPU 反应结构合理性筛查。

| 板块 | 方法或基础设施 | 本实验的可检查结果 |
|---|---|---|
| 信息抽取 | 单篇使用 ReactionSeek 原提示词；跨文献使用课程图文/JSON 适配；均提供真实响应回放 | 原始候选、模型信息、输入/提示词哈希 |
| 对齐与融合 | 借鉴 ReactionSeek 标准化流程；有来源的名称/结构缓存、RDKit、课程记录组织 | 别名关联到同一化合物，跨文献关联且独立保存实验结果 |
| 校验与更新 | 真实 ORD 校验库；课程参考核对、SQLite 版本与修订 | 区分规则和事实检查，查询随修订改变，历史可查 |

## 快速跑通

完成下方环境安装后，跨文献主线运行：

```bash
python -m reaction_knowledge_lab batch-demo --workdir runs/batch
python -m reaction_knowledge_lab batch-verify --workdir runs/batch
```

预期40条结果、4篇来源、10组跨文献相同转化。两处正文/SI冲突仍标为待核查，不能把软件通过理解为化学事实全部获确认。需要一键回传运行结果时：`python scripts/verify_student_setup.py --output runs/student-check`。

以下 `demo` 是原有单篇入门流程，`batch-demo` 是新增批量流程，两者分别保留。

下载本仓库 ZIP 或克隆后，进入包含 `pyproject.toml` 的目录。推荐 **Python 3.12**。

macOS / Linux：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps -e .
python -m reaction_knowledge_lab demo --workdir runs/demo
python -m reaction_knowledge_lab verify --workdir runs/demo
```

Windows PowerShell（无需修改脚本执行策略）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m reaction_knowledge_lab demo --workdir runs/demo
.\.venv\Scripts\python.exe -m reaction_knowledge_lab verify --workdir runs/demo
```

预期显示 `"passed": true`。重复验收使用 `verify`；重新做实验请使用新的工作目录，程序不会覆盖已有知识库。

第一次不下载原文也可完成离线回放；此时原文定位核对明确显示 `not_checked`。要核对证据、或进行真实 API 抽取，再运行：

```bash
python -m reaction_knowledge_lab fetch
python -m reaction_knowledge_lab check-evidence
```

下载器会获取固定 commit 的输入和提示词，并核对 SHA-256。依赖安装和资料下载需要网络，安装完成后的必做回放不联网。

## 单篇入门案例会看到什么

案例是 *Photoexcited Nitroarenes for the Anaerobic Cleavage of Alkenes*，Organic Syntheses 102:114–127 (2025)。[原文](https://www.orgsyn.org/demo.aspx?prep=v102p0114)

- 上游抽取只留下第一轮实验；原文还报告了第二轮。
- 两轮产物都是二苯甲酮、产率都是 72%，但质量分别是 2.63 g 和 2.62 g，不能按结构或产率去重。
- 课程明确注入一条 **27% 产率的教学错误**。它不是模型实际错误，且在合法数值范围内，单靠 ORD 规则无法识别。
- 学生核对原文后恢复 72%，补录第二轮；“产率 ≥70%”的查询条数依次为 **1 → 0 → 2**。
- 第二轮未逐项重述投料和条件：知识库保存它，但 ORD 完整反应检查会报告缺失。不能为让检查变绿而编造条件。

## Notebook

```bash
python -m pip install -r requirements-dev.lock.txt
python -m jupyterlab
```

按顺序打开：

1. [01_extraction.ipynb](notebooks/01_extraction.ipynb)
2. [02_alignment.ipynb](notebooks/02_alignment.ipynb)
3. [03_validation_update.ipynb](notebooks/03_validation_update.ipynb)
4. [04_cross_paper_batch.ipynb](notebooks/04_cross_paper_batch.ipynb)

这些 Notebook 默认不调用付费 API。测试执行与重跑目录说明见操作手册。

## 复现边界

这是**有限案例的模块复现与教学适配**，不是三篇论文全量指标复现。

- ReactionSeek：单篇使用固定原始提示词与公开真实输出；DeepSeek 替换 GLM 属模型适配。跨文献采用课程 JSON 提示词与图文输入，借鉴其抽取任务；结构缓存、保守单位规则和记录身份处理是课程改造，不冒称原始标准化脚本原样运行。
- ORD：运行 `ord-schema==0.9.6` 的真实导出与校验。它不会替你读取原文验证事实。
- SQLite、修订提案、原文参考比较、查询回归：课程新增代码。
- RXN Filter：保留原模型架构、特征与权重，适配独立 CPU 推理。分数只供筛疑。
- 参考记录由助手逐项对照公开原文建立，不是原作者提供的 gold，也不是化学专家独立审校。本案例只结构化有限字段；光照、气氛等完整实验信息仍需回看原文。

实际曾用 DeepSeek 对主案例调用一次，输入 7,279 / 输出 113 tokens，按 2026-11-10 官方高峰价估算 0.015462 元。真实响应和用量见 [回放记录](data/replay/deepseek_20261110.metadata.json)。每次 API 结果可能变化，不能要求它与固定回放逐字相同。

## 论文、代码与许可

- [ReactionSeek，Nature Communications 2026](https://www.nature.com/articles/s41467-026-70180-1) · [原代码](https://github.com/DeepSynthesis/ReactionSeek)
- [The Open Reaction Database，JACS 2021](https://doi.org/10.1021/jacs.1c09820) · [原代码](https://github.com/open-reaction-database/ord-schema)
- [ChemEnzyRetroPlanner，Nature Communications 2025](https://www.nature.com/articles/s41467-025-65898-3) · [原代码](https://github.com/wangxr0526/ChemEnzyRetroPlanner)

本仓库新增代码采用 [MIT](LICENSE)。第三方来源、许可与数据分发边界见 [THIRD_PARTY.md](THIRD_PARTY.md)。API 密钥、下载的完整原文、模型权重、个人运行结果均不纳入 Git。
