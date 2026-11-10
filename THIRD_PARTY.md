# 第三方材料与课程改造

| 材料 | 固定版本或来源 | 在本仓库中的使用 |
|---|---|---|
| ReactionSeek | commit `6d42c4a1c5e47e1a5544b67a5b3ce9b00dbf8f6a`，MIT，Copyright 2025 DeepSynthesis | 两份真实输出 CSV 原样分发；完整输入与提示词脚本按哈希下载；保留 [原许可](third_party/ReactionSeek-LICENSE) |
| ORD | PyPI `ord-schema==0.9.6`，Apache-2.0 | 作为依赖安装并调用；课程 `ord_bridge.py` 是接口适配，未复制全库 |
| RDKit | 核心运行锁定版本见 requirements.lock.txt，BSD-3-Clause | 分子结构解析和规范 SMILES；不去盐、不抹掉立体化学 |
| ChemEnzyRetroPlanner | commit `7dbab354189db9edc7aea9c0aedc2f1b1659f906`，MIT | 选做中保留原模型和指纹算法；原许可、改造列表和权重哈希见 [provenance](optional/rxn_filter/provenance.json) |
| Organic Syntheses 原文 | DOI 和链接见 [sources.json](data/sources.json) | 本库提供事实、少量短证据与字符定位；完整文献/上游输入下载到忽略目录。软件仓库 MIT 许可不等于原文被重新授权 |
| PubChem | 4 个 CID 与来源见 [aliases.json](data/reference/aliases.json) | 有出处的小型身份参考缓存；不是声称保存了完整官方 API 响应 |
| DeepSeek 实测结果 | 2026-11-10 单次真实调用 | 保存响应表格、模型、用量和提示词哈希，不保存密钥。它仍是待核对抽取，不是实验事实金标准 |

课程新增的 SQLite、patch、CLI、参考比较和教学错误不归功于原论文。原作者论文指标也不因本课程小样本运行成功而视为已复现。

完整源代码通过下载指针可检查；本库不运行上游脚本顶层代码。抽取提示词从固定脚本的字面 f-string 中读取，仅填入标题和正文，不导入原模型 SDK。
