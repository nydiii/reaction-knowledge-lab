"""Replay authentic ReactionSeek output, or run its prompt with DeepSeek.

The HTTP client, budget checks, and Markdown parser are course adaptations.
The upstream prompt is downloaded at a pinned commit, not executed as Python.
"""
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .files import DATA, read_json, sha256, write_json

CASE = "volume102article22"
COMMIT = "6d42c4a1c5e47e1a5544b67a5b3ce9b00dbf8f6a"
COLUMNS = ["Reactants", "Reactant amounts", "Products", "Product amounts",
           "Solvents", "Reaction temperature", "Reaction time", "Yield"]


def fetch_sources(destination=None):
    destination = Path(destination or DATA / "downloads")
    destination.mkdir(parents=True, exist_ok=True)
    results = []
    for item in read_json(DATA / "sources.json")["files"]:
        path = destination / item["target"]
        if not path.exists():
            request = urllib.request.Request(item["url"], headers={"User-Agent": "reaction-knowledge-lab/0.1"})
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read()
            if hashlib.sha256(body).hexdigest() != item["sha256"]:
                raise ValueError(f"下载哈希不一致：{item['name']}；未保存该文件。")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        if sha256(path) != item["sha256"]:
            raise ValueError(f"本地文件被修改：{path}；请保留修改副本后重新下载。")
        results.append({"name": item["name"], "path": str(path), "sha256": item["sha256"]})
    return results


def _check_download(name, directory):
    item = next(x for x in read_json(DATA / "sources.json")["files"] if x["name"] == name)
    path = Path(directory) / item["target"]
    if not path.exists():
        raise FileNotFoundError("先运行 python -m reaction_knowledge_lab fetch 下载上游输入与提示词。")
    if sha256(path) != item["sha256"]:
        raise ValueError(f"上游文件校验失败：{name}")
    return path


def upstream_prompt(script, title, procedure):
    """Extract only a literal f-string; never import/execute upstream code."""
    tree = ast.parse(Path(script).read_text(encoding="utf-8"))
    function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "get_names")
    assignment = next(x for x in function.body if isinstance(x, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "prompt" for t in x.targets))
    values = {"title": title, "text": procedure}
    if not isinstance(assignment.value, ast.JoinedStr):
        raise ValueError("上游提示词结构发生变化。")
    parts = []
    for part in assignment.value.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            parts.append(part.value)
        elif isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name) and part.value.id in values:
            parts.append(values[part.value.id])
        else:
            raise ValueError("提示词包含未支持的动态表达式，已停止。")
    return "".join(parts)


def parse_table(text, source_id, procedure_number=1):
    rows = []
    header_seen = False
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if [x.casefold() for x in cells] == [x.casefold() for x in COLUMNS]:
            header_seen = True
            continue
        if not header_seen or all(re.fullmatch(r"[:\-\s]+", cell or "-") for cell in cells):
            continue
        if len(cells) != len(COLUMNS):
            raise ValueError("模型表格列数不是8；原始响应已保存，请人工检查，不自动猜列。")
        rows.append({"Index": f"{source_id}_{procedure_number}_{len(rows)+1}", **dict(zip(COLUMNS, cells))})
    if not rows:
        raise ValueError("没有解析到8列表格；请查看已保存的原始响应。")
    return rows


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["Index", *COLUMNS])
        writer.writeheader()
        writer.writerows(rows)


def replay(output, source_id=CASE):
    source = DATA / "replay/upstream_output_table.csv"
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = [row for row in csv.DictReader(stream)
                if source_id == "all" or row["Index"].startswith(source_id + "_")]
    if not rows:
        raise ValueError(f"上游回放没有此文档：{source_id}")
    write_csv(output, rows)
    metadata = {"mode": "replay", "source_id": source_id, "row_count": len(rows),
                "upstream_commit": COMMIT, "upstream_file_sha256": sha256(source),
                "api_calls": 0, "cost_cny": 0, "note": "作者公开的GLM示例输出，不是本次模型调用。"}
    write_json(Path(output).with_suffix(".metadata.json"), metadata)
    return metadata


def _credentials(path):
    config = read_json(path) if path else {}
    key = os.environ.get("DEEPSEEK_API_KEY") or config.get("api_key")
    if not key:
        raise ValueError("未配置 DEEPSEEK_API_KEY，或使用 --credentials 指向本地配置。回放不需要密钥。")
    return key


