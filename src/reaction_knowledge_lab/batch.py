"""Cross-paper identity, source comparison and updates for the bounded batch."""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from rdkit import Chem

from .alignment import parse_amount, resolve_alias, temperature_range, time_minutes
from .batch_sources import BATCH, manifest
from .files import load_records, read_json, save_records, sha256, write_json
from .ord_bridge import export_ord
from .store import apply_patch, build_database, get_history, get_records, ingest_records, query_records
from .validation import get_field


def batch_entities():
    return read_json(BATCH/'entities.json')['entities']


def reference_records():
    return read_json(BATCH/'reference.json')['records']


def normalize_candidate(raw):
    sources={s['source_id']:s for s in manifest()['sources']}
    sid=raw['source_id'];source=sources[sid]
    job=next(j for j in manifest()['jobs'] if j['source_id']==sid)
    if raw.get('label') not in job['labels']:
        raise ValueError('Unknown source-local label')
    value=raw.get('yield_percent')
    if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=100):
        raise ValueError('yield_percent must be a finite percentage or null')
    entities=batch_entities()
    def components(names,amounts,role):
        if not isinstance(names,list) or any(not isinstance(n,str) for n in names):
            raise ValueError('Names must be a list of strings')
        amounts=amounts or []
        result=[]
        for i,name in enumerate(names):
            amount=amounts[i] if len(amounts)==len(names) else None
            result.append({**resolve_alias(name,entities),'role':role,
                           'raw_amount':amount,'amount':parse_amount(amount) if isinstance(amount,str) else None})
        return result
    inputs=components(raw.get('reactants',[]),raw.get('reactant_amounts'),'reactant')
    if raw.get('base'):
        inputs+=components([raw['base']],[raw.get('base_amount')],'reagent')
    product={**resolve_alias(raw.get('product') or 'unknown product',entities),
             'yield_percent':value,'mass_g':None,'purity_percent':None}
    mass=parse_amount(raw['product_mass']) if isinstance(raw.get('product_mass'),str) else None
    if mass and mass['unit'] in ('g','mg'):
        product['mass_g']=mass['value']*(.001 if mass['unit']=='mg' else 1)
    kind=raw.get('record_kind','reported_result')
    if kind not in ('reported_result','pooled_result','source_conflict'):
        raise ValueError('Unknown record_kind')
    replicates=raw.get('replicates')
    if replicates is not None and (type(replicates) is not int or replicates<1):
        raise ValueError('replicates must be a positive integer or null')
    if kind=='source_conflict':
        product['yield_percent']=None
    label=raw['label']
    return {'record_id':sid+'-'+label,'source_id':sid,'raw_record_id':'model:'+sid+':'+label,
        'experiment_label':label,'status':'extracted','record_kind':kind,'replicates':replicates,
        'inputs':inputs,'solvents':components(raw.get('solvents',[]),raw.get('solvent_amounts'),'solvent'),
        'product':product,'conditions':{'raw_time':raw.get('time'),'time_minutes':time_minutes(raw.get('time')),
              'raw_temperature':raw.get('temperature'),'temperature_c':temperature_range(raw.get('temperature'))},
        'measurement':{'yield_type':raw.get('yield_type','unknown'),'yield_claims':[]},
        'catalyst':{'name':raw.get('catalyst'),'sample_id':sid+':'+str(raw.get('catalyst')),'loading':raw.get('catalyst_loading')},
        'source':{'doi':source['doi'],'url':source['url'],'locator':label+'; see pinned job fragments in data/batch/sources.json'},
        'evidence':[{'source_id':sid,'locator':label,'files':[f['file'] for f in job['fragments']]}],
        'notes':[raw.get('notes','')],'raw':deepcopy(raw)}


def align_batch(input_path,output_path):
    records=[normalize_candidate(r) for r in load_records(input_path)]
    if len({r['record_id'] for r in records})!=len(records):
        raise ValueError('Duplicate record_id; do not merge rows automatically')
    save_records(output_path,records)
    unresolved=[{'record_id':r['record_id'],'name':c['name']} for r in records
                for c in r['inputs']+r['solvents']+[r['product']] if c['entity_id'] is None]
    result={'record_count':len(records),'source_count':len({r['source_id'] for r in records}),
            'unresolved':unresolved,'method':'exact curated aliases + RDKit; no fuzzy identity merge'}
    write_json(Path(output_path).with_suffix('.alignment.json'),result)
    return result


def transformation_key(record):
    """Same resolved reactant multiset and product; not an experiment identity."""
    reactants=[c.get('entity_id') for c in record['inputs'] if c.get('role')=='reactant']
    product=record['product'].get('entity_id')
    if not reactants or not all(reactants) or not product:
        return None
    return tuple(sorted(reactants)),product


