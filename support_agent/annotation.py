import json
from pathlib import Path
from .core import INTENTS
from .data import read_jsonl, write_jsonl
from .judge import DIMENSIONS

def ask(prompt,choices):
    while True:
        value=input(prompt).strip()
        if value in choices:return value
        print('Choose one of: '+', '.join(choices))

def annotate(source,out,annotator,ratings=False):
    if not annotator.strip():raise ValueError('Provide your annotator name or stable alias')
    rows=read_jsonl(source);dest=Path(out)
    if Path(source).resolve()==dest.resolve():raise ValueError('Annotation output must differ from input')
    saved=read_jsonl(dest) if dest.exists() else []
    idkey='prediction_id' if ratings else 'id'
    done={r[idkey] for r in saved}
    for row in rows:
        if row[idkey] in done:continue
        print('\n'+'─'*64+'\nExample '+row[idkey])
        # Hide weak suggested labels and system identities to reduce anchoring.
        for c in row.get('context',[]):print(c['role']+': '+c['text'])
        print('CURRENT MESSAGE: '+row['text'])
        record={idkey:row[idkey], 'label_source':'human','annotator':annotator}
        if ratings:
            print('DRAFT: '+row['reply']+'\nROUTING: '+row['decision']+'\nREASON: '+row['reason'])
            print('EVIDENCE: '+json.dumps(row['evidence'],ensure_ascii=False,indent=2))
            for d in DIMENSIONS:record[d]=int(ask(d+' [0/1/2]: ',('0','1','2')))
        else:
            print('INTENTS: '+', '.join(INTENTS))
            record['intent']=ask('Intent: ',INTENTS)
            record['should_escalate']=ask('Requires human review for safe next response? [yes/no]: ',('yes','no'))
        rationale=''
        while not rationale:rationale=input('Brief rationale: ').strip()
        record['rationale']=rationale;saved.append(record)
        write_jsonl(dest,saved)
    return {'saved':len(saved),'path':str(dest)}
