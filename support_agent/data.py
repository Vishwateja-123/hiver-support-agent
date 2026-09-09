import csv
import hashlib
import json
import random
import sqlite3
import tempfile
from pathlib import Path
from .core import clean, normalized, weak_intent

def read_jsonl(path):
    with open(path,encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def write_jsonl(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

class Union:
    def __init__(self): self.p={}
    def find(self,x):
        self.p.setdefault(x,x)
        root=x
        while self.p[root]!=root: root=self.p[root]
        while x!=root:
            nxt=self.p[x]; self.p[x]=root; x=nxt
        return root
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        self.p[max(a,b)]=min(a,b)

def prepare(csv_path,out,brand='AppleSupport',max_pairs=4000,seed=41):
    """Disk-backed joins; entire conversations/users are grouped before splitting."""
    out=Path(out)
    if (out/'manifest.json').exists():
        raise ValueError('Output already prepared; choose a new directory to preserve annotations')
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        db=sqlite3.connect(str(Path(td)/'tweets.sqlite'))
        db.execute('CREATE TABLE tweets(id TEXT PRIMARY KEY, author TEXT, inbound INTEGER, created TEXT, text TEXT, parent TEXT)')
        n=0
        with open(csv_path,newline='',encoding='utf-8-sig') as f:
            reader=csv.DictReader(f)
            needed={'tweet_id','author_id','inbound','created_at','text','in_response_to_tweet_id'}
            if not needed.issubset(reader.fieldnames or []): raise ValueError('Not a TWCS CSV; missing required columns')
            batch=[]
            for r in reader:
                batch.append((r['tweet_id'],r['author_id'],int(r['inbound'].lower()=='true'),r['created_at'],r['text'],r['in_response_to_tweet_id']))
                n+=1
                if len(batch)==10000:
                    db.executemany('INSERT OR IGNORE INTO tweets VALUES(?,?,?,?,?,?)',batch);batch=[]
            db.executemany('INSERT OR IGNORE INTO tweets VALUES(?,?,?,?,?,?)',batch)
        db.commit()
        # One deterministic direct brand reply per incoming message; no row-adjacency joins.
        pairs={}
        q='SELECT c.id,c.author,c.created,c.text,c.parent,b.id,b.text FROM tweets b JOIN tweets c ON b.parent=c.id WHERE b.author=? AND b.inbound=0 AND c.inbound=1 ORDER BY b.id'
        for cid,author,created,text,parent,bid,reply in db.execute(q,(brand,)):
            if cid not in pairs:
                pairs[cid]=dict(id=cid,customer_id=author,created_at=created,text=clean(text),
                                reply_id=bid,reference_reply=clean(reply),parent=parent,brand=brand)
        if len(pairs)<4: raise ValueError(f'Only {len(pairs)} paired messages for {brand}; need at least 4')
        # Build group identity on ALL brand pairs before capping. Ancestor traversal connects
        # cross-customer branches; customer identity connects multiple separate conversations.
        u=Union(); ancestor_cache={}
        def ancestors(cid):
            if cid in ancestor_cache: return ancestor_cache[cid]
            seen=set(); cursor=cid; chain=[]
            while cursor and cursor not in seen:
                seen.add(cursor)
                r=db.execute('SELECT id,author,inbound,created,text,parent FROM tweets WHERE id=?',(cursor,)).fetchone()
                if r is None: chain.append((cursor,None,None,None,None,None));break
                chain.append(r);cursor=r[5]
            ancestor_cache[cid]=chain
            return chain
        for r in pairs.values():
            key='tweet:'+r['id'];u.join(key,'user:'+r['customer_id'])
            for ancestor in ancestors(r['id']): u.join(key,'tweet:'+ancestor[0])
            norm=normalized(r['text'])
            if norm: u.join(key,'duplicate:'+hashlib.sha256(norm.encode()).hexdigest())
        rows=[]
        for r in pairs.values():
            chain=ancestors(r['id'])[1:]
            r['context']=[dict(id=a[0],role='customer' if a[2] else 'support',text=clean(a[4])) for a in reversed(chain[:6]) if a[4]]
            r['missing_context']=bool(r['parent']) and any(a[4] is None for a in chain)
            r['group_id']=hashlib.sha256(u.find('tweet:'+r['id']).encode()).hexdigest()[:20]
            r['suggested_intent']=weak_intent(r['text'])
            r.pop('parent'); rows.append(r)
        db.close()
    # Select groups in seeded random order; cap is soft to avoid cutting selected groups.
    grouped={}
    for r in rows: grouped.setdefault(r['group_id'],[]).append(r)
    groups=sorted(grouped);random.Random(seed).shuffle(groups)
    selected=[]
    for g in groups:
        if len(selected)>=max_pairs: break
        selected.extend(grouped[g])
    chosen={r['group_id'] for r in selected}
    group_order=[g for g in groups if g in chosen]
    if len(group_order)<3: raise ValueError('Need at least 3 independent groups for train/dev/test')
    # Allocate test first so the full-data recipe has 200 candidates when available.
    target_test=200 if len(selected)>=500 else max(1,round(len(selected)*.25))
    target_dev=100 if len(selected)>=500 else max(1,round(len(selected)*.15))
    assignments={};counts={'train':0,'dev':0,'test':0}
    for i,g in enumerate(group_order):
        remaining=len(group_order)-i
        split='test' if counts['test']<target_test and remaining>2 else 'dev' if counts['dev']<target_dev and remaining>1 else 'train'
        assignments[g]=split;counts[split]+=len(grouped[g])
    splits={s:sorted([r for r in selected if assignments[r['group_id']]==s],key=lambda r:r['id']) for s in counts}
    # Bound evaluation samples while retaining their entire groups outside training.
    rng=random.Random(seed)
    for split,limit in [('test',200),('dev',100)]:
        if len(splits[split])>limit: splits[split]=sorted(rng.sample(splits[split],limit),key=lambda r:r['id'])
    for s,rs in splits.items(): write_jsonl(out/(s+'.jsonl'),rs)
    manifest=dict(brand=brand,source_sha256=digest(csv_path),seed=seed,source_rows=n,
                  brand_pairs_before_cap=len(rows),max_pairs_soft_cap=max_pairs,
                  counts={s:len(rs) for s,rs in splits.items()},
                  group_counts={s:len({r['group_id'] for r in rs}) for s,rs in splits.items()},
                  label_status='unlabelled',sampling='seeded group random; user + ancestor + normalized exact duplicate grouping',
                  files={s+'.jsonl':digest(out/(s+'.jsonl')) for s in splits})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def check_leakage(train,test):
    for key in ('id','group_id','customer_id'):
        overlap={r[key] for r in train}&{r[key] for r in test}
        if overlap: raise ValueError(f'Leakage across {key}: {len(overlap)} overlapping values')
    a={normalized(r['text']) for r in train}-{''}
    b={normalized(r['text']) for r in test}-{''}
    if a&b: raise ValueError('Normalized text duplicate leakage')
