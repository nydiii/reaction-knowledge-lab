# 有机反应科学知识建模：学生操作手册

本手册面向会基础 Python 和终端操作的本科生。普通电脑即可完成必做实验，不需要独立显卡，也不需要购买大模型 API。

你将围绕同一篇文献完成：**原文信息抽取 → 名称与单位标准化 → 独立实验记录入库 → 规则检查与原文核对 → 修订与重新查询**。最后交付的是可追溯、可查询、有历史版本的小型知识库。

## 0. 先了解要完成什么

必做文献是 [Photoexcited Nitroarenes for the Anaerobic Cleavage of Alkenes](https://www.orgsyn.org/demo.aspx?prep=v102p0114)，Organic Syntheses 102:114–127（2025），DOI `10.15227/orgsyn.102.0114`。

文中报告两个实验结果，但 ReactionSeek 公开的示例 CSV 只保留第一轮。这提供了一个真实的漏抽检查任务。此外，课堂会**明确地人为注入一次产率错误**，观察查询结果如何变化，然后依据原文修正。人为错误不能写成 ReactionSeek 或 DeepSeek 实际犯过的错误。

| 环节 | 学生活动 | 核心验收 |
|---|---|---|
| 科学信息抽取 | 回放作者公开输出，或自行调用 DeepSeek；保存来源和运行信息 | 区分原文、模型输出与课程参考 |
| 知识对齐与融合 | 名称关联到结构与实体 ID；换算时间；保留原值 | 相同对象可关联，不把两个实验合为一个 |
| 知识校验与更新 | ORD 检查、参考差异检查、证据定位、修订和查询 | 合法数值也可能不符合原文；修改有依据和历史 |

**范围说明：**本仓库复用固定版本 ReactionSeek 的提示词和真实输出；DeepSeek 调用是模型适配。四实体名称缓存、单位规则、SQLite、参考对照与修订协议是课程实现，不是完整复现上游所有标准化算法。ORD 使用实际 `ord-schema==0.9.6`。参考由助手逐项对照原文建立，状态为 `source_checked`，不是原作者提供的 gold，也不是独立化学专家评审。详见[数据来源](DATA_SOURCES.md)。

## 1. 获取仓库

在本仓库 GitHub 页面选择 **Code → Download ZIP**，解压到自己的课程目录。不要直接在 ZIP 压缩包内运行程序。

也可以在 GitHub 的 **Code → HTTPS** 复制本仓库地址，使用 Git 克隆。将下面占位内容替换为页面中实际的地址，不要原样执行：

```text
git clone <从本仓库Code按钮复制的HTTPS地址>
```

打开终端，进入包含 `pyproject.toml`、`data`、`docs` 的仓库根目录。下面假设解压后的目录名是 `reaction-knowledge-lab`；若带有 `-main` 后缀，使用实际目录名。

```text
cd reaction-knowledge-lab
```

后续命令均在此根目录执行。代码输出放在 `runs/`，不要直接编辑 `data/replay/` 中的原始结果。

## 2. 配置 Python 3.12 环境

安装 Python 3.12。Windows 可使用 Python 安装程序提供的 `py` 启动器；macOS/Linux 请确认有 `python3.12`。本课程固定使用 3.12，不要因为系统已有其他版本就跳过版本检查。

### 2.1 Windows PowerShell

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m reaction_knowledge_lab --help
```

最后一条应显示 `fetch`、`extract`、`align`、`resolve`、`validate` 等子命令。

后面的示例为简洁起见统一写作 `python ...`。在 PowerShell 中，**可将每条命令开头的 `python` 替换成 `.\.venv\Scripts\python.exe`**，不需要激活，也不需要修改执行策略。例如：

```powershell
.\.venv\Scripts\python.exe -m reaction_knowledge_lab demo --workdir runs/demo
```

如果希望后续直接使用 `python`，也可以激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
```

若激活被执行策略阻止，使用前述完整解释器路径即可。

### 2.2 macOS / Linux

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps -e .
python -m reaction_knowledge_lab --help
```

每次打开新终端后，重新进入仓库并执行 `source .venv/bin/activate`。也可不激活，直接用 `.venv/bin/python` 替换后续命令中的 `python`。

### 2.3 环境自检

```bash
python -c "import sys; from importlib.metadata import version; print(sys.executable); print(sys.version); print('ord-schema', version('ord-schema'))"
```

应看到仓库 `.venv` 内的解释器、Python 3.12 和 `ord-schema 0.9.6`。核心使用 CPU；无需安装 CUDA。

安装依赖需要网络。安装完成后，默认回放和数据库操作不需要 API，也不会自动访问模型服务。项目当前实际验证的平台为 macOS arm64；Windows/Linux 提供跨平台命令及 CI 配置，不能把配置文件存在说成已在每种电脑上跑过。

## 3. 先运行一键回放，再做分步实验

如果 `runs/demo` 不存在或为空，运行：

```bash
python -m reaction_knowledge_lab demo --workdir runs/demo
python -m reaction_knowledge_lab verify --workdir runs/demo
```

预期终端显示 `"passed": true`，15 项 `checks` 全为 `true`，`api_calls` 为 `0`。这证明教学流程已连通，不等于论文全量指标已复现。

若还没有下载原文，`evidence_check.status` 会是 `not_checked`；离线流程仍可完成，但此时不能声称重新核验过原文字符位置。下一节下载后再检查。

一键流程的主要文件：

| 文件或目录 | 含义 |
|---|---|
| `runs/demo/extracted.csv`、`extracted.metadata.json` | 主案例真实上游结果回放；元信息说明没有调用 API |
| `aligned.json`、`aligned.mapping.json` | 归一记录和原名称到实体的映射 |
| `knowledge.sqlite` | 当前知识记录与历史版本 |
| `01_initial/` | 初始来源检查与 ORD 导出 |
| `02_injected_error/` | 注入 27% 教学错误后的检查 |
| `03_reviewed/` | 修订后的检查与 ORD 导出 |
| `query_initial.json`、`query_injected.json`、`query_reviewed.json` | 同一产率查询依次返回 1、0、2 条 |
| `teaching_error.patch.json`、`source_review.patch.json` | 可阅读的修订内容与依据 |
| `final_records.json`、`history_run1.json` | 最终记录与第一轮历史 |
| `verification.json`、`evidence_check.json` | 验收结果与证据检查状态 |

**不要反复用 `demo` 覆盖同一个目录。**重复检查已有结果使用 `verify`；重新实验使用新的目录，如 `runs/demo-second`。

`verify` 专门检查 **`demo` 生成的完整目录结构**，并通过重放同一修订测试幂等性。下面的手工分步目录 `runs/manual` 不具备全部相同的文件名，不能直接对它执行 `verify`。

## 4. 下载原始资料并检查证据

```bash
python -m reaction_knowledge_lab fetch
python -m reaction_knowledge_lab check-evidence
```

`fetch` 从固定的 ReactionSeek commit 下载两个文件，并检查 SHA-256：

- `data/downloads/input.json`：五篇文献的标题与 Procedure 文本。
- `data/downloads/GLM_evaluate.py`：用于读取固定提示词，不在本课程中原样执行。

下载地址、固定版本和预期哈希保存在 [`data/sources.json`](../data/sources.json)。有相同哈希的本地文件不会重复下载；内容被修改时会明确报错，不静默覆盖。

`check-evidence` 预期显示 `status: verified`、`evidence_count: 13`。它核对主案例 Procedure 字符串的哈希及短证据位置，不判断任意新文献是否真实。

再检查一键输出可运行：

```bash
python -m reaction_knowledge_lab verify --workdir runs/demo
```

此时 `verification.json` 中的证据检查应为 `verified`。`evidence_check.json` 是一键运行时的快照；如果当时还未下载，它不会因单独运行 `verify` 而自动改写。

**学生活动：**打开原文 Procedure 最后的两段，对照 [`data/reference/case22.json`](../data/reference/case22.json)。分别找到两轮的质量、产率和纯度；再判断第二轮是否逐项重述了温度和投料。不要只看参考 JSON 就宣布原文核对完成。

## 5. 分步实验一：回放真实抽取结果

以下必做流程使用全新的 `runs/manual` 目录，与一键目录分开。默认路径不用 API：

```bash
python -m reaction_knowledge_lab extract --mode replay --output runs/manual/extracted.csv
```

预期：`mode: replay`、`source_id: volume102article22`、`row_count: 1`、`api_calls: 0`、`cost_cny: 0`。

输出：

- `runs/manual/extracted.csv`
- `runs/manual/extracted.metadata.json`

CSV 记录第一轮：产物 benzophenone，质量 2.63 g，产率 72%，时间 36 hours，温度 30–35°C。**回放是在读取作者公开的真实输出，没有重新运行抽取模型。**它同样保留上游的漏抽和未抽字段，不能先修好数据再假装这是模型结果。

元信息保存模式、来源 ID、固定 commit 和上游文件哈希。真实 API 路径见第 11 节；它输出相同的八个科学字段，可以进入同一套后续程序。

## 6. 分步实验二：名称关联、单位整理与实验身份

### 6.1 运行归一

```bash
python -m reaction_knowledge_lab align --input runs/manual/extracted.csv --output runs/manual/aligned.json
```

默认回放的预期输出：`record_count: 1`、`entity_count: 4`、`unresolved_names: []`。

查看：

- `runs/manual/aligned.json`：课程记录，包含原值 `raw` 和归一后的字段。
- `runs/manual/aligned.mapping.json`：原记录、原名称、角色和统一实体标识。

检查以下值：

| 字段 | 初始值 |
|---|---|
| `record_id` | `orgsyn-102-0114-run-1` |
| `raw_record_id` | `volume102article22_1_1` |
| `product.entity_id` | `pubchem:3102` |
| `product.mass_g` | `2.63` |
| `product.yield_percent` | `72.0` |
| `product.purity_percent` | `null`，上游未抽取，不在此步填答案 |
| `conditions.raw_time` | `36 hours` |
| `conditions.time_minutes` | `2160.0` |
| `conditions.temperature_c` | `{"min":30.0,"max":35.0}` |

`record_id` 初始按候选顺序分配，仍需来源核对；不能仅因程序生成了编号就认为实验身份一定正确。未知时间保持 `null`，温度区间不取平均；原字段保留在 `raw`。

### 6.2 比较真实别名

```bash
python -m reaction_knowledge_lab resolve "acetonitrile"
python -m reaction_knowledge_lab resolve "CH3CN"
python -m reaction_knowledge_lab resolve "1,1-diphenylethene"
python -m reaction_knowledge_lab resolve "1,1-diphenylethylene"
python -m reaction_knowledge_lab resolve "unlisted-example-name"
```

前两条都应得到 `pubchem:6342`，另两个真实别名都得到 `pubchem:10740`。未知名称返回 `resolution_status: unresolved`、空标识和空结构，不强行匹配最近的已有对象。

本步骤使用四个实体的有出处参考缓存和 RDKit 结构规范化，复用 ReactionSeek“名称关联结构”的组织思路。它不是对任意化学名称都适用的自动实体链接模型；也不会为了课堂例子在线查全库。

**验收：**解释 `entity_id` 与 `record_id` 的区别。说明为什么共用产物标识并不能证明两条记录来自同一次实验。

## 7. 分步实验三：分别运行规则检查和来源检查

```bash
python -m reaction_knowledge_lab validate --input runs/manual/aligned.json --output-dir runs/manual/01_initial
```

每个检查目录生成：

| 文件 | 用途 |
|---|---|
| `validation.json` | `source_check` 与 `ord` 两类诊断分开保存 |
| `ord_all_records.json` | 所有课程记录的 ORD 表示，包括信息不完整者 |
| `ord_structurally_ready.json` | 当前没有 ORD errors 的记录子集，仍须阅读 warnings |

初始参考检查应发现至少两项：第一轮缺少纯度；第二轮整个实验缺失。`source_check.issues` 中可看到 `missing_field` 与 `missing_experiment`。

第一轮通常能通过 ORD 的必需结构检查，但仍可能有 warnings，例如分析记录不完整。这说明：**ORD 检查某些格式、结构和数值约束；课程参考检查它是否与这篇原文的有限字段一致。**两者都不等于已经独立证明所有科学内容正确。

`source_check` 是与已提供参考的确定性比较，不是一个自动读论文并判断真假的新模型。终端命令完成只代表报告已生成；请阅读报告，不要仅看退出码。

## 8. 建库并查询初始记录

```bash
python -m reaction_knowledge_lab build --input runs/manual/aligned.json --db runs/manual/knowledge.sqlite
python -m reaction_knowledge_lab query --db runs/manual/knowledge.sqlite --min-yield 70 --output runs/manual/query_initial.json
python -m reaction_knowledge_lab query --db runs/manual/knowledge.sqlite --name "diphenylmethanone"
```

建库应显示 `record_count: 1`、`entity_count: 4`。`--min-yield 70` 表示产率不低于 70%，当前返回 1 条记录，`revision: 1`。

SQLite 内部分开保存实体、实验记录、关联、历史和修订。名称查询通过实体别名查找相关实验，不会把多个实验折叠为一个结果。

`build` 拒绝覆盖已存在的数据库。再次实验应使用新目录，不要为消除报错直接删除尚未提交的实验结果。

## 9. 注入教学错误，再依据原文修订

### 9.1 生成并阅读错误提案

```bash
python -m reaction_knowledge_lab make-patch --db runs/manual/knowledge.sqlite --kind teaching-error --output runs/manual/teaching_error.patch.json
```

此命令只生成提案，不改数据库。用文本编辑器打开 patch，确认：

- `teaching_injection` 为 `true`。
- 理由明确说把 72% 故意改为 27%，这不是原文值或模型真实错误。
- `expected_revision` 为当前版本 1。
- 修改字段是 `product.yield_percent`。

### 9.2 应用错误并观察变化

```bash
python -m reaction_knowledge_lab revise --db runs/manual/knowledge.sqlite --patch runs/manual/teaching_error.patch.json
python -m reaction_knowledge_lab validate --db runs/manual/knowledge.sqlite --output-dir runs/manual/02_injected_error
python -m reaction_knowledge_lab query --db runs/manual/knowledge.sqlite --min-yield 70 --output runs/manual/query_injected.json
```

预期第一轮变为 `revision: 2`，当前产率 27%。产率查询返回空数组 `[]`。

27% 仍是合法的百分数，ORD 不会因此认定它违反产率范围。来源对照应出现 `source_mismatch`，字段为 `product.yield_percent`，预期 72、实际 27。原始抽取字典中的 `raw.Yield` 仍为 `72%`，没有为了当前修改销毁原始结果。

### 9.3 对照原文，生成修订提案

回到第 4 节的原文与短证据定位。确认两轮的不同质量、纯度和未重述条件后再运行：

```bash
python -m reaction_knowledge_lab make-patch --db runs/manual/knowledge.sqlite --kind source-review --output runs/manual/source_review.patch.json
```

阅读文件，找出两种操作：

1. `replace`：恢复第一轮的来源支持值，并补充参考中核实的字段。
2. `add`：新增 `orgsyn-102-0114-run-2`，保留其未知条件。

这是**依据现成课程参考生成的修订提案**，不是自动发现新事实的论文模型。学生需要检查提案的 `reason`、`evidence`、修改范围与来源是否相符。

### 9.4 应用修订、检查与查询

```bash
python -m reaction_knowledge_lab revise --db runs/manual/knowledge.sqlite --patch runs/manual/source_review.patch.json
python -m reaction_knowledge_lab validate --db runs/manual/knowledge.sqlite --output-dir runs/manual/03_reviewed
python -m reaction_knowledge_lab query --db runs/manual/knowledge.sqlite --min-yield 70 --output runs/manual/query_reviewed.json
python -m reaction_knowledge_lab query --db runs/manual/knowledge.sqlite --name "diphenylmethanone"
```

预期两个查询均返回 2 条；第一轮版本为 3，第二轮版本为 1。两条记录共享产物 `pubchem:3102`，但质量分别 2.63 g 和 2.62 g，产率均为 72%，纯度分别为 99.8% 和 98.6%。

来源参考对照应为 `source_reference_agreement: true`，但这只覆盖参考定义的有限字段。第二轮仍然没有逐项报告输入物质和条件，知识库保留这一不完整观察。

**最终两个计数不同是正常结果：**

- 知识库保留 **2 条有来源的实验观察记录**。
- `ord_structurally_ready.json` 只有 **1 条无 ORD errors 的记录**。
- 第二轮在 `ord_incomplete_ids` 中，因为缺少 ORD 要求的反应输入；不能为“全绿”从第一轮复制未知条件和投料。

### 9.5 验证历史与重复修订

```bash
python -m reaction_knowledge_lab query --db runs/manual/knowledge.sqlite --history orgsyn-102-0114-run-1 --output runs/manual/history_run1.json
python -m reaction_knowledge_lab revise --db runs/manual/knowledge.sqlite --patch runs/manual/source_review.patch.json
python -m reaction_knowledge_lab query --db runs/manual/knowledge.sqlite --history orgsyn-102-0114-run-1
```

历史按版本应显示产率 **72 → 27 → 72**，包含原因、依据、patch ID 和时间。第二次应用**同一份** `source_review.patch.json` 应返回 `status: already_applied`，第一轮历史仍为 3 个版本。

不要在已修正的数据库上重新生成同种提案来“测试幂等性”；程序会提示当前已与参考一致。幂等性测试使用第一次生成的原 patch 文件。修改了内容却沿用同一 `patch_id` 也会被拒绝。

更新后需要**重新运行查询**。已导出的 `query_initial.json` 是历史快照，不会被后台悄悄改写；这个课程没有额外部署实时通知或自动刷新服务。

## 10. 导出与提交成果

```bash
python -m reaction_knowledge_lab export --db runs/manual/knowledge.sqlite --output runs/manual/final_records.json
```

预期 `record_count: 2`。导出的课程 JSON 保留来源、原值和未知字段；版本历史仍在 SQLite 中，可用 `query --history` 单独导出。ORD 格式已在各次 `validate` 目录中生成。

建议提交：

- `runs/manual/extracted.csv` 与 `.metadata.json`。
- `aligned.json` 和 `aligned.mapping.json`。
- 三个验证目录的 `validation.json`。
- 三次查询结果、两个 patch、`history_run1.json`、`final_records.json`。
- `knowledge.sqlite`。
- 一页说明：哪里是模型漏抽，哪里是人为教学错误，如何核对来源，为什么第二轮条件保持未知。

如果还提交一键验收结果，使用 `runs/demo/verification.json`。**不要用 `verify --workdir runs/manual` 代替分步结果检查。**

## 11. 可选：真实 DeepSeek 调用与真实结果回放

这部分不影响免费必做流程。API 密钥由使用者自行准备，真实调用会按账户计费；先完成第 4 节下载。

### 11.1 在终端安全输入密钥，只调用一篇

使用新的 `runs/api` 目录，不覆盖 `runs/manual`。下列命令在终端中用 `getpass` 提示输入密钥，将其只放入本次 Python 进程的 `DEEPSEEK_API_KEY` 环境变量；输入内容不回显，也不出现在命令历史中。不要把密钥写进命令、Notebook、截图或聊天。

```bash
python -c "import getpass, os; from reaction_knowledge_lab.cli import main; os.environ['DEEPSEEK_API_KEY']=getpass.getpass('DeepSeek API Key: '); raise SystemExit(main(['extract','--mode','api','--output','runs/api/extracted.csv','--source-id','volume102article22','--max-calls','1','--budget-cny','0.10']))"
```

Windows 不激活环境时，将开头的 `python` 换为 `.\.venv\Scripts\python.exe`。此命令应在真正终端运行，不在 Notebook 的普通输出单元中运行。若 `getpass` 警告无法隐藏输入，停止输入并换终端。

输出：`runs/api/extracted.csv` 和 `runs/api/extracted.metadata.json`。元信息保存模型、模式、提示词哈希、原始回答、usage、结束状态和估算费用，不保存密钥。正常完成应为 `status: complete`、`api_calls: 1`。

实现固定使用 `deepseek-flash`、关闭思考模式、最多输出 2048 tokens，无隐藏自动重试；超过请求前保守估算预算时不会发送请求。这里的预算是本次命令的估算保护，不是服务商的账户硬性限额，也不跨多次进程累计。已有输出或元信息文件时拒绝覆盖；排查后重试应使用新的目录，并考虑失败请求可能已产生费用。

### 11.2 不调用 API，使用仓库中已有的 DeepSeek 实测结果

仓库还附有一次真实调用的结果和元信息：

- [`data/replay/deepseek_20261110.csv`](../data/replay/deepseek_20261110.csv)
- [`data/replay/deepseek_20261110.metadata.json`](../data/replay/deepseek_20261110.metadata.json)

若选择这个免费选项，不执行上一节的调用命令，改用下面跨平台复制命令：

```bash
python -c "from pathlib import Path; import shutil; p=Path('runs/api'); p.mkdir(parents=True,exist_ok=True); assert not (p/'extracted.csv').exists(), '请选择全新runs/api目录'; assert not (p/'extracted.metadata.json').exists(), '元信息已存在'; shutil.copyfile('data/replay/deepseek_20261110.csv',p/'extracted.csv'); shutil.copyfile('data/replay/deepseek_20261110.metadata.json',p/'extracted.metadata.json')"
```

复制保留了原来那次调用的元信息，**不代表学生本次发生过 API 调用**。报告中请注明“回放课程发布的 DeepSeek 实测结果”。默认 `extract --mode replay` 仍读取上游 GLM 示例，不会悄悄改成这份 DeepSeek 结果。

### 11.3 用相同程序处理 API 路径结果

```bash
python -m reaction_knowledge_lab align --input runs/api/extracted.csv --output runs/api/aligned.json
python -m reaction_knowledge_lab validate --input runs/api/aligned.json --output-dir runs/api/01_initial
python -m reaction_knowledge_lab build --input runs/api/aligned.json --db runs/api/knowledge.sqlite
python -m reaction_knowledge_lab make-patch --db runs/api/knowledge.sqlite --kind source-review --output runs/api/source_review.patch.json
python -m reaction_knowledge_lab revise --db runs/api/knowledge.sqlite --patch runs/api/source_review.patch.json
python -m reaction_knowledge_lab validate --db runs/api/knowledge.sqlite --output-dir runs/api/02_reviewed
python -m reaction_knowledge_lab query --db runs/api/knowledge.sqlite --min-yield 70
python -m reaction_knowledge_lab export --db runs/api/knowledge.sqlite --output runs/api/final_records.json
```

每次新模型输出都可能不同，先检查 CSV 和原始回答，再读验证报告。若出现未知名称、表格列数不符或额外候选，应先人工复核，不能为了继续运行直接删除疑点或套用参考答案。

**已核实的一次调用：**2026-11-10，仅主案例一篇，输入 7279 tokens、输出 113 tokens；按当天高峰输入 2 元/百万、输出 8 元/百万，忽略缓存折扣估算为 **0.015462 元**。这不是账户账单实扣证明，也不是整套数据的费用保证。[官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)可能变化。

该次 DeepSeek 输出仍漏掉第二轮，而且只给出 35°C；上游 GLM 示例保留 30–35°C。不能凭一次调用声称 DeepSeek 更准确，也不能把这次演示称为重现了论文所有指标。

## 12. Notebook 与自动化测试

需要逐单元观察中间数据时安装开发依赖：

```bash
python -m pip install -r requirements-dev.lock.txt
python -m pip install --no-deps -e .
python -m jupyterlab
```

JupyterLab 启动后保持该终端运行。需要继续执行命令时另开终端，重新进入仓库，并使用同一个 `.venv` 解释器。

打开下列 Notebook，并选择当前 `.venv` 对应的 Python 内核：

1. [`01_extraction.ipynb`](../notebooks/01_extraction.ipynb)
2. [`02_alignment.ipynb`](../notebooks/02_alignment.ipynb)
3. [`03_validation_update.ipynb`](../notebooks/03_validation_update.ipynb)

Notebook 内若需要确认环境，可运行 `import sys; print(sys.executable)`。不要为了切换内核把 API Key 打印出来。已有 Notebook 结果与新结果应使用各自目录，避免重复创建已有数据库。

测试与无界面 Notebook 执行：

```bash
python -m pytest -q
python scripts/run_notebooks.py
```

执行器默认把实验结果写入 `runs/notebook-lab`，把带输出的 Notebook 副本写入 `runs/notebook-executed`，并固定使用启动它的 Python。它拒绝覆盖旧结果；若前面已运行过，换两个互不包含的新目录：

```bash
python scripts/run_notebooks.py --workdir runs/notebook-lab-second --output-dir runs/notebook-executed-second
```

应全部通过；若未下载原文，证据定位相关测试会明确显示跳过。`fetch` 后重新运行即可启用该检查。测试通过证明这些具体行为和有限样例符合预期，不证明任意化学资料都能自动处理。

## 13. 五篇样例的扩展阅读

仓库总共包含五篇上游样例，其中一篇必做、另四篇扩展：

```bash
python -m reaction_knowledge_lab extract --mode replay --source-id all --output runs/extension/all_candidates.csv
```

预期得到六行候选。**当前 `align` 只支持必做案例**，不要把这份全量 CSV 直接交给它并期待自动正确处理所有反应。

扩展任务可选择：

- 找出 `volume102article24` 两条候选分别表示什么，判断是否是两次实验。
- 检查 `volume102article28` 中哪些溶剂和时间属于后处理。
- 阅读 `volume102article17` 的两段温度—时间程序，讨论当前字段如何扩展。
- 对比 `volume102article9` 的标题和产物名称，保留无法仅凭当前信息消除的疑点。

这些记录没有被全部逐项来源核对，不能直接作为训练金标准。RXN Filter 是独立选做内容，按仓库提供的选做说明执行；它的合理性分数不验证温度、产率或文献事实，也不是必做验收条件。

## 14. 常见问题

| 现象 | 检查和处理 |
|---|---|
| `No module named reaction_knowledge_lab` | 确认在仓库根目录、使用 `.venv` 的解释器，并执行 `python -m pip install --no-deps -e .` |
| Windows 无法运行 Activate.ps1 | 直接使用 `.\.venv\Scripts\python.exe`；无需修改系统执行策略 |
| pip 找不到匹配版本 | 确认 Python 3.12、64 位、更新 pip，检查网络；不要随意升级 ORD 绕过固定版本 |
| `fetch` 网络失败 | 回放主线仍可运行；检查对 GitHub raw 的访问。获得文件后必须按 manifest 验哈希，不能跳过来源验证 |
| 本地文件哈希不一致 | 保留自己修改的副本；将错误文件移出下载目录，再运行 `fetch`，不要修改 manifest 来迁就错误文件 |
| `check-evidence` 为 `not_checked` | 还没有默认位置的原文文件，运行 `fetch`；不能把此状态写成已核验 |
| API 未配置密钥 | 使用第 11 节 getpass 命令，或完成默认回放；不要在报错截图中提供密钥 |
| API 请求失败或解析失败 | 查看 metadata 的状态、HTTP 状态和原始回答；无自动重试。重新调用使用新路径并控制费用 |
| API 提示已有结果 | 本程序防止覆盖和误付费；先阅读已有结果，再决定是否使用新目录 |
| `unresolved` 名称 | 缓存只覆盖四实体；保留未知并核对来源，不把它改成最相近已知名称 |
| SQLite 文件已存在 | 使用新实验目录；已有库用 `query`/`validate`，不要再次 `build` |
| 修订提示版本过期 | 数据库已变化，重新阅读当前记录和历史；不要随意修改 expected_revision 来强行通过 |
| 修订提示当前已一致 | 说明无新差异；幂等性测试应重放原 patch，而非重新生成 |
| 最终第二轮有 ORD error | 这是预期的信息不完整标记；保留来源事实，不填造缺失投料 |
| `verify` 找不到阶段文件 | 它只检查 `demo` 输出；手工目录按第 7–10 节检查，或新建目录运行 demo |

最后检查你的报告是否区分了三件事：程序能运行、记录符合规则、记录符合来源。它们需要不同的证据。本课程仅结构化有限字段，光照、气氛等完整实验条件仍须回查原文，知识库不能直接作为湿实验执行说明。
