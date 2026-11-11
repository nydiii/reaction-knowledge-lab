# Suzuki 跨文献实践操作手册

本实验把 **4 篇原始论文的 40 条选定结果记录**串成同一条流程。入门单篇实验继续保留在 [MANUAL.md](MANUAL.md)。本实验使用普通电脑 CPU；模型调用在云端完成，默认回放不联网、不收费。

当前是可运行、待教师科学审校的教学版本。40 条不是 40 次独立湿实验，也不是四篇论文的全部反应。两条来源冲突不被强行消除；一条记录是五次反应的合并结果。目标是实践知识建模，不是在实验室执行化学合成，也不在本课训练预测模型。

## 1. 方法和资料如何连接

| 环节 | 输入 | 方法与学生动作 | 输出 | 验收 |
|---|---|---|---|---|
| 信息抽取 | 原始反应图表、SI 选页、正文方法段 | 借鉴 ReactionSeek 的字段抽取思路，使用课程 JSON 提示词和 DeepSeek 图文输入；或回放已保存真实响应 | 带 source_id 和文内标签的候选记录 | 检查模型是否读错取代位置、是否混淆图与脚注 |
| 对齐与融合 | 候选结果、可审查实体字典 | 精确别名匹配、RDKit 结构标准化、时间/质量单位整理、独立记录入库 | 化合物关联、转化分组、SQLite 知识库 | 相同底物与产物的转化能跨论文连接，实验记录不会因此消失 |
| 校验与更新 | 知识库、原图和 SI、课程参考 | 实体/结构一致性检查、ORD 校验、原文核对、带证据修订、第四篇增量入库 | 历史版本、查询变化、未解决冲突 | 修订有历史；重复导入不增行；疑点仍可追溯 |

这是 **ReactionSeek 任务思路的图文与格式适配**，不是原提示词、原模型或论文基准的原样复现。旧单篇路径仍保留固定 ReactionSeek 原提示词和公开输出。ORD 使用真实 `ord-schema==0.9.6`；实体字典、融合、SQLite、修订和参考答案都是课程代码/资料。

## 2. 文献批次与抽取范围

