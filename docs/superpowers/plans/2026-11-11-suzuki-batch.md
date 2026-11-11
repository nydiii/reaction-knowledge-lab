# Suzuki 跨文献实训扩展 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 用可获得的真实 Suzuki 文献，贯通批量抽取、跨文献关联、校验、增量导入和修订，并交付教师人工核查表。

**Architecture:** 保留现有单篇入门实验，新增批量命令及独立数据目录；复用名称标准化、ORD 和 SQLite 历史机制。先取得来源和定位，再确定实际纳入规模；人工参考与真实模型输出分开，不能用参考冒充模型回放。

**Tech Stack:** Python 3.12、RDKit、ord-schema 0.9.6、SQLite、pytest；普通 CPU。

**Spec:** `SPEC.md` 及 2026-11-11 用户确认的 Suzuki 批量方案和“把自己能做的全部做完”授权。

## Global Constraints

- 不改掉旧案例；私有 GitHub；密钥和完整原文不入库。
- 无 API 路径必须使用真实保存的响应；API 本轮总保守预留不超过 1 元。
- 独立实验、重复实验均值、表中汇总记录明确区分；未报告字段保持未知。
- 不将共同产物当作重复实验，不将未获取资料宣称为已验证。
- 新增人工参考仅代表助手核对，等待教师独立审校。

## Review Focus

- 多论文出现同一局部编号：标识必须带 source_id。
- 相同分子但条件或重复次数不同：不可丢失独立记录或均值语义。
- 增量导入重复执行及同 ID 内容冲突：幂等或拒绝，不能静默覆盖。
- 非法/不完整 API 响应：保留用量和原响应，不能自动充当参考。
- 修订底物或产率：关联查询实时重新计算，历史不变，过期版本被拒绝。

### Task 1: 来源与参考
Files: `data/batch/sources.json`, `data/batch/reference.json`, `data/batch/entities.json`。
Interface: sources 含下载 URL/格式/哈希/正文定位；reference 为现有 records 契约并增加 record_kind、measurement、catalyst、evidence。
- [x] 下载可获得正文并建立记录定位；获取失败的候选单列。
- [x] 建立共享实体与转化组，核对产率类型和独立实验身份。
- [x] 验证每条记录能回到原始资料；实际条数不按目标编造。

### Task 2: 批量抽取与回放
Files: `src/reaction_knowledge_lab/batch_sources.py`, `src/reaction_knowledge_lab/batch.py`, `data/batch/prompt.txt`, `data/batch/replay/`。
Interface: fetch_batch(destination)、extract_batch(output, mode, ...)、align_batch(input, output)。
- [x] 新增可定位正文块的获取与哈希核对，资料仅下载到忽略目录。
- [x] 提供预算限制的真实调用、逐次响应保存、离线重放与保守对齐。
- [x] 小批实测后完成真实回放；失败不伪造结果。

### Task 3: 融合、增量与校验
Files: `src/reaction_knowledge_lab/store.py`, `src/reaction_knowledge_lab/batch.py`, `tests/test_batch.py`。
Interface: ingest_records(records, db_path, entities)、batch_report(db)、batch_demo(workdir)。
- [x] 先写同物异名、跨文献转化、均值不拆、重复导入及冲突回滚测试。
- [x] 实现最小事务化增量导入和动态查询分组；复用 ORD 与 patch 历史。
- [x] 验证一次修订改变查询，保留旧版本；留出文献再导入，不按产率覆盖。

### Task 4: 学生入口与人工核查表
Files: `src/reaction_knowledge_lab/cli.py`, `docs/BATCH_MANUAL.md`, `docs/MANUAL_REVIEW.md`, `docs/REVIEW_RETURN.md`, `README.md`。
- [x] CLI 分步与一键操作；写 Windows/macOS 命令、预期结果和故障处理。
- [x] 逐条核查表包含来源、定位、当前值、人工动作、回传栏；区分必需与可选。
- [x] 保留真实 API 与回放两条路径；标明方法适配与尚未验证范围。

回传表采用可直接填写的Markdown，并提供逐条40行参考摘要；无需额外CSV工具。

### Task 5: 验证与私有发布
Files: `.github/workflows/test.yml`, `docs/VERIFICATION.md`, `docs/examples/batch-verification.json`。
- [x] 原有测试与新增测试、全流程、原文哈希/定位、ORD 实际运行。
- [ ] 检查密钥/原文不进入 Git，提交到现有私有仓库并检查 CI。
- [ ] 给用户可直接填写回传的表格和准确完成/未完成清单。
