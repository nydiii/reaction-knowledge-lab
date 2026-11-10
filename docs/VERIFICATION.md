# 实际验证记录

验证日期：**2026-11-10**。这是课程有限案例的运行记录，不是原论文全量基准复现，也不是任意化学文献的自动处理能力证明。

## 1. 已实际运行的环境

- macOS，Apple Silicon / arm64，CPU。
- Python **3.12.15**。
- 核心环境按 [`requirements.lock.txt`](../requirements.lock.txt) 安装；开发环境另按 [`requirements-dev.lock.txt`](../requirements-dev.lock.txt) 安装。
- ORD **0.9.6**，RDKit **2026.9.1**，protobuf **5.29.6**。
- 另建全新虚拟环境，仅用 `pip` 安装核心锁定依赖和本项目，再运行 `demo`；15 项验收全部通过。核心路径不需要 PyTorch、Jupyter 或 API。

发布后已在 GitHub Actions 的 **Windows、macOS、Ubuntu** 托管 runner 上完成核心安装、测试、离线 `demo` / `verify` 和三本 Notebook，全部通过。[成功运行记录](https://github.com/nydiii/reaction-knowledge-lab/actions/runs/42810087211)对应代码提交 `c4886c7`；可下载 [CI 摘要](examples/github-ci.json)。这些结果不等于每一种学生电脑都已测试，也不包含 RXN Filter 选做。推荐 Python 3.12；`pyproject.toml` 的兼容范围不等于每个 Python 版本都已测试。

## 2. 验证结果

| 检查 | 实际结果 | 证明的范围 |
|---|---|---|
| 本机核心自动测试 | **46 passed** | 解析、对齐、保守单位处理、ORD 接口、来源检查、版本修订、幂等、事务回滚和终端编码 |
| GitHub Actions 三系统 | 每个系统 **45 passed, 1 skipped**；流程与 Notebook 全通过 | CI 不下载完整原文，因此跳过 1 项原文定位测试；不是将跳过算作通过 |
| `demo` / `verify` | **15 / 15 通过**，API 调用 0 | 同一案例从真实回放到可查询、可修订资源 |
| 原文证据检查 | **13 处短证据定位通过** | 固定输入版本、原文片段位置及哈希；不是通用事实证明器 |
| 分步命令行流程 | 手册主线运行成功 | 初始建库、教学错误、来源复核、修订、查询和导出 |
| Notebook | **3 本、25 个代码单元、0 执行错误** | 按顺序运行的默认免费路径；8 项 Notebook 验收通过 |
| 独立干净环境 | 核心安装与 15 项验收通过 | 无开发依赖的 CPU 路径 |
| 发布包独立解压 | 禁止网络连接后 15 项验收通过，API 调用 0 | 未携带原开发环境或下载目录也可回放；原文定位明确为 `not_checked` |
| 依赖一致性 | `pip check` 无冲突 | 本次安装环境的依赖声明 |
| RXN Filter 选做 | **3 项测试通过**，真实权重 CPU 推理成功 | 原始模型结构与指纹的独立推理适配 |

可查看随仓库保存的 [demo 验收快照](examples/demo-verification.json)。它是发布者的一次运行记录；学生自己的结果应保存在自己的 `runs/` 中。源 Notebook 不带执行输出，执行器会另存含输出的副本。

首次 Windows CI 暴露了默认 `cp1252` 编码不能输出中文的问题。现已将 CLI 和 Notebook 执行器的输出设为 UTF-8，并增加回归测试，覆盖结果打印、错误提示和拒绝覆盖旧目录；修复后第二轮三系统检查全部通过。

## 3. 必做路径的关键可观察结果

主案例是 Organic Syntheses 102:114–127 (2025)，来源及固定版本见 [数据说明](DATA_SOURCES.md)。最终保留两个实验：

| 记录 | 产物 | 质量 | 分离产率 | qNMR 纯度 |
|---|---|---:|---:|---:|
| `orgsyn-102-0114-run-1` | 二苯甲酮，`pubchem:3102` | 2.63 g | 72% | 99.8% |
| `orgsyn-102-0114-run-2` | 二苯甲酮，`pubchem:3102` | 2.62 g | 72% | 98.6% |

两条记录关联同一产物实体，但没有合并为同一次实验。

1. 原始抽取只提供第一轮。初始“产率 ≥70%”查询有 **1** 条。
2. 明确注入教学错误，把第一轮 72% 改为 27%。查询变为 **0** 条。这不是模型实际犯过的错误。
3. 对照来源修订为 72%，补录第二轮和纯度信息。查询变为 **2** 条。
4. 第一轮历史仍能查到 **72 → 27 → 72**。重复提交同一个 patch 返回 `already_applied`，不会再次增加版本。
5. 第二轮没有独立重述的投料和条件仍保持未知。ORD 完整性检查会标出该记录；它仍保留在知识库中。

因此，“知识库保存了有来源的记录”与“记录满足 ORD 完整反应结构要求”是两个验收问题。`ord_structurally_ready.json` 只有第一轮；仍需阅读警告，不能将文件名理解为已经获得训练质量认证。`source_reference_agreement` 也只表示与本课程有限参考字段一致。

## 4. 一次真实 DeepSeek 调用

调用对象仅主案例一篇，使用固定 ReactionSeek 提示词，适配 `deepseek-flash`，关闭思考模式。原始回答、用量、模型和提示词哈希见 [实测元信息](../data/replay/deepseek_20261110.metadata.json)。

| 项目 | 实测或估算 |
|---|---:|
| 请求次数 | 1 |
| 输入 tokens | 7,279 |
| 输出 tokens | 113 |
| 总 tokens | 7,392 |
| 按当日官方高峰价估算 | **0.015462 元** |

估算采用输入 2 元 / 百万、输出 8 元 / 百万，不等同于账户账单实扣证明；[官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)可能变化。后续免费回放、测试与 Notebook 没有再次发起付费调用。

此次输出仍漏掉第二轮，并把原文温度区间 30–35°C 写成 35°C。后续来源比较确实识别出温度差异。因此不能把一次成功请求理解为模型结果正确，也不能据此断言 DeepSeek 优于上游 GLM。

## 5. RXN Filter 选做实测

选做采用独立环境：Python 3.12.15、PyTorch 2.8.0、RDKit 2025.3.6、NumPy 2.2.6，使用 CPU。模型和源码版本、下载校验值见 [provenance.json](../optional/rxn_filter/provenance.json)。

- 主案例反应结构分数：**0.8016688228**。
- 阈值 0.5 时不标记；阈值 0.9 时标记待核查。分数相同，改变的是决策阈值。
- 上游示例结构分数：**0.9940396547**。
- 官方模型下载在本环境超时；实际使用显式镜像下载并核对压缩包及权重 SHA-256。仓库不附带权重。

该模型不检查产率、文献证据或条件，也不自动修订知识库。不得因为它打低分就删除有实验依据的记录。

## 6. 学生如何重复检查

在已安装开发依赖的仓库根目录运行，工作目录须为新目录：

```bash
python -m pytest -q
python -m reaction_knowledge_lab demo --workdir runs/check-my-install
python -m reaction_knowledge_lab verify --workdir runs/check-my-install
python scripts/run_notebooks.py --workdir runs/check-my-notebooks --output-dir runs/check-my-notebooks-executed
```

未下载原文时，离线路径仍可运行，但证据定位显示 `not_checked`，相关源文件测试明确跳过。若要重复 13 处原文定位检查，先运行 `fetch`，再执行 `check-evidence`。不要把 `not_checked` 写成“原文已核验”。

手册逐步路径与 Notebook 各自保存结果。CLI 的 `verify` 专用于 `demo` 生成的目录，不能直接拿它验收任意手工拼装的目录。

## 7. 本次没有覆盖什么

- 原论文全量数据、指标、训练过程和消融实验。
- 任意有机反应名称、任意单位或复杂条件程序的自动归一。
- 化学专家独立审校或大规模人工金标准；参考由助手逐项对照原文建立。
- 光照、气氛、装置等全部实验条件的结构化。
- 自动从新原文生成可信修订；课程 `source-review` 只是基于固定参考生成提案，仍要求阅读证据。
- 学生个人电脑的全部系统版本和环境；RXN Filter 选做的 Windows / Linux 运行。

本实验的验收目标是让学生观察并完成一条可复查的数据处理链，而不是获得无需人工审查的化学事实数据库。