| source_id | 论文 | 选取范围 | 记录数 | 导入顺序 |
|---|---|---|---:|---|
| nc2019 | [Palladium-bearing intermetallic electride…，Nature Communications 2019](https://doi.org/10.1038/s41467-019-13679-0) | 正文 Table 1 的 15 项；SI PDF 第48页 Table S6 的1项 | 16 | 首批 |
| nc2022 | [Building up libraries and production line for single atom catalysts…，Nature Communications 2022](https://doi.org/10.1038/s41467-022-33442-2) | 正文 Fig.6 a–m；图注和 Methods 条件 | 13 | 首批 |
| jacs2024 | [ProPhos…，JACS 2024](https://doi.org/10.1021/jacs.4c00370) | SI PDF 第121–122页的7、8、30、31；第119页通用过程供核查 | 4 | 首批 |
| nc2025 | [Defying the oxidative-addition prerequisite…，Nature Communications 2025](https://doi.org/10.1038/s41467-025-58579-8) | 4a-Cl、4c-Cl、4c-Br、4q-Br、4r-Br、4s-Br、4v-Br；SI第26、46、49、50页 | 7 | 留出，后导入 |

这一批实际形成 **10 组跨文献相同转化、24 个跨文献共同实体**（实体数包括溶剂/试剂，不全是反应物）。例如 nc2019-t1-9、nc2022-f6-a、nc2025-4q-Br 都是对溴甲苯＋苯硼酸→4-甲基联苯，条件和催化剂不同，保存三条记录。

反例：nc2022-f6-g 同样得到4-甲基联苯，但使用溴苯＋对甲基苯硼酸。它与 f6-a 共享产物，**不共享本课定义的完整转化**。转化键使用“已解析反应物多重集＋产物”，不是机理、原子映射或实验身份。

原先设想的8–10篇是扩展目标。当前完成的是上面4篇/40条；OrgSyn 2026 和 ChemComm 2016 仍列在 manifest 的 `pending_candidates`，不计入上述成果。

## 3. 环境安装

先安装 Python 3.12，下载/克隆本仓库，进入有 `pyproject.toml` 的目录。仓库仍是私有的，学生需要仓库访问权限或教师提供的发布 ZIP。

macOS / Linux：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps -e .
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

下文统一使用 `python`。Windows 无需激活环境：把每条命令开头的 `python` 替换成 `.\.venv\Scripts\python.exe`。批量新增 PDF 依赖 `PyMuPDF==1.28.2` 已写入锁定文件。安装需要网络，安装后的回放不需要网络。

## 4. 先一键检查，再分步实践

```bash
python -m reaction_knowledge_lab batch-demo --workdir runs/batch-demo
python -m reaction_knowledge_lab batch-verify --workdir runs/batch-demo
```

预期 `passed: true`。目录不能已经有结果；重新实验换一个新目录。`batch-verify`只适用于 `batch-demo` 产生的目录，不是任意手工工作目录的验收器。

一键流程自动完成真实回放、对齐、三篇初始入库、参考修订、明确标记的教学错误与恢复、第四篇增量导入、重复导入、ORD导出。它是软件自检；分步练习时学生应亲自看证据再应用 patch。

| 输出 | 应观察到什么 |
|---|---|
| raw.json、raw.metadata.json | 40条真实模型候选；当前 API 调用0 |
| aligned.json、aligned.alignment.json | 统一标识、原始字段、未解析名称清单 |
| initial.json、holdout.json | 首批33条、留出7条 |
| initial-differences.json | 与课程参考的差异；包含表述/格式差异，不能把差异条数直接当模型错误率 |
| knowledge.sqlite | 4篇40条最终记录，历史和修订证据 |
| query-regression.json | 产率≥90%的查询：29→28→29（加入第四篇之前） |
| incremental.json | 新增7条；再次导入返回 already_ingested，新增0条 |
| validation/ord.json | 真实ORD导出；合并结果避免混用单次投料与总产物量 |
| validation/validation.json | ORD诊断、来源比较、实体结构规则，分别报告 |
| verification.json | 软件验收结果及跨文献分组；不代表教师审校已完成 |

**教学错误**是把 nc2019-t1-9 的95%改成27%，再根据原图恢复95%。它不是原作者或模型真实犯过的错误。真实模型错误和未解析名称保留在 raw/aligned 文件中。

## 5. 获取并核对原始资料

```bash
python -m reaction_knowledge_lab batch-fetch
python -m reaction_knowledge_lab batch-check-evidence
```

下载11个官方来源文件：4份全文XML、4份SI PDF、3张原图，保存在 `data/downloads/batch/`，不会提交到Git。清单、直接下载URL和SHA-256见 [sources.json](../data/batch/sources.json)。每个文件都检查哈希；下载失败不会把验证页当论文保存，也不会覆盖已有不同版本。

`batch-check-evidence` 的 `verified` 证明文件、选页/段落和真实回放的输入提示词可重建；**不证明图中结构或化学含义正确**。未下载时显示 `not_checked`，回放仍可进行。

若某个网站被校园网拦截，在浏览器打开 manifest 对应的 `url`，另存到指定目录并保持 `name`，再运行以上命令。哈希不一致时不要修改清单强行通过：保留文件并在核查表注明，以便判断是否出版社更新。原文不随仓库重新分发；离线机可以从有网络的电脑复制同名文件后校验。

## 6. 分步做抽取、关联、融合

使用新的 `runs/batch-manual` 路径。

```bash
python -m reaction_knowledge_lab batch-extract --mode replay --output runs/batch-manual/raw.json
python -m reaction_knowledge_lab batch-align --input runs/batch-manual/raw.json --output runs/batch-manual/aligned.json
python -m reaction_knowledge_lab batch-build --input runs/batch-manual/aligned.json --exclude-source nc2025 --db runs/batch-manual/knowledge.sqlite
python -m reaction_knowledge_lab batch-query --db runs/batch-manual/knowledge.sqlite --output runs/batch-manual/groups-before.json
python -m reaction_knowledge_lab query --db runs/batch-manual/knowledge.sqlite --name "benzeneboronic acid" --output runs/batch-manual/alias-query.json
```

阅读 `aligned.alignment.json`。本次真实模型在NC2019 Table1有结构识别错误，字典外名称也会留作未解析；不能为了减少警告把未知名称都映射到“最相近”化合物。结构字典在 [entities.json](../data/batch/entities.json)，49个实体由原图/名称人工式转录并经过RDKit检查，尚需教师独立审校，不能视为通用化学名称解析器。

每条记录的 `raw` 保存模型字段。`record_id` 含论文ID与局部标签；`entity_id` 来自明确结构的InChIKey。催化剂样品使用来源限定的 sample_id，不因为都含Pd就合并。

本版换算覆盖严格可识别的时间→分钟、产物mg→g，原值同时保留；不猜 overnight、室温和未报告的投料，不把普通反应信息与后处理溶剂混在一起。未支持的单位/范围保留原始文本，交给人工。

## 7. 校验与来源修订

```bash
python -m reaction_knowledge_lab batch-validate --db runs/batch-manual/knowledge.sqlite --output-dir runs/batch-manual/check-before
python -m reaction_knowledge_lab batch-review --db runs/batch-manual/knowledge.sqlite --output runs/batch-manual/review-initial.json
```

打开生成的 patch，按 `evidence` 回查原图与SI；课程参考在 [reference.json](../data/batch/reference.json)。初始只有三篇，校验报告中缺第四篇7条是预期情况。`batch-review`只修订已导入的来源，不会提前导入留出论文。

确认参考适用于练习后应用：

```bash
python -m reaction_knowledge_lab revise --db runs/batch-manual/knowledge.sqlite --patch runs/batch-manual/review-initial.json
python -m reaction_knowledge_lab query --db runs/batch-manual/knowledge.sqlite --history nc2019-t1-9 --output runs/batch-manual/history.json
```

这是课程参考驱动的修订提案，不是模型自动证明自己正确。修订保留原始模型记录、旧版本、依据和原因；旧版本号的patch会被拒绝，同一patch重复应用不会增版本。若命令显示 `no_changes`，不会创建新patch，跳过对应 `revise`。

## 8. 加入第四篇，体验更新

```bash
python -m reaction_knowledge_lab batch-ingest --input runs/batch-manual/aligned.json --only-source nc2025 --db runs/batch-manual/knowledge.sqlite
python -m reaction_knowledge_lab batch-ingest --input runs/batch-manual/aligned.json --only-source nc2025 --db runs/batch-manual/knowledge.sqlite
python -m reaction_knowledge_lab batch-review --db runs/batch-manual/knowledge.sqlite --output runs/batch-manual/review-all.json
python -m reaction_knowledge_lab revise --db runs/batch-manual/knowledge.sqlite --patch runs/batch-manual/review-all.json
python -m reaction_knowledge_lab batch-query --db runs/batch-manual/knowledge.sqlite --output runs/batch-manual/groups-after.json
python -m reaction_knowledge_lab batch-validate --db runs/batch-manual/knowledge.sqlite --output-dir runs/batch-manual/check-final
```

比较groups-before与groups-after。不同催化剂、温度、时间的记录仍独立。重复导入返回 `already_ingested`；同ID但不同内容的输入必须走修订流程，不能静默覆盖。已导入过的同一批原始输入也不会冲掉后续审校。

最终来源参考字段一致；ORD当前无结构错误，但仍有分析关联等警告，必须读报告。两条真实冲突仍存在：

- `nc2025-4s-Br`：正文Fig.3为89%，SI第50页为80%。
- `nc2025-4v-Br`：正文Fig.3为98%，SI第50页为99%。

它们的 `yield_percent=null`，两种说法保存在 `measurement.yield_claims`。因此阈值查询不把它们当作已有单一确认产率。没有更正通知或其他可靠依据前，不平均、不选择“看起来合理”的值；可以保留待核查状态。

`jacs2024-p8` 的180mg和93%来自五次反应的合并产物。知识记录保留单次投料及其含义；ORD原生投料量暂不填总量，完整来源语义放在metadata，避免构造错误的物料衡算。

## 9. 可选：自行调用API

先完成第5节下载。以下命令只调用JACS一篇，输入密钥不回显、不写入命令历史：

```bash
python -c "import getpass,os; from reaction_knowledge_lab.cli import main; os.environ['DEEPSEEK_API_KEY']=getpass.getpass('DeepSeek API Key: '); raise SystemExit(main(['batch-extract','--mode','api','--source-id','jacs2024','--max-calls','1','--budget-cny','0.25','--output','runs/my-batch-api/jacs.json']))"
```

Windows把开头python换成虚拟环境完整解释器路径。全部四篇：将 source-id 改为 `all`、max-calls 改为 `4`、budget-cny 改为 `1`，并换新输出文件。图文输入需要支持图像的 `deepseek-flash`；只有文本能力的兼容服务不属于已验证路径。

输出旁保存metadata和 `.calls/` 原响应目录，含模型、usage、输入/提示词哈希、结束状态；不会保存API Key。异常响应先留存再报错，无自动重试。预算是估算预留，不是服务端硬限额；图像token数、价格和实际账单可能变化。本批4次实测输入12772、输出7949 tokens，高峰/不计缓存估算 **0.089136元**，不是账单扣费证明。[官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)

将API输出交给同一个 `batch-align`；API结果不保证与固定回放一致。只抽一篇时，在 `batch-validate` 命令中加上 `--source-id jacs2024`，只做该篇参考比较，不能把其余未请求的文献算作漏抽。默认回放中四份真实结果未经修改，不包含教师参考。

## 10. 作业与回传

学生提交：原始候选、对齐结果、至少两组跨论文关联及一个不能合并的反例、来源差异解释、一条有依据的修订前后历史、增量导入前后统计。必须注明使用“真实调用”还是“真实结果回放”，不可把回放写成自己请求了模型。

教师或学生可运行：

```bash
python scripts/verify_student_setup.py --output runs/student-check
```

得到 `runs/student-check/return-to-teacher.zip`，无付费调用、无密钥、无完整论文。另行填写该目录中的 `REVIEW_RETURN.md` 并一起回传；ZIP中的表是初始空表，修改外部表后不自动重打包。

完整核查分工见 [人工核查表](MANUAL_REVIEW.md)。软件可重复跑通不替代化学教师确认参考答案。参考已由两次助手检查，但尚未获得独立化学专家批准。
