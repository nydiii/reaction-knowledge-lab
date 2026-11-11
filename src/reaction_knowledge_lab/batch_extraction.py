"""Authentic saved responses and explicit, bounded DeepSeek batch requests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

from .batch_sources import BATCH, job_input, manifest
from .extraction import _credentials
from .files import DATA, read_json, sha256, write_json


def response_records(content, job):
    payload = json.loads(content)
    rows = payload.get('records')
    if not isinstance(rows, list):
        raise ValueError('API JSON must contain a records array')
    seen, result = set(), []
    for row in rows:
        label = row.get('label')
        if label not in job['labels'] or label in seen:
            raise ValueError('Invalid or duplicate source-local label: '+str(label))
        seen.add(label)
        result.append({**row, 'source_id':job['source_id']})
    return result


def extract_batch(output, *, mode='replay', source_id='all', credentials=None,
                  downloads=DATA/'downloads/batch', budget_cny=1.0, max_calls=1):
    output = Path(output)
    meta_path = output.with_suffix('.metadata.json')
    if output.exists() or meta_path.exists():
        raise FileExistsError('输出已存在，请使用新路径，避免覆盖或重复付费。')
    jobs = [j for j in manifest()['jobs'] if source_id=='all' or j['source_id']==source_id]
    if not jobs:
        raise ValueError('Unknown source_id')
    rows=[]
    if mode=='replay':
        integrity = read_json(BATCH/'replay/manifest.json')
        for job in jobs:
            path=BATCH/'replay'/f"{job['source_id']}.json"
            if sha256(path) != integrity['files'][path.name]:
                raise ValueError('保存的真实响应哈希不符：'+path.name)
            saved=read_json(path)
            rows.extend(response_records(saved['content'],job))
        write_json(output, {'schema_version':1,'records':rows})
        meta={'mode':'replay','api_calls':0,'cost_cny':0,'row_count':len(rows),
              'source_count':len(jobs),'origin':'Real course DeepSeek responses; not original ReactionSeek output'}
        write_json(meta_path,meta)
        return meta
    if mode != 'api' or not 0 < budget_cny <= 1 or len(jobs)>max_calls:
        raise ValueError('需 mode=api、0<budget<=1，并显式设置足够的 --max-calls。')
    prepared=[(j,*job_input(j,downloads)) for j in jobs]
    max_output=8192
    # Image allowance is an estimate, not a provider-side spending limit.
    # Only the three pinned figures can be sent; byte/text allowance is separate.
    reserve=sum((len(prompt.encode())+1024+len(images)*32768)*2/1e6+max_output*8/1e6
                for _,prompt,images,_ in prepared)
    if reserve>budget_cny:
        raise ValueError(f'预估预留 {reserve:.4f} 元超过预算，未发送请求。')
    key=_credentials(credentials)
    meta={'mode':'api','provider':'DeepSeek','model':'deepseek-flash','status':'running',
          'api_calls':0,'calls':[],'budget_cny':budget_cny,'reserved_cny':reserve,
          'started_at':datetime.now(timezone.utc).isoformat(),
          'pricing_checked':'2026-11-11','price_input_cny_per_million':2,'price_output_cny_per_million':8,
          'pricing_url':'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/',
          'budget_note':'Estimate at peak/no-cache prices; images reserve 32768 tokens each; not a provider hard cap.',
          'estimated_cost_cny_peak_no_cache':0}
    write_json(meta_path,meta)
    call_dir=output.parent/(output.stem+'.calls')
    for job,prompt,images,fingerprints in prepared:
        body={'model':'deepseek-flash','thinking':{'type':'disabled'},'temperature':0,
              'max_tokens':max_output,'response_format':{'type':'json_object'},'stream':False,
              'messages':[{'role':'user','content':[{'type':'text','text':prompt},*images]}]}
        request=urllib.request.Request('https://api.deepseek.com/chat/completions',
            data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        provider_path=call_dir/(job['source_id']+'.provider.json')
        try:
            with urllib.request.urlopen(request,timeout=180) as response:
                response_bytes=response.read()
        except OSError as error:
            meta.update(status='request_failed',error_type=type(error).__name__)
            write_json(meta_path,meta)
            raise RuntimeError('批量 API 请求失败；未自动重试，已保存此前响应与用量。') from None
        provider_path.parent.mkdir(parents=True,exist_ok=True)
        provider_path.write_bytes(response_bytes)
        try:
            result=json.loads(response_bytes)
        except (ValueError,UnicodeError):
            meta['api_calls']+=1
            meta['calls'].append({'source_id':job['source_id'],'provider_response':str(provider_path),'usage':None})
            meta.update(status='parse_failed',usage_unknown=True)
            write_json(meta_path,meta)
            raise ValueError('API响应不是有效JSON；原始字节已保存，用量未知，停止后续调用。') from None
        usage=result.get('usage',{}) if isinstance(result,dict) else {}
        usage=usage if isinstance(usage,dict) else {}
        cost=usage.get('prompt_tokens',0)*2/1e6+usage.get('completion_tokens',0)*8/1e6
        meta['calls'].append({'source_id':job['source_id'],'provider_response':str(provider_path),'usage':usage})
        meta['api_calls']+=1
        meta['estimated_cost_cny_peak_no_cache']+=cost
        write_json(meta_path,meta)
        try:
            choice=result['choices'][0]
            content=choice['message']['content']
            if not isinstance(content,str):raise ValueError('Response content is not text')
        except (ValueError,TypeError,KeyError,IndexError,AttributeError):
            meta['status']='parse_failed';write_json(meta_path,meta)
            raise ValueError('API响应结构不完整；原始响应与已知用量已保存，未自动重试。') from None
        call={'source_id':job['source_id'],'response_id':result.get('id'),'served_model':result.get('model'),
              'usage':usage,'finish_reason':choice.get('finish_reason'),
              'content':content,
              'input_files':fingerprints,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
              'prompt_template_sha256':sha256(BATCH/'prompt.txt'),'timestamp':datetime.now(timezone.utc).isoformat()}
        path=call_dir/(job['source_id']+'.json')
        write_json(path,call)
        meta['calls'][-1]['path']=str(path)
        write_json(meta_path,meta)
        try:
            if call['finish_reason']!='stop':
                raise ValueError('API response did not finish normally')
            rows.extend(response_records(call['content'],job))
        except (ValueError,TypeError,KeyError,IndexError,AttributeError):
            meta['status']='parse_failed';write_json(meta_path,meta)
            raise ValueError('API表格结构未通过检查；原始响应与用量已保存，未自动重试。') from None
        if meta['estimated_cost_cny_peak_no_cache']>budget_cny:
            meta['status']='budget_exceeded';write_json(meta_path,meta)
            raise ValueError('已记录用量超过预算；后续请求停止。')
    write_json(output,{'schema_version':1,'records':rows})
    meta.update(status='complete',row_count=len(rows),source_count=len(jobs))
    write_json(meta_path,meta)
    return {k:meta[k] for k in ('status','api_calls','row_count','source_count','estimated_cost_cny_peak_no_cache')}
