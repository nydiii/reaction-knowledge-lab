"""Command-line interface shared by the Chinese manual and notebooks."""
import argparse
import json
from pathlib import Path
import sys

from .alignment import align_csv, entity_cache, resolve_alias
from .extraction import CASE, extract_api, fetch_sources, replay
from .files import load_records, read_json, save_records, write_json
from .store import apply_patch, build_database, get_history, get_records, query_records
from .validation import check_evidence
from .workflow import demo, reference_patch, teaching_error_patch, validate_and_export, verify
from .batch import (align_batch, batch_demo, batch_entities, batch_report,
                    batch_validate, batch_verify, review_patch)
from .batch_extraction import extract_batch
from .batch_sources import check_batch_evidence, fetch_batch
from .store import ingest_records


def parser():
    root = argparse.ArgumentParser(description="有机反应知识建模实训：CPU、可追溯、可回放")
    sub = root.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="下载并校验固定上游输入和提示词")
    fetch.add_argument("--destination", type=Path)
    extract = sub.add_parser("extract", help="真实上游输出回放，或显式调用DeepSeek")
    extract.add_argument("--mode", choices=["replay", "api"], default="replay")
    extract.add_argument("--output", type=Path, required=True)
    extract.add_argument("--source-id", default=CASE)
    extract.add_argument("--credentials", type=Path)
    extract.add_argument("--downloads", type=Path)
    extract.add_argument("--budget-cny", type=float, default=1.0)
    extract.add_argument("--max-calls", type=int, default=1)
    align = sub.add_parser("align", help="主案例名称关联及单位标准化")
    align.add_argument("--input", type=Path, required=True)
    align.add_argument("--output", type=Path, required=True)
    alias = sub.add_parser("resolve", help="查询有出处的小型结构缓存，未知名称不猜测")
    alias.add_argument("name")
    validation = sub.add_parser("validate", help="ORD规则校验与课程参考核对，分开报告")
    selection = validation.add_mutually_exclusive_group(required=True)
    selection.add_argument("--input", type=Path)
    selection.add_argument("--db", type=Path)
    validation.add_argument("--output-dir", type=Path, required=True)
    sub.add_parser("check-evidence", help="核对已下载原文的哈希和证据位置")
    build = sub.add_parser("build", help="创建SQLite知识库，拒绝覆盖旧数据库")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--db", type=Path, required=True)
    query = sub.add_parser("query", help="查询当前记录、别名、产率与历史")
    query.add_argument("--db", type=Path, required=True)
    query.add_argument("--min-yield", type=float)
    query.add_argument("--name")
    query.add_argument("--history")
    query.add_argument("--output", type=Path)
    patch = sub.add_parser("make-patch", help="生成可审阅的课程修订提案；不会立即修改数据库")
    patch.add_argument("--db", type=Path, required=True)
    patch.add_argument("--kind", choices=["teaching-error", "source-review"], default="source-review")
    patch.add_argument("--output", type=Path, required=True)
    revision = sub.add_parser("revise", help="有依据、带版本检查的原子修订")
    revision.add_argument("--db", type=Path, required=True)
    revision.add_argument("--patch", type=Path, required=True)
    export = sub.add_parser("export", help="导出当前知识记录，包含来源和原值")
    export.add_argument("--db", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    for name, help_text in (("demo", "无需API的一键课堂回放"), ("verify", "验收已有demo输出")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--workdir", type=Path, default=Path("runs/demo"))
    batch_fetch = sub.add_parser('batch-fetch', help='下载并校验批量文献、SI及图表')
    batch_fetch.add_argument('--destination', type=Path, default=Path('data/downloads/batch'))
    evidence=sub.add_parser('batch-check-evidence', help='核对原文件、选页和真实回放的输入哈希')
    evidence.add_argument('--downloads',type=Path,default=Path('data/downloads/batch'))
    batch_extract = sub.add_parser('batch-extract', help='批量真实响应回放或显式真实调用')
    batch_extract.add_argument('--mode', choices=['replay','api'], default='replay')
    batch_extract.add_argument('--source-id', default='all')
    batch_extract.add_argument('--output', type=Path, required=True)
    batch_extract.add_argument('--downloads', type=Path, default=Path('data/downloads/batch'))
    batch_extract.add_argument('--credentials', type=Path)
    batch_extract.add_argument('--max-calls', type=int, default=1)
    batch_extract.add_argument('--budget-cny', type=float, default=1.0)
    batch_align = sub.add_parser('batch-align', help='跨文献保守名称关联和单位整理')
    batch_align.add_argument('--input', type=Path, required=True)
    batch_align.add_argument('--output', type=Path, required=True)
    for name in ('batch-build','batch-ingest'):
        p=sub.add_parser(name, help='创建批量知识库' if name=='batch-build' else '事务化增量导入，不覆盖修订')
        p.add_argument('--input', type=Path, required=True)
        p.add_argument('--db', type=Path, required=True)
        p.add_argument('--exclude-source')
        p.add_argument('--only-source')
    for name in ('batch-query','batch-validate','batch-review'):
        p=sub.add_parser(name)
        p.add_argument('--db', type=Path, required=True)
        if name=='batch-validate':
            p.add_argument('--output-dir', type=Path, required=True)
            p.add_argument('--source-id',nargs='+',help='仅比较这些论文的参考；单篇API试跑时指定')
        else:p.add_argument('--output', type=Path, required=True)
    for name in ('batch-demo','batch-verify'):
        p=sub.add_parser(name)
        p.add_argument('--workdir', type=Path, default=Path('runs/batch'))
    return root


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == 'batch-fetch':
            result=fetch_batch(args.destination)
        elif args.command == 'batch-check-evidence':
            result=check_batch_evidence(args.downloads)
        elif args.command == 'batch-extract':
            result=extract_batch(args.output,mode=args.mode,source_id=args.source_id,
                credentials=args.credentials,downloads=args.downloads,budget_cny=args.budget_cny,max_calls=args.max_calls)
        elif args.command == 'batch-align':
            result=align_batch(args.input,args.output)
        elif args.command in ('batch-build','batch-ingest'):
            records=[r for r in load_records(args.input)
                     if r['source_id']!=args.exclude_source and (not args.only_source or r['source_id']==args.only_source)]
            if not records:raise ValueError('所选来源没有记录。')
            result=build_database(records,args.db,batch_entities()) if args.command=='batch-build' else ingest_records(records,args.db,batch_entities())
        elif args.command=='batch-query':
            result=batch_report(args.db);write_json(args.output,result)
        elif args.command=='batch-validate':
            report=batch_validate(get_records(args.db),args.output_dir,args.source_id)
            result={'reference_differences':len(report['source_comparison']['issues']),
                    'source_conflicts':report['source_comparison']['unresolved_source_conflicts'],
                    'ord_dataset_errors':len(report['ord']['dataset_errors']),
                    'report':str(args.output_dir/'validation.json')}
        elif args.command=='batch-review':
            patch=review_patch(args.db,{r['source_id'] for r in get_records(args.db)})
            if patch:write_json(args.output,patch)
            result={'status':'patch_ready' if patch else 'no_changes','output':str(args.output) if patch else None}
        elif args.command=='batch-demo':
            result=batch_demo(args.workdir)
        elif args.command=='batch-verify':
            result=batch_verify(args.workdir)
        elif args.command == "fetch":
            result = fetch_sources(args.destination)
        elif args.command == "extract":
            if args.mode == "replay":
                result = replay(args.output, args.source_id)
            else:
                metadata = extract_api(args.output, credentials=args.credentials, source_id=args.source_id,
                                       downloads=args.downloads, budget_cny=args.budget_cny, max_calls=args.max_calls)
                result = {k: metadata[k] for k in ("status", "model", "api_calls", "row_count", "estimated_cost_cny_peak_no_cache")}
        elif args.command == "align":
            result = align_csv(args.input, args.output)
        elif args.command == "resolve":
            result = resolve_alias(args.name)
        elif args.command == "validate":
            records = get_records(args.db) if args.db else load_records(args.input)
            report = validate_and_export(records, args.output_dir)
            result = {"source_issues": len(report["source_check"]["issues"]),
                      "ord_structurally_ready_ids": report["ord_structurally_ready_ids"],
                      "ord_incomplete_ids": report["ord_incomplete_ids"], "report": str(args.output_dir / "validation.json")}
        elif args.command == "check-evidence":
            result = check_evidence()
        elif args.command == "build":
            result = build_database(load_records(args.input), args.db, entity_cache())
        elif args.command == "query":
            result = get_history(args.db, args.history) if args.history else query_records(args.db, args.min_yield, args.name)
            if args.output:
                write_json(args.output, result)
        elif args.command == "make-patch":
            result = teaching_error_patch(args.db) if args.kind == "teaching-error" else reference_patch(args.db)
            write_json(args.output, result)
        elif args.command == "revise":
            result = apply_patch(args.db, read_json(args.patch))
        elif args.command == "export":
            records = get_records(args.db)
            save_records(args.output, records)
            result = {"record_count": len(records), "output": str(args.output)}
        elif args.command == "demo":
            result = demo(args.workdir)
        else:
            result = verify(args.workdir)
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError, KeyError) as error:
        print(f"操作未完成：{error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if isinstance(result, dict) and result.get("passed") is False else 0
