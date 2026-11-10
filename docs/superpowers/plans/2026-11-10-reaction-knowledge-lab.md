# Reaction Knowledge Lab Implementation Plan

> 执行方式：当前会话主代理集成，子代理并行核验数据、ORD 与可选 RXN Filter；最终独立复核。用户已经授权制作，不重复请求中间阶段批准。

**Goal:** 交付本科生可按中文手册在 CPU 上完成的有机反应知识建模仓库。

**Architecture:** 固定真实回放数据和外部原文下载清单；Python CLI/Notebook 共用小型处理模块，SQLite 保存当前记录和修订历史。真实 API 只在显式 api 模式调用，并使用相同后续接口。

**Tech Stack:** Python3.12、RDKit、ord-schema0.9.6、SQLite、pytest、Jupyter。可选 torch 仅用于 RXN Filter。

**Spec:** ../../../SPEC.md

## Global Constraints

- 核心 CPU、无 API 回放；Secret 仅本地、不可进入 Git。
- 上游原代码/提示词、适配、课程新增分别标注。
- 第二次实验不继承成未明确报告的测量条件；单位换算不得猜测。
- 所有“已验证”说法必须有运行证据。

## Review Focus

- CSV 名称中的逗号（1,1-diphenylethene）不能当实体分隔符。
- 未知/区间/条件未重述不能变成数值零或平均值。
- 改产率仍在合法范围时，需原文参考才能判错。
- 错误/重复修订必须保持事务一致和幂等。
- API 失败/预算不足不能覆盖已有结果或输出密钥。

## Tasks

- [x] T1 固定上游文件、数据清单、短证据、原始输出、人工参考与化合物标识；检查哈希及实验身份。
- [x] T2 完成 fetch/extract/align，真实回放一致；API 先估算、限请求/费用，验证真实少量请求并保存 usage。
- [x] T3 实现 ORD bridge 与原文参考校验；测试缺失、区间、合法但错误的事实。
- [x] T4 实现 SQLite 当前/历史、query、原子 patch、demo/verify；测试两次实验、别名、幂等和回滚。
- [x] T5 编写逐步中文手册、Notebook、故障排查、第三方说明、环境锁定和 CI；执行教程。
- [x] T6 可选 RXN Filter 固定代码/权重，CPU 实跑；注明只做结构合理性筛查。
- [x] T7 独立审查、密钥/发布文件扫描、干净环境回放，打包并准备 GitHub 发布。

## 实际验证与发布状态

46 项本机核心测试、15 项 demo 验收、3 本 Notebook 的 25 个代码单元、选做的 3 项测试通过。干净环境及发布包独立解压后的离线回放通过；GitHub Actions 三系统核心检查全部通过（各 45 passed、1 项原文定位跳过），详见 [验证记录](../../VERIFICATION.md)。

已创建并上传至 [nydiii/reaction-knowledge-lab](https://github.com/nydiii/reaction-knowledge-lab)，仓库可见性已核实为**私有**。跨平台 CI 结果以 [验证记录](../../VERIFICATION.md) 为准。
