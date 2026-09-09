import collections
import html
import math
import re

INTENTS = ('battery_power', 'connectivity', 'software_performance', 'apps_media',
           'account_billing', 'hardware_repair', 'thanks', 'other')
RULES = {
    'account_billing': r'\b(account|password|login|log in|apple id|refund|charged|billing|payment|subscription|hacked)\b',
    'hardware_repair': r'\b(cracked|broken screen|repair|replacement|swollen|smoke|burning|water damage)\b',
    'battery_power': r'\b(battery|drain\w*|charging|charge|power|dies|dead|percent)\b',
    'connectivity': r'\b(wifi|wi-fi|bluetooth|network|disconnect\w*|signal|cellular)\b',
    'apps_media': r'\b(apps?|music|whatsapp|notification\w*|keyboard|itunes|safari|playback)\b',
    'software_performance': r'\b(ios|update\w*|slow|freez\w*|crash\w*|lag\w*|restart\w*|load\w*)\b',
}
STOP = set('a an the i me my you your we our us it its is are was were to of on in for and or with this that at as be have has do does can could would please help apple applesupport'.split())
RISK = re.compile(r'\b(password|passcode|otp|verification code|hacked|stolen|fraud|refund|charged|payment|billing|lawyer|lawsuit|smoke|fire|swollen|burning|injur\w*|suicid\w*|kill|danger|data loss|lost data|erase|delete|reset)\b|__email__|__phone__|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{6,}\b', re.I)
INJECTION = re.compile(r'ignore.{0,30}(instruction|previous)|system prompt|developer message|reveal.{0,20}(secret|prompt)|jailbreak', re.I)
GENERIC = "Thanks for reaching out. A human support specialist should review this before we suggest a next step. Please do not share passwords or verification codes."

def clean(text):
    text = html.unescape(text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', '[redacted]', text, flags=re.I)
    text = re.sub(r'@[\w]+', '', text)
    text = re.sub(r'\b\d{6,}\b', '[redacted]', text)
    text = re.sub(r'\s+[\^/][A-Za-z]{1,4}\s*$', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def tokens(text):
    return [w for w in re.findall(r"[a-z]+(?:'[a-z]+)?", clean(text).lower()) if w not in STOP]

def normalized(text):
    return ' '.join(tokens(text))

def weak_intent(text):
    """Development-only heuristic labels. These are never human ground truth."""
    t = clean(text).lower()
    if re.fullmatch(r"(?:brilliant |great |ok |okay )?(?:thanks?|thank you|cheers)[!. ,😊🙂]*", t):
        return 'thanks'
    for label, pattern in RULES.items():
        if re.search(pattern, t):
            return label
    return 'other'

def features(text):
    words = tokens(text)
    return collections.Counter(words + [' '.join(p) for p in zip(words, words[1:])])

class Retriever:
    def __init__(self, rows):
        if not rows:
            raise ValueError('Training set is empty')
        self.rows = rows
        counts = [features(r['text']) for r in rows]
        df = collections.Counter(k for c in counts for k in c)
        self.idf = {k: math.log((1+len(rows))/(1+v))+1 for k,v in df.items()}
        self.vectors = [self.vector(c) for c in counts]
        self.majority = collections.Counter(self.label(r) for r in rows).most_common(1)[0][0]

    @staticmethod
    def label(row):
        return row.get('intent') or weak_intent(row['text'])

    def vector(self, counts):
        v = {k:(1+math.log(n))*self.idf[k] for k,n in counts.items() if k in self.idf}
        norm = math.sqrt(sum(x*x for x in v.values())) or 1
        return {k:x/norm for k,x in v.items()}

    def search(self, text, k=3):
        q = self.vector(features(text))
        scores = [(sum(v.get(w,0)*x for w,x in q.items()),i) for i,v in enumerate(self.vectors)]
        return [(s,self.rows[i]) for s,i in sorted(scores, key=lambda p:(-p[0],p[1]))[:k] if s>0]

class Agent:
    def __init__(self, rows, threshold=0.4):
        self.index = Retriever(rows)
        self.threshold = threshold

    def predict(self, text, baseline='agent', context=None, missing_context=False):
        if not isinstance(text,str) or not text.strip() or len(text)>10000:
            raise ValueError('Message must contain 1–10,000 characters')
        hits = self.index.search(text)
        evidence = [dict(tweet_id=r['id'], reply_id=r['reply_id'], text=r['text'],
                         reply=r['reference_reply'], similarity=round(s,6)) for s,r in hits]
        if baseline == 'majority':
            return dict(intent=self.index.majority, reply=GENERIC, decision='escalate',
                        reason='Trivial baseline: always escalate.', evidence=[], score=0.0)
        if baseline == 'nearest':
            return dict(intent=self.index.label(hits[0][1]) if hits else 'other',
                        reply=clean(hits[0][1]['reference_reply']) if hits else GENERIC,
                        decision='auto' if hits else 'escalate',
                        reason='Simple baseline: copy nearest historical reply without a safety gate.',
                        evidence=evidence[:1],score=round(hits[0][0],6) if hits else 0.0)
        votes = collections.Counter()
        for score,row in hits:
            votes[self.index.label(row)] += score
        ranked = votes.most_common()
        intent = ranked[0][0] if ranked else 'other'
        share = ranked[0][1]/sum(votes.values()) if ranked else 0
        score = hits[0][0] if hits else 0
        reason = None
        safety_text=' '.join([text]+[c['text'] for c in (context or [])])
        if INJECTION.search(safety_text): reason = 'Instruction-like input requires human review.'
        elif RISK.search(safety_text) or '[redacted]' in safety_text: reason = 'Account, financial, privacy, or physical-safety risk.'
        elif missing_context: reason = 'Conversation history is incomplete.'
        elif len(tokens(text))<3 and intent!='thanks': reason = 'Too little context to act safely.'
        elif score<self.threshold: reason = 'No sufficiently similar historical customer message.'
        elif share<0.7: reason = 'Retrieved examples disagree about the intent.'
        elif intent in ('account_billing','hardware_repair','other'): reason = 'Intent requires a specialist or more context.'
        # Only narrowly defined clarification/courtesy drafts may be auto-eligible.
        reply, selected = None, None
        if reason is None:
            for _, row in hits:
                if self.index.label(row)!=intent: continue
                ref = clean(row['reference_reply']).lower()
                if intent=='thanks' and weak_intent(text)=='thanks' and re.search(r'welcome|glad|happy to help',ref):
                    reply = "You're welcome! Let us know if you need anything else."
                elif re.search(r'which|what',ref) and re.search(r'ios|version',ref) and re.search(r'ios|iphone|ipad|update|phone',text,re.I):
                    reply = 'We can help look into this. Which iOS version are you using?'
                if reply:
                    selected = row['id']
                    break
            if not reply: reason = 'Historical replies do not support an approved low-risk clarification.'
        return dict(intent=intent,reply=reply or GENERIC,decision='escalate' if reason else 'auto',
                    reason=reason or 'Similar history supports a low-risk clarification; no account action or resolution is promised.',
                    evidence=evidence, used_evidence_ids=[selected] if selected else [],
                    score=round(score,6),vote_share=round(share,6),
                    mode='offline_shadow', policy_version='1')
