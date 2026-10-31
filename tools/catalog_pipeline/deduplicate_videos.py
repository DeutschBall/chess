"""Group likely repeated uploads using title wording and duration, with an audit trail."""
import csv,json,re,collections
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from difflib import SequenceMatcher
from dedup_analysis import topic

rows=sorted([r for p in Path('bilibili_data').glob('*.json') for r in json.loads(p.read_text())['data']['archives']],key=lambda r:(r['pubdate'],r['aid']),reverse=True)
manual={'BV1fUx16tEMA','BV1f2x16ZE72','BV1e4x66TEeZ','BV1Dex66aEfs'}
manual_keep=max((r for r in rows if r['bvid'] in manual),key=lambda r:(r['duration'],r['pubdate'],r['aid']))
kept=[]
by_duration=collections.defaultdict(list)
audit=[]
def numbers(key):return re.findall(r'[0-9一二三四五六七八九十百]+',key)
for r in rows:
    key=topic(r['title'])
    chosen=None;reason=None
    if r['bvid'] in manual and r['bvid']!=manual_keep['bvid']:
        chosen=manual_keep;reason='用户截图确认：含复盘版及短版，保留长版'
    if chosen is None:
        candidates=[v for duration in range(r['duration']-2,r['duration']+3) for v in by_duration[duration]]
        for v in candidates:
            other=topic(v['title'])
            if r['title']==v['title']:
                chosen=v;reason='完整标题相同且时长差≤2秒';break
            if len(key)>=8 and key==other:
                chosen=v;reason='去宣传文案后主题相同且时长差≤2秒';break
        if chosen is None and len(key)>=12:
            for v in candidates:
                other=topic(v['title'])
                if abs(r['duration']-v['duration'])>1 or len(other)<12:continue
                if ('复盘' in key)!=('复盘' in other) or numbers(key)!=numbers(other):continue
                if min(len(key),len(other))/max(len(key),len(other))<0.92:continue
                if SequenceMatcher(None,key,other,autojunk=False).ratio()>=0.94:
                    chosen=v;reason='主题文字相似度≥94%且时长差≤1秒、编号及复盘标记相同';break
    if chosen is not None:
        audit.append({'removed_bvid':r['bvid'],'kept_bvid':chosen['bvid'],'reason':reason,'removed_title':r['title'],'kept_title':chosen['title'],'removed_duration':r['duration'],'kept_duration':chosen['duration']})
    else:
        kept.append(r);by_duration[r['duration']].append(r)
def lesson(r):
    return re.sub(r'实战复盘|复盘分析|复盘|实战', '', topic(r['title']))
def day(r):
    return datetime.fromtimestamp(r['pubdate'],ZoneInfo('Asia/Shanghai')).date().toordinal()

# Same lesson on the same/adjacent day: game, review and title variants are one lesson.
# A group's total date span is capped at one day to prevent chains across weeks.
groups=[]
for r in sorted(kept,key=lambda r:(r['pubdate'],r['aid']),reverse=True):
    k=lesson(r);matched=None
    if len(k)>=8:
        for g in reversed(groups):
            if g['maxday']-day(r)>1:break
            other=g['key']
            if k==other or (min(len(k),len(other))>=12 and numbers(k)==numbers(other) and SequenceMatcher(None,k,other,autojunk=False).ratio()>=0.90):
                matched=g;break
    if matched is None:
        groups.append({'key':k,'maxday':day(r),'items':[r]})
    else:matched['items'].append(r)
redirect={}
final=[]
for g in groups:
    rep=max(g['items'],key=lambda r:(r['duration'],r['pubdate'],r['aid']))
    final.append(rep)
    for r in g['items']:
        if r['bvid']==rep['bvid']:continue
        redirect[r['bvid']]=rep
        audit.append({'removed_bvid':r['bvid'],'kept_bvid':rep['bvid'],'reason':'同日/相邻日同一具体着法课题：实战与复盘合并，保留长版','removed_title':r['title'],'kept_title':rep['title'],'removed_duration':r['duration'],'kept_duration':rep['duration']})
for a in audit:
    if a['kept_bvid'] in redirect:
        rep=redirect[a['kept_bvid']]
        a['via_bvid']=a['kept_bvid']
        a['reason']+='；初次匹配后归入同日/相邻日同课题长版'
        a.update(kept_bvid=rep['bvid'],kept_title=rep['title'],kept_duration=rep['duration'])
kept=sorted(final,key=lambda r:(r['pubdate'],r['aid']),reverse=True)
Path('lesson_groups.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding='utf-8')
Path('selected_videos.json').write_text(json.dumps(kept,ensure_ascii=False,indent=2),encoding='utf-8')
Path('dedup_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print('Original',len(rows),'retained',len(kept),'removed',len(audit))
print(collections.Counter(r['reason'] for r in audit))
fuzzy=[r for r in audit if '94%' in r['reason']]
for r in fuzzy[:20]:print(r['removed_duration'],topic(r['removed_title']),' => ',topic(r['kept_title']))
