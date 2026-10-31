import json,re,unicodedata,collections
from pathlib import Path
from difflib import SequenceMatcher

def topic(title):
    t=unicodedata.normalize('NFKC',title).split('#')[0]
    t=re.sub(r'河南省(?:三届)?象棋冠军黄丹青(?:全套象棋课程)?[!！,，。:：\s]*','',t)
    t=re.sub(r'象棋布局一点通全套课程[!！,，。:：\s]*','',t)
    t=re.sub(r'如何(?:快速提升象棋水平|学习(?:象棋)?布局|学习布中残局|系统学习象棋)[^!！?？。]*[!！?？。]?','',t)
    t=re.split(r'河南省冠|真心教棋|少走弯路|带你上业九|不上业九',t)[0]
    return ''.join(c.lower() for c in t if c.isalnum())

def base(key):
    return key.replace('复盘分析','').replace('复盘','')

if __name__=='__main__':
    rows=sorted([r for p in Path('bilibili_data').glob('*.json') for r in json.loads(p.read_text())['data']['archives']],key=lambda r:(r['pubdate'],r['aid']),reverse=True)
    groups=collections.defaultdict(list)
    for r in rows:groups[topic(r['title'])].append(r)
    print('keys',len(groups),'empty',len(groups.get('',[])))
    for k,v in sorted(groups.items(),key=lambda kv:len(kv[1]),reverse=True)[:15]:
        print(k,len(v),[r['duration'] for r in v])