def batch_report(db):
    records=get_records(db);groups=defaultdict(list);entities=defaultdict(list)
    for r in records:
        key=transformation_key(r)
        if key is not None:groups[key].append(r)
        for c in r['inputs']+r['solvents']+[r['product']]:
            if c.get('entity_id'):entities[c['entity_id']].append(r)
    return {'record_count':len(records),'source_count':len({r['source_id'] for r in records}),
        'by_source':{sid:sum(r['source_id']==sid for r in records) for sid in sorted({r['source_id'] for r in records})},
        'cross_source_transformations':[{'reactant_ids':list(k[0]),'product_id':k[1],
             'source_ids':sorted({r['source_id'] for r in rows}),'record_ids':[r['record_id'] for r in rows]}
             for k,rows in sorted(groups.items()) if len({r['source_id'] for r in rows})>1],
        'cross_source_entity_count':sum(len({r['source_id'] for r in rows})>1 for rows in entities.values()),
        'pooled_result_ids':[r['record_id'] for r in records if r['record_kind']=='pooled_result'],
        'source_conflict_ids':[r['record_id'] for r in records if r['record_kind']=='source_conflict'],
        'unresolved_components':[{'record_id':r['record_id'],'name':c['name']} for r in records
                                for c in r['inputs']+r['solvents']+[r['product']] if not c.get('entity_id')],
        'note':'Counts are reported-result records, not a count of independent wet-lab runs.'}


def _signature(items):
    return sorted([(c.get('entity_id'),c.get('smiles'),c.get('role'),c.get('amount')) for c in items],key=repr)


def batch_rules(records):
    entities={e['entity_id']:e['smiles'] for e in batch_entities()}
    issues=[]
    for r in records:
        for c in r['inputs']+r['solvents']+[r['product']]:
            eid=c.get('entity_id');smiles=c.get('smiles')
            if eid is None:
                issues.append({'record_id':r['record_id'],'code':'unresolved_entity','severity':'warning','name':c.get('name')})
                continue
            molecule=Chem.MolFromSmiles(smiles or '')
            expected=entities.get(eid)
            if not expected or not smiles or molecule is None or Chem.MolToSmiles(molecule,isomericSmiles=True)!=Chem.MolToSmiles(Chem.MolFromSmiles(expected),isomericSmiles=True):
                issues.append({'record_id':r['record_id'],'code':'entity_structure_conflict','severity':'error','entity_id':eid})
        value=r['product'].get('yield_percent')
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=100):
            issues.append({'record_id':r['record_id'],'code':'invalid_percentage','severity':'error'})
        if r.get('record_kind')=='source_conflict' and value is not None:
            issues.append({'record_id':r['record_id'],'code':'unresolved_conflict_has_single_value','severity':'error'})
    return {'issues':issues,'passed':not any(i['severity']=='error' for i in issues)}


def compare_batch(records,reference=None):
    reference=reference_records() if reference is None else reference
    expected={r['record_id']:r for r in reference};actual={r['record_id']:r for r in records};issues=[]
    if len(actual)!=len(records):issues.append({'code':'duplicate_id','field':'record_id'})
    fields=['source_id','source.doi','product.entity_id','product.smiles','product.yield_percent','product.mass_g',
            'conditions.time_minutes','conditions.temperature_c','measurement.yield_type',
            'measurement.yield_claims','record_kind','replicates','catalyst.name','catalyst.loading']
    for rid in sorted(expected.keys()|actual.keys()):
        if rid not in expected or rid not in actual:
            issues.append({'record_id':rid,'code':'unexpected_record' if rid not in expected else 'missing_record','field':'record_id'})
            continue
        for field in fields+['inputs','solvents']:
            a,b=get_field(actual[rid],field),get_field(expected[rid],field)
            if field in ('inputs','solvents'):a,b=_signature(a),_signature(b)
            if a!=b:issues.append({'record_id':rid,'field':field,'actual':a,'expected':b,'code':'reference_difference',
                                   'locator':expected[rid]['source']['locator']})
    return {'issues':issues,'agreement_with_course_reference':not issues,
            'reference_status':'assistant-reviewed, independent teacher review pending',
            'unresolved_source_conflicts':[r['record_id'] for r in reference if r['record_kind']=='source_conflict']}


def review_patch(db,source_ids=None):
    current={r['record_id']:r for r in query_records(db)}
    wanted=[r for r in reference_records() if source_ids is None or r['source_id'] in source_ids]
    changes=[]
    for r in wanted:
        old=current.get(r['record_id'])
        if old is None:changes.append({'action':'add','record':r})
        elif compare_batch([old],[r])['issues']:
            fields={k:deepcopy(v) for k,v in r.items() if k not in ('record_id','source_id','raw_record_id','raw')}
            changes.append({'action':'replace','record_id':r['record_id'],'expected_revision':old['revision'],'set':fields})
    if not changes:return None
    digest=hashlib.sha256(json.dumps(changes,sort_keys=True).encode()).hexdigest()[:16]
    return {'patch_id':'batch-source-review-'+digest,
            'reason':'Apply assistant source-reviewed reference; preserves raw model output and unresolved source conflicts. Teacher approval of gold still pending.',
            'evidence':[{'source_id':r['source_id'],**r['source']} for r in wanted], 'changes':changes}


