from copy import deepcopy

import pytest

from reaction_knowledge_lab.batch import (
    align_batch, batch_entities, batch_report, batch_rules, compare_batch, normalize_candidate,
    reference_records, transformation_key,
)
from reaction_knowledge_lab.store import (
    apply_patch, build_database, get_history, get_records, ingest_records,
)


def test_same_transformation_across_papers_keeps_experiments():
    rows = {r['record_id']: r for r in reference_records()}
    pair = [rows['nc2019-t1-9'], rows['nc2022-f6-a'], rows['nc2025-4q-Br']]
    assert len({transformation_key(r) for r in pair}) == 1
    assert len({r['record_id'] for r in pair}) == 3
    assert transformation_key(rows['nc2022-f6-g']) != transformation_key(pair[0])
    assert rows['nc2022-f6-g']['product']['entity_id'] == pair[0]['product']['entity_id']


def test_iodide_bromide_chloride_and_boronic_ester_not_conflated():
    rows = {r['record_id']: r for r in reference_records()}
    assert transformation_key(rows['nc2019-t1-1']) != transformation_key(rows['nc2019-t1-9'])
    assert transformation_key(rows['jacs2024-p7']) != transformation_key(rows['jacs2024-p8'])
    unknown = deepcopy(rows['nc2019-t1-9'])
    unknown['inputs'][0]['entity_id'] = None
    assert transformation_key(unknown) is None


def test_real_pooled_result_and_source_conflicts_are_preserved():
    rows = {r['record_id']: r for r in reference_records()}
    pooled = rows['jacs2024-p8']
    assert pooled['record_kind'] == 'pooled_result' and pooled['replicates'] == 5
    assert pooled['product']['mass_g'] == .180 and pooled['product']['yield_percent'] == 93
    for label, values in [('4s-Br', [89, 80]), ('4v-Br', [98, 99])]:
        r = rows['nc2025-'+label]
        assert r['product']['yield_percent'] is None
        assert [c['value'] for c in r['measurement']['yield_claims']] == values


def test_ingest_transaction_idempotency_and_conflict(tmp_path):
    rows = reference_records()
    db = tmp_path/'batch.sqlite'
    build_database(rows[:1], db, batch_entities())
    assert ingest_records(rows[1:3], db, batch_entities())['added'] == 2
    assert ingest_records(rows[1:3], db, batch_entities())['status'] == 'already_ingested'
    bad = deepcopy(rows[1])
    bad['product']['yield_percent'] = 1
    with pytest.raises(ValueError, match='conflict'):
        ingest_records([rows[3], bad], db, batch_entities())
    assert len(get_records(db)) == 3
    assert len(get_history(db, bad['record_id'])) == 1


def test_revision_updates_groups_without_stale_cached_links(tmp_path):
    rows = {r['record_id']: r for r in reference_records()}
    selected = [rows['nc2019-t1-9'], rows['nc2022-f6-a']]
    db = tmp_path/'batch.sqlite'
    build_database(selected, db, batch_entities())
    assert len(batch_report(db)['cross_source_transformations']) == 1
    apply_patch(db, {'patch_id':'test-change', 'reason':'Test fixture only',
        'evidence':[{'source_id':'test','locator':'test fixture'}],
        'changes':[{'action':'replace','record_id':selected[0]['record_id'],'expected_revision':1,
                    'set':{'inputs':rows['nc2019-t1-1']['inputs']}}]})
    assert batch_report(db)['cross_source_transformations'] == []
    assert len(get_history(db, selected[0]['record_id'])) == 2


def test_bad_percentage_qualifiers_and_duplicate_label_rejected(tmp_path):
    raw = {'source_id':'nc2019','label':'t1-9','reactants':['4-bromotoluene','phenylboronic acid'],
           'product':'4-methylbiphenyl','yield_percent':101,'temperature':'room temperature','time':'overnight'}
    with pytest.raises(ValueError, match='yield'):
        normalize_candidate(raw)
    raw['yield_percent'] = None
    normalized = normalize_candidate(raw)
    assert normalized['conditions']['temperature_c'] is None
    assert normalized['conditions']['time_minutes'] is None
    from reaction_knowledge_lab.files import write_json
    p=tmp_path/'raw.json'; write_json(p,{'records':[raw,raw]})
    with pytest.raises(ValueError, match='Duplicate'):
        align_batch(p,tmp_path/'aligned.json')