def extract_api(output, *, credentials=None, source_id=CASE, downloads=None,
                budget_cny=1.0, max_calls=1, max_output_tokens=2048):
    """One request per procedure; no hidden retry, no reasoning, no web tools."""
    output = Path(output)
    if output.exists() or output.with_suffix(".metadata.json").exists():
        raise ValueError("API输出路径已有结果，请换新目录，避免覆盖或重复付费。")
    if not 0 < budget_cny <= 1.0:
        raise ValueError("课堂调用预算需大于0且不超过1元；批量研究请另行配置。")
    if not 1 <= max_output_tokens <= 4096:
        raise ValueError("max_output_tokens需为1至4096。")
    directory = Path(downloads or DATA / "downloads")
    data_path = _check_download("input.json", directory)
    script = _check_download("GLM_evaluate.py", directory)
    documents = read_json(data_path)
    selected = documents if source_id == "all" else {source_id: documents[source_id]}
    jobs = [(name, doc["Title"], n, text) for name, doc in selected.items()
            for n, text in enumerate(doc["Procedure"], 1)]
    if len(jobs) > max_calls:
        raise ValueError(f"将调用{len(jobs)}次，超过--max-calls={max_calls}；请显式指定上限。")
    prompts = [upstream_prompt(script, title, text) for _, title, _, text in jobs]
    # UTF-8 byte count is a conservative token-count bound for this text request.
    reserve = sum((len(p.encode("utf-8")) + 1024) * 2 / 1e6 + max_output_tokens * 8 / 1e6 for p in prompts)
    if reserve > budget_cny:
        raise ValueError(f"请求前保守预留{reserve:.4f}元，超过预算{budget_cny:.2f}元；未发送请求。")
    key = _credentials(credentials)
    output.parent.mkdir(parents=True, exist_ok=True)
    calls, rows = [], []
    metadata = {"mode": "api", "provider": "DeepSeek", "model": "deepseek-flash",
                "thinking": "disabled", "upstream_commit": COMMIT,
                "input_sha256": sha256(data_path), "prompt_source_sha256": sha256(script),
                "pricing_checked": "2026-11-10", "price_assumption": "peak: input 2 CNY/M, output 8 CNY/M; ignore cache discount",
                "reserved_cny": reserve, "budget_cny": budget_cny, "calls": calls,
                "started_at": datetime.now(timezone.utc).isoformat(), "status": "running"}
    meta_path = output.with_suffix(".metadata.json")
    write_json(meta_path, metadata)
    for (name, _, number, _), prompt in zip(jobs, prompts):
        body = {"model": "deepseek-flash", "messages": [{"role": "user", "content": prompt}],
                "temperature": 0, "thinking": {"type": "disabled"}, "max_tokens": max_output_tokens, "stream": False}
        request = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                         data=json.dumps(body).encode(),
                                         headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            metadata["status"] = "request_failed"
            metadata["error_type"] = type(error).__name__
            metadata["http_status"] = getattr(error, "code", None)
            write_json(meta_path, metadata)
            raise RuntimeError("API请求失败；没有自动重试。请检查网络、余额和模型权限；不要粘贴密钥排错。") from None
        choice = result["choices"][0]
        content = choice["message"].get("content") or ""
        usage = result.get("usage", {})
        call = {"source_id": name, "procedure_number": number, "response_id": result.get("id"),
                "served_model": result.get("model"), "usage": usage,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "finish_reason": choice.get("finish_reason"), "content": content}
        calls.append(call)
        metadata["api_calls"] = len(calls)
        metadata["estimated_cost_cny_peak_no_cache"] = sum(
            c["usage"].get("prompt_tokens", 0) * 2 / 1e6 + c["usage"].get("completion_tokens", 0) * 8 / 1e6 for c in calls)
        write_json(meta_path, metadata)
        if choice.get("finish_reason") != "stop":
            metadata["status"] = "incomplete_response"
            write_json(meta_path, metadata)
            raise ValueError("模型输出未正常结束；已保存响应与用量，不把截断结果入库。")
        try:
            rows.extend(parse_table(content, name, number))
        except ValueError:
            metadata["status"] = "parse_failed"
            write_json(meta_path, metadata)
            raise
    write_csv(output, rows)
    metadata.update(status="complete", row_count=len(rows))
    write_json(meta_path, metadata)
    return metadata
