import collections
import hashlib
import json
import math
from pathlib import Path
from .core import Agent, INTENTS, RISK, weak_intent
from .data import check_leakage, read_jsonl, write_jsonl, digest

SYSTEMS=('majority','nearest','agent')

def ratio(a,b): return a/b if b else None

def wilson(success,total):
    if not total: return None
    z=1.96;p=success/total;d=1+z*z/total
    center=(p+z*z/(2*total))/d
    radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [max(0,center-radius),min(1,center+radius)]

def classification(gold,pred):
    matrix={a:{b:0 for b in INTENTS} for a in INTENTS}
    for a,b in zip(gold,pred): matrix[a][b]+=1
    per={}
    for label in INTENTS:
        tp=matrix[label][label];support=sum(matrix[label].values())
        pp=sum(matrix[a][label] for a in INTENTS)
        per[label]=dict(support=support,precision=ratio(tp,pp),recall=ratio(tp,support),
                        f1=2*tp/(support+pp) if support+pp else 0)
    return dict(accuracy=ratio(sum(a==b for a,b in zip(gold,pred)),len(gold)),
                macro_f1=sum(p['f1'] for p in per.values())/len(INTENTS),
                macro_f1_supported=ratio(sum(p['f1'] for p in per.values() if p['support']),sum(p['support']>0 for p in per.values())),
                per_intent=per,confusion_matrix=matrix)

def validate_labels(rows,expected_ids=None):
    ids=[r['id'] for r in rows]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate label IDs')
    if expected_ids is not None and set(ids)!=set(expected_ids): raise ValueError('Label IDs must exactly match evaluation IDs')
    for r in rows:
        if r.get('intent') not in INTENTS or r.get('should_escalate') not in ('yes','no'):
            raise ValueError(f"Invalid or missing labels: {r['id']}")
        if r.get('label_source')!='human' or not r.get('annotator','').strip() or not r.get('rationale','').strip():
            raise ValueError(f"Human attribution and rationale required: {r['id']}")
    return {r['id']:r for r in rows}

def evaluate(train_path,test_path,out,labels_path=None,threshold=.4):
    train=read_jsonl(train_path);test=read_jsonl(test_path)
    if not test: raise ValueError('Evaluation set is empty')
    check_leakage(train,test)
    gold=validate_labels(read_jsonl(labels_path),[r['id'] for r in test]) if labels_path else {}
    agent=Agent(train,threshold); predictions=[]; metrics={}
    for name in SYSTEMS:
        results=[agent.predict(r['text'],name,r.get('context'),r.get('missing_context',False)) for r in test]
        auto=[i for i,p in enumerate(results) if p['decision']=='auto']
        item=dict(n=len(test),auto_count=len(auto),coverage=len(auto)/len(test),
                  emitted_sensitive_pattern_count=sum(bool(RISK.search(p['reply'])) for p in results),
                  note='Sensitive-pattern count is a lexical diagnostic, not a safety score.')
        if gold:
            item.update(classification([gold[r['id']]['intent'] for r in test],[p['intent'] for p in results]))
            unsafe=sum(gold[test[i]['id']]['should_escalate']=='yes' for i in auto)
            needs=sum(gold[r['id']]['should_escalate']=='yes' for r in test)
            correct=sum(p['intent']==gold[test[i]['id']]['intent'] for i,p in enumerate(results) if i in auto)
            item.update(unsafe_auto_count=unsafe,unsafe_auto_rate=ratio(unsafe,len(auto)),
                        unsafe_auto_95ci=wilson(unsafe,len(auto)),escalation_recall=ratio(needs-unsafe,needs),
                        selective_intent_accuracy=ratio(correct,len(auto)))
        else:
            item['human_metrics']=None
            item['weak_label_agreement_diagnostic']=classification([weak_intent(r['text']) for r in test],[p['intent'] for p in results])
        metrics[name]=item
        for row,p in zip(test,results):
            p.update(id=row['id'],system=name,text=row['text'],context=row['context'],group_id=row['group_id'])
            p['prediction_id']=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()[:24]
            predictions.append(p)
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    write_jsonl(output/'predictions.jsonl',predictions)
    summary=dict(status='human_labelled_evaluation' if gold else 'SMOKE_TEST_ONLY_NO_HUMAN_GOLD',
                 threshold=threshold,threshold_status='preset_not_calibrated',
                 train_sha256=digest(train_path),test_sha256=digest(test_path),
                 labels_sha256=digest(labels_path) if labels_path else None,
                 training_label_source='human where provided; otherwise weak keyword labels',
                 systems=metrics,judge_status='not_run',human_judge_agreement=None)
    (output/'metrics.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Evaluation results','',f"Status: **{summary['status']}**",'',
           '| System | N | Auto eligible | Coverage | Human accuracy |',
           '|---|---:|---:|---:|---:|']
    for name,m in metrics.items():
        accuracy=f"{m['accuracy']:.3f}" if 'accuracy' in m else 'Not available'
        lines.append(f"| {name} | {m['n']} | {m['auto_count']} | {m['coverage']:.1%} | {accuracy} |")
    lines+=['','Auto eligibility is a simulated routing decision; no reply is sent.',
            'Weak-label agreement is circular with weakly labelled training and must not be presented as accuracy.',
            'Reply quality and human–LLM judge agreement require independent ratings.']
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    return summary

def agreement(a,b):
    if len(a)!=len(b) or not a: raise ValueError('Paired, non-empty ratings required')
    n=len(a);observed=sum(x==y for x,y in zip(a,b))/n
    ca,cb=collections.Counter(a),collections.Counter(b)
    expected=sum(ca[x]*cb[x] for x in ca.keys()|cb.keys())/(n*n)
    return dict(n=n,exact_agreement=observed,cohens_kappa=(observed-expected)/(1-expected) if expected<1 else None,
                mean_absolute_error=sum(abs(x-y) for x,y in zip(a,b))/n,
                exact_agreement_95ci=wilson(sum(x==y for x,y in zip(a,b)),n))

def judge_agreement(judge_path,human_path):
    from .judge import DIMENSIONS, validate_rating
    js=read_jsonl(judge_path);hs=read_jsonl(human_path)
    for rows in (js,hs):
        ids=[r['prediction_id'] for r in rows]
        if len(ids)!=len(set(ids)): raise ValueError('Duplicate prediction ratings')
        for r in rows: validate_rating(r)
    if not hs: raise ValueError('No human ratings')
    if any(r.get('label_source')!='human' or not r.get('annotator','').strip() for r in hs):
        raise ValueError('Human ratings need explicit attribution')
    j={r['prediction_id']:r for r in js}
    if any(r['prediction_id'] not in j for r in hs): raise ValueError('Unmatched human rating IDs')
    if any(r.get('status')!='ok' for r in js): raise ValueError('Judge errors must be resolved before agreement')
    out={d:agreement([r[d] for r in hs],[j[r['prediction_id']][d] for r in hs]) for d in DIMENSIONS}
    out['pass']=agreement([int(all(r[d]>=2 for d in DIMENSIONS)) for r in hs],
                          [int(all(j[r['prediction_id']][d]>=2 for d in DIMENSIONS)) for r in hs])
    out['rated_predictions']=len(hs);out['total_judged_predictions']=len(js)
    out['note']='Intervals treat ratings as independent; multiple systems from the same message are correlated. Small samples are exploratory.'
    return out
