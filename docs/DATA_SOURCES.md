# 数据来源、参考答案与复现边界

本实训的必做案例是 Organic Syntheses 的一篇有机反应实验文献；四篇其他文献仅保留为扩展素材。所有样例来源和下载哈希都在 [`data/sources.json`](../data/sources.json) 中。

## 1. 固定的上游版本

- 项目：[ReactionSeek](https://github.com/DeepSynthesis/ReactionSeek)
- commit：`6d42c4a1c5e47e1a5544b67a5b3ce9b00dbf8f6a`
- 论文：[ReactionSeek: LLM-powered literature data mining and knowledge discovery in organic synthesis](https://www.nature.com/articles/s41467-026-70180-1)，Nature Communications，2026。
- 软件许可证：MIT；原文保留在 [`third_party/ReactionSeek-LICENSE`](../third_party/ReactionSeek-LICENSE)。

本仓库不修改分发的两份上游结果 CSV：

| 本仓库文件 | 上游相对路径 | 内容 |
|---|---|---|
| `data/replay/upstream_output_table.csv` | `examples/OrganicSyntheses/reaction_extract/newer_document_extract/reaction_extract/output_table.csv` | 5 篇文献产生的 6 行结构化抽取结果 |
| `data/replay/upstream_output_summary.csv` | 同目录 `output_summary.csv` | 上游公开的 5 条文本回答 |

两份文件已经与上述 commit 的文件逐字节比较，SHA-256 写入 manifest。它们是真实公开的上游结果，不是本课程伪造的模型回答；但也不是本课程人工参考答案。

`upstream_output_summary.csv` 还保留上游的一个空占位行（`Index=0`、`Summary` 为空）。因此它有 6 个物理数据行，但只有 5 个非空模型回答；读取时跳过空回答，不修改分发原文件。

上游配套脚本 `GLM_evaluate.py` 的默认模型是 `glm-4`。CSV 本身没有完整响应元数据、调用时间或 token 用量，因此不能从 CSV 独立证明当次请求的实际模型版本。我们保留这一来源限制。把相同提示词改用 DeepSeek 执行，属于**模型调用适配**，不保证重现原 GLM 的逐字输出或论文全量指标。

## 2. 原文清单

下表的 `source_id` 沿用上游字典键，是上游项目内部编号；它不等于 Organic Syntheses 的正式文章编号。

| 上游 source_id | 原文 | 正式 DOI | 课程状态 |
|---|---|---|---|
| `volume102article28` | [Sharpless Epoxidation of Divinyl Carbinol](https://www.orgsyn.org/demo.aspx?prep=v102p0001) | `10.15227/orgsyn.102.0001` | 扩展素材，尚未逐字段审校 |
| `volume102article24` | [Copper-Catalyzed Suzuki–Miyaura Coupling of Unactivated Alkyl Halides with Arylborons](https://www.orgsyn.org/demo.aspx?prep=v102p0086) | `10.15227/orgsyn.102.0086` | 扩展素材，尚未逐字段审校 |
| `volume102article22` | [Photoexcited Nitroarenes for the Anaerobic Cleavage of Alkenes](https://www.orgsyn.org/demo.aspx?prep=v102p0114) | `10.15227/orgsyn.102.0114` | 必做案例，有课程参考记录 |
| `volume102article17` | [Iodine-Catalyzed Stereospecific anti-Diamination of trans-β-Methylstyrene](https://www.orgsyn.org/demo.aspx?prep=v102p0203) | `10.15227/orgsyn.102.0203` | 扩展素材，尚未逐字段审校 |
| `volume102article9` | [Synthesis of 6-Methoxy-2-methyl-2-(4-methylpent-3-en-1-yl)chroman-4-one via Kabbe Condensation](https://www.orgsyn.org/demo.aspx?prep=v102p0335) | `10.15227/orgsyn.102.0335` | 扩展素材，尚未逐字段审校 |

这五篇均发表于 Organic Syntheses 第 102 卷（2025）。原论文链接和 PDF 链接是取证入口，不是本课程的软件依赖。

## 3. 下载的内容与分发的内容

`data/sources.json` 的 `files` 数组固定两个下载文件：

| name / target | 用途 |
|---|---|
| `input.json` | 上游准备好的原文 Procedure 文本，用于真实抽取和证据字符定位 |
| `GLM_evaluate.py` | 固定上游提示词及调用实现，供适配代码读取和对照；不要填入密钥后原样上传 |

`target` 是相对于 `data/downloads/` 的路径。下载器应先验证 `sha256`，再将文件用于抽取或证据核对。`input.json` 中的科学原文不是由本课程创作；完整原文不随本仓库重新分发，也不因 ReactionSeek 的软件许可证变成 MIT 授权内容。使用者通过固定链接在本地获取，并保留各原文出处。

本仓库分发的课程数据包括：少量事实字段、实体标识、原始模型结果、短证据片段与定位、参考答案和教学修订记录。`data/reference/case22.json` 的课程参考由助手逐项对照公开原文建立，状态标记为 `source_checked`；不是原作者提供的 gold，也不是独立化学专家评审或新的湿实验测量。建议教师在正式将其用作评分金标准前复核原文。

## 4. 必做案例为什么有两条实验记录

原文 Procedure 末尾分别报告了两个实验结果：

| record_id | 产物 | 产物质量 | 产率 | qNMR 纯度 |
|---|---|---:|---:|---:|
| `orgsyn-102-0114-run-1` | benzophenone | 2.63 g | 72% | 99.8% |
| `orgsyn-102-0114-run-2` | benzophenone | 2.62 g | 72% | 98.6% |

两个实验的产物身份相同，实验身份不同。两条记录共享 `source_id` 和产物 `entity_id`，但 `record_id` 不同。第二条的 `raw_record_id` 以 `manual-reference:` 开头，是课程参考标识，不伪装成上游 CSV 中存在的行。

第一轮投料和反应过程在正文中明确报告；第二轮仅报告结果，没有逐项重述投料、溶剂、时间和温度。因此第二条记录保持 `inputs=[]`、`solvents=[]`、四个 `conditions` 字段均为 `null`，并通过同一个来源关联原 procedure。不要复制第一轮条件来填补未知字段。

第一轮 `temperature_c={min:30,max:35}` 记录文中过程的温度变化范围，不是恒定设定温度，也不将其平均为 32.5℃。产率与 qNMR 纯度是不同测量，不可互换。

本课程只结构化规格中列出的有限字段。原文还报告照射波长、灯具布置和气氛等条件，需通过来源回查；当前最小记录不等于可以据此完整复现湿实验的全部条件清单。

## 5. 如何定位参考证据

[`data/reference/case22.json`](../data/reference/case22.json) 包含：

- `input_json_pointer`：`/volume102article22/Procedure/0`。
- `procedure_sha256`：对**解码后的完整字符串**按 UTF-8 编码计算 SHA-256，不是对整个 JSON 文件的哈希。
- `evidence`：每个片段包含 `record_id`、点路径 `field`、`source_id`、`start`、`end` 和 `text`。
- `start/end`：Python Unicode 字符下标，包含起点、不包含终点；不是 UTF-8 字节下标。

读取本地下载的 `input.json` 后，应满足：

```python
procedure = source_data["volume102article22"]["Procedure"][0]
assert procedure[evidence["start"]:evidence["end"]] == evidence["text"]
```

先核对文件哈希及 `procedure_sha256`，再核对片段。若原文文本被重新排版，字符位置可能变化；不要静默把旧定位套到新文本。片段只用于定位和说明，长篇原文在本地下载文件或原出版页阅读。

## 6. 小型名称—结构参考缓存

[`data/reference/aliases.json`](../data/reference/aliases.json) 是必做案例的显式参考缓存，不是声称实时访问 PubChem 后保存的完整 API 响应。四个实体已核对官方记录：

| entity_id | 名称 | 标识来源 |
|---|---|---|
| `pubchem:10740` | 1,1-diphenylethene / 1,1-diphenylethylene | [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/10740) |
| `pubchem:12090` | 4-nitrobenzonitrile | [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/12090) |
| `pubchem:6342` | acetonitrile / CH3CN | [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/Acetonitrile) |
| `pubchem:3102` | benzophenone / diphenylmethanone | [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/3102) |

第一组别名分别在原文 Procedure 与 Note 3 出现；乙腈名称和分子式分别出现在 Procedure 与 Figure 1B 图注。benzophenone 的 IUPAC 名称取自 PubChem。SMILES 来源逐实体保存在 `sources` 中，前三个非溶剂结构还可对照固定上游结构表。

缓存外名称应保持未解析，不能总取“最相近”的已有名称。相同结构标识也不能作为合并不同实验的依据。

## 7. 扩展素材中已发现的局限

- `volume102article24` 的两行上游结果是同一次反应的分离馏分和汇总结果，不应当作两次独立实验。
- `volume102article28` 的抽取结果混入后处理阶段的 acetone 和 1 h；须先区分反应阶段和后处理阶段。
- `volume102article17` 包含两段温度—时间程序，不能简单压成一对温度和时间。
- `volume102article9` 的标题与部分正文产物名称存在 `6-methoxy` 是否出现的不一致，应保留疑点并继续核对。
- 上游名称—结构表中存在将 pyrrolidine 匹配到盐酸盐、部分酒石酸酯缺失立体信息的情况；本课程没有把整张上游结构表当作金标准。

这也说明只检查总行数不够：上游五篇得到六行，但必做案例少了一次实验，另一篇又多拆了一条汇总行。验收必须核对记录身份和字段事实，而不只是文件是否生成、数量是否相同。
