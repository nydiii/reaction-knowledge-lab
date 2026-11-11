# 第三方材料与课程改造

| 材料 | 固定版本或来源 | 在本仓库中的使用 |
|---|---|---|
| ReactionSeek | commit `6d42c4a1c5e47e1a5544b67a5b3ce9b00dbf8f6a`，MIT，Copyright 2025 DeepSynthesis | 两份真实输出 CSV 原样分发；完整输入与提示词脚本按哈希下载；保留 [原许可](third_party/ReactionSeek-LICENSE) |
| ORD | PyPI `ord-schema==0.9.6`，Apache-2.0 | 作为依赖安装并调用；课程 `ord_bridge.py` 是接口适配，未复制全库 |
| RDKit | 核心运行锁定版本见 requirements.lock.txt，BSD-3-Clause | 分子结构解析和规范 SMILES；不去盐、不抹掉立体化学 |
| PyMuPDF | `1.28.2`，GNU AGPL-3.0 / Artifex 商业双重许可 | 安装为依赖，仅用于读取下载的 SI 选页；依赖本身不改为本库的 MIT 许可 |
| ChemEnzyRetroPlanner | commit `7dbab354189db9edc7aea9c0aedc2f1b1659f906`，MIT | 选做中保留原模型和指纹算法；原许可、改造列表和权重哈希见 [provenance](optional/rxn_filter/provenance.json) |
| Organic Syntheses 原文 | DOI 和链接见 [sources.json](data/sources.json) | 本库提供事实、少量短证据与字符定位；完整文献/上游输入下载到忽略目录。软件仓库 MIT 许可不等于原文被重新授权 |
| PubChem | 4 个 CID 与来源见 [aliases.json](data/reference/aliases.json) | 有出处的小型身份参考缓存；不是声称保存了完整官方 API 响应 |
| DeepSeek 实测结果 | 2026-11-10 单次真实调用 | 保存响应表格、模型、用量和提示词哈希，不保存密钥。它仍是待核对抽取，不是实验事实金标准 |

课程新增的 SQLite、patch、CLI、参考比较和教学错误不归功于原论文。原作者论文指标也不因本课程小样本运行成功而视为已复现。

完整源代码通过下载指针可检查；本库不运行上游脚本顶层代码。抽取提示词从固定脚本的字面 f-string 中读取，仅填入标题和正文，不导入原模型 SDK。
# Suzuki 批量资料补充（2026-11-11）

新增 `data/batch` 的来源清单逐项列出 DOI、官方下载URL、许可、SHA-256和抽取选页。NC2019、NC2022、JACS2024为CC BY 4.0；NC2025原文为CC BY-NC-ND 4.0。完整原文、SI及图表只下载到Git忽略目录，不在仓库重新分发。软件MIT许可证不重新授权原论文。

分发内容是有限选定的事实字段、名称/结构映射、参考定位，以及本课程真实模型响应与使用量。结构字典是助手依据原图/名称转录，不冒充PubChem官方缓存；需要教师审校。图像不做改编分发，发生来源冲突时保留双方数值。新的JSON提示词和图文调用为课程适配，不冒充ReactionSeek原实现。