def test_source_comparison_detects_reactant_and_measurement_changes():
    r = deepcopy(reference_records()[0])
    assert compare_batch([r], [r])['issues'] == []
    r['inputs'][0]['entity_id'] = None
    r['measurement']['yield_type'] = 'isolated'
    report = compare_batch([r], reference_records()[:1])
    assert {'inputs','measurement.yield_type'} <= {x['field'] for x in report['issues']}


def test_valid_but_wrong_structure_cannot_keep_a_trusted_entity_id():
    r=deepcopy(reference_records()[0]);r['product']['smiles']='CC'
    assert not batch_rules([r])['passed']
    assert any(i['field']=='product.smiles' for i in compare_batch([r],reference_records()[:1])['issues'])


def test_pooled_ord_does_not_mix_per_run_inputs_with_total_product_mass():
    from reaction_knowledge_lab.ord_bridge import to_ord
    r=next(r for r in reference_records() if r['record_id']=='jacs2024-p8')
    reaction=to_ord(r)
    assert all(c.amount.HasField('unmeasured') for group in reaction.inputs.values() for c in group.components)
    assert 'Pooled result from 5' in reaction.notes.procedure_details
    assert r['inputs'][0]['amount']['value']==.2
    assert any(m.amount.mass.value==pytest.approx(.18) for m in reaction.outcomes[0].products[0].measurements if m.HasField('amount'))


def test_malformed_paid_response_keeps_usage_before_parsing(tmp_path,monkeypatch):
    import io,json
    from reaction_knowledge_lab import batch_extraction as api
    from reaction_knowledge_lab.files import read_json
    monkeypatch.setattr(api,'_credentials',lambda _: 'test-placeholder')
    monkeypatch.setattr(api,'job_input',lambda *_:('test json prompt',[],[]))
    monkeypatch.setattr(api.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(json.dumps({'choices':[],'usage':{'prompt_tokens':100,'completion_tokens':20}}).encode()))
    output=tmp_path/'api.json'
    with pytest.raises(ValueError,match='原始响应'):
        api.extract_batch(output,mode='api',source_id='jacs2024',max_calls=1)
    meta=read_json(output.with_suffix('.metadata.json'))
    assert meta['status']=='parse_failed' and meta['api_calls']==1
    assert meta['calls'][0]['usage']['prompt_tokens']==100
    assert read_json(tmp_path/'api.calls/jacs2024.provider.json')['choices']==[]
    assert not output.exists()


def test_invalid_provider_json_is_saved_and_usage_marked_unknown(tmp_path,monkeypatch):
    import io
    from reaction_knowledge_lab import batch_extraction as api
    from reaction_knowledge_lab.files import read_json
    monkeypatch.setattr(api,'_credentials',lambda _: 'test-placeholder')
    monkeypatch.setattr(api,'job_input',lambda *_:('test json prompt',[],[]))
    monkeypatch.setattr(api.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(b'incomplete provider response'))
    output=tmp_path/'api.json'
    with pytest.raises(ValueError,match='原始字节'):
        api.extract_batch(output,mode='api',source_id='jacs2024',max_calls=1)
    meta=read_json(output.with_suffix('.metadata.json'))
    assert meta['usage_unknown'] and meta['api_calls']==1
    assert (tmp_path/'api.calls/jacs2024.provider.json').read_bytes()==b'incomplete provider response'


def test_offline_batch_and_verification_detects_tampered_export(tmp_path,monkeypatch):
    from reaction_knowledge_lab.batch import batch_demo,batch_verify
    import urllib.request
    def no_network(*args,**kwargs):raise AssertionError('offline replay must not call network')
    monkeypatch.setattr(urllib.request,'urlopen',no_network)
    work=tmp_path/'run'
    result=batch_demo(work)
    assert result['passed']
    (work/'validation/ord.json').write_text('{}')
    assert not batch_verify(work)['passed']