def batch_validate(records,output_dir,source_ids=None):
    output_dir=Path(output_dir)
    reference=reference_records()
    if source_ids is not None:
        if not set(source_ids)<={r['source_id'] for r in reference}:raise ValueError('Unknown reference source_id')
        reference=[r for r in reference if r['source_id'] in source_ids]
    result={'source_comparison':compare_batch(records,reference), 'rules':batch_rules(records), 'ord':export_ord(records,output_dir/'ord.json'),
            'records_sha256':_records_hash(records),'ord_sha256':sha256(output_dir/'ord.json')}
    write_json(output_dir/'validation.json',result)
    return result


def _records_hash(records):
    return hashlib.sha256(json.dumps(sorted(records,key=lambda r:r['record_id']),sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def batch_verify(workdir):
    workdir=Path(workdir);db=workdir/'knowledge.sqlite';records=get_records(db)
    report=batch_report(db);comparison=compare_batch(records)
    history=get_history(db,'nc2019-t1-9')
    validation=read_json(workdir/'validation/validation.json')
    regression=read_json(workdir/'query-regression.json')
    checks={'40_records':report['record_count']==40,'4_sources':report['source_count']==4,
        'reference_fields_match':not comparison['issues'],
        'entity_structure_consistency':batch_rules(records)['passed'],
        'cross_paper_transformation':any({'nc2019-t1-9','nc2022-f6-a','nc2025-4q-Br'}<=set(g['record_ids']) for g in report['cross_source_transformations']),
        'same_product_different_reactants':transformation_key(next(r for r in records if r['record_id']=='nc2022-f6-a'))!=transformation_key(next(r for r in records if r['record_id']=='nc2022-f6-g')),
        'pooled_result_not_split':report['pooled_result_ids']==['jacs2024-p8'],
        'real_source_conflicts_retained':set(report['source_conflict_ids'])=={'nc2025-4s-Br','nc2025-4v-Br'},
        'teaching_revision_in_history':27 in [h['record']['product'].get('yield_percent') for h in history] and history[-1]['record']['product']['yield_percent']==95,
        'aliases_equivalent':{r['record_id'] for r in query_records(db,name='phenylboronic acid')}=={r['record_id'] for r in query_records(db,name='benzeneboronic acid')},
        'reimport_idempotent':read_json(workdir/'incremental.json')['repeat']['status']=='already_ingested',
        'ord_current_export_checked':validation['records_sha256']==_records_hash(records) and validation['ord_sha256']==sha256(workdir/'validation/ord.json') and not validation['ord']['dataset_errors'],
        'query_regression':regression['before']==29 and regression['after_error']==28 and regression['after_correction']==29}
    result={'passed':all(checks.values()),'checks':checks,'report':report,
            'scientific_review':'Software passed does not resolve the two source conflicts or replace teacher review.'}
    write_json(workdir/'verification.json',result)
    return result


def batch_demo(workdir):
    from .batch_extraction import extract_batch
    workdir=Path(workdir)
    if workdir.exists() and any(workdir.iterdir()):raise FileExistsError('使用新的空工作目录。')
    workdir.mkdir(parents=True,exist_ok=True)
    extract_batch(workdir/'raw.json')
    align_batch(workdir/'raw.json',workdir/'aligned.json')
    rows=load_records(workdir/'aligned.json');holdout=manifest()['holdout_source']
    initial=[r for r in rows if r['source_id']!=holdout];later=[r for r in rows if r['source_id']==holdout]
    save_records(workdir/'initial.json',initial);save_records(workdir/'holdout.json',later)
    db=workdir/'knowledge.sqlite';build_database(initial,db,batch_entities())
    write_json(workdir/'before.json',batch_report(db))
    write_json(workdir/'initial-differences.json',compare_batch(initial,[r for r in reference_records() if r['source_id']!=holdout]))
    patch=review_patch(db,{r['source_id'] for r in initial})
    if patch:write_json(workdir/'review-initial.json',patch);apply_patch(db,patch)
    target=next(r for r in query_records(db) if r['record_id']=='nc2019-t1-9')
    before=len(query_records(db,min_yield=90))
    error={'patch_id':'batch-controlled-teaching-error','reason':'Explicit teaching error, not an error made by the model or authors.',
       'evidence':[{'source_id':'course-teaching-fixture','locator':'Set nc2019-t1-9 yield to 27 for revision exercise'}],
       'changes':[{'action':'replace','record_id':target['record_id'],'expected_revision':target['revision'],'set':{'product.yield_percent':27}}]}
    write_json(workdir/'teaching-error.json',error);apply_patch(db,error)
    during=len(query_records(db,min_yield=90))
    correction=review_patch(db,{r['source_id'] for r in initial})
    write_json(workdir/'correction.json',correction);apply_patch(db,correction)
    write_json(workdir/'query-regression.json',{'before':before,'after_error':during,'after_correction':len(query_records(db,min_yield=90)),'threshold':90})
    first=ingest_records(later,db,batch_entities());repeat=ingest_records(later,db,batch_entities())
    write_json(workdir/'incremental.json',{'first':first,'repeat':repeat})
    patch=review_patch(db,{holdout})
    if patch:write_json(workdir/'review-holdout.json',patch);apply_patch(db,patch)
    save_records(workdir/'final.json',get_records(db))
    batch_validate(get_records(db),workdir/'validation')
    return batch_verify(workdir)
