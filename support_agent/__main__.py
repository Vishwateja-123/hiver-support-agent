import argparse
import json
import sys
from pathlib import Path
from .core import Agent
from .data import prepare, read_jsonl, write_jsonl, check_leakage
from .evaluation import evaluate, validate_labels, judge_agreement
from .annotation import annotate
from .judge import run_judge

def main():
    parser=argparse.ArgumentParser(description='Auditable AppleSupport agent — Python standard library only')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--csv',required=True);p.add_argument('--out',required=True)
    p.add_argument('--max-pairs',type=int,default=4000)
    p=sub.add_parser('predict');p.add_argument('--train',required=True);p.add_argument('--text',required=True)
    p.add_argument('--system',choices=['agent','majority','nearest'],default='agent');p.add_argument('--threshold',type=float,default=.4)
    p=sub.add_parser('evaluate');p.add_argument('--train',required=True);p.add_argument('--test',required=True);p.add_argument('--out',required=True)
    p.add_argument('--labels');p.add_argument('--threshold',type=float,default=.4)
    for name in ('annotate','rate'):
        p=sub.add_parser(name);p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--annotator',required=True)
    p=sub.add_parser('judge');p.add_argument('--predictions',required=True);p.add_argument('--out',required=True);p.add_argument('--model',required=True);p.add_argument('--limit',type=int,default=60)
    p=sub.add_parser('agreement');p.add_argument('--judge',required=True);p.add_argument('--human',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('attach-labels');p.add_argument('--input',required=True);p.add_argument('--labels',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('rating-pack');p.add_argument('--predictions',required=True);p.add_argument('--judge',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('audit');p.add_argument('--data',required=True);p.add_argument('--gold');p.add_argument('--agreement')
    args=parser.parse_args()
    try:
        if hasattr(args,'threshold') and not 0<=args.threshold<=1:raise ValueError('Threshold must be in [0,1]')
        if args.command=='prepare':
            if args.max_pairs<4:raise ValueError('max-pairs must be at least 4')
            result=prepare(args.csv,args.out,max_pairs=args.max_pairs)
        elif args.command=='predict':result=Agent(read_jsonl(args.train),args.threshold).predict(args.text,args.system)
        elif args.command=='evaluate':result=evaluate(args.train,args.test,args.out,args.labels,args.threshold)
        elif args.command in ('annotate','rate'):result=annotate(args.input,args.out,args.annotator,args.command=='rate')
        elif args.command=='judge':
            if args.limit<1:raise ValueError('Judge limit must be positive')
            result=run_judge(args.predictions,args.out,args.model,args.limit)
        elif args.command=='agreement':
            result=judge_agreement(args.judge,args.human)
            Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
        elif args.command=='attach-labels':
            rows=read_jsonl(args.input);labels=validate_labels(read_jsonl(args.labels),[r['id'] for r in rows])
            write_jsonl(args.out,[dict(r,**{k:v for k,v in labels[r['id']].items() if k!='id'}) for r in rows]);result={'attached':len(rows)}
        elif args.command=='rating-pack':
            rows={r['prediction_id']:r for r in read_jsonl(args.predictions)}
            js=read_jsonl(args.judge)
            selected=[rows[r['prediction_id']] for r in js if r.get('status')=='ok']
            write_jsonl(args.out,selected);result={'examples':len(selected)}
        else:
            base=Path(args.data);splits={s:read_jsonl(base/(s+'.jsonl')) for s in ('train','dev','test')}
            for a,b in [('train','dev'),('train','test'),('dev','test')]:check_leakage(splits[a],splits[b])
            blockers=[]
            if not 150<=len(splits['test'])<=250:blockers.append('Need 150–250 real evaluation examples')
            if args.gold:validate_labels(read_jsonl(args.gold),[r['id'] for r in splits['test']])
            else:blockers.append('Human golden labels missing')
            if args.agreement:
                ratings=json.loads(Path(args.agreement).read_text())
                if ratings.get('rated_predictions',0)<30:blockers.append('Fewer than 30 paired human/judge ratings')
            else:blockers.append('Human–LLM judge agreement evidence missing')
            result={'data_leakage_checks':'passed','submission_data_ready':not blockers,'blockers':blockers}
        print(json.dumps(result,indent=2,ensure_ascii=False))
        if args.command=='audit' and result['blockers']:return 2
        return 0
    except (ValueError,RuntimeError,OSError,KeyError) as e:
        print('Error: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
