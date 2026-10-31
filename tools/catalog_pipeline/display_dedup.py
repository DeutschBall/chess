import json,collections
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,'chess/tools')
from clean_titles import clean_title

source=Path('before_display_dedup.json')
if not source.exists():
    source.write_text(Path('selected_videos.json').read_text(),encoding='utf-8')
rows=json.loads(source.read_text())
groups=collections.defaultdict(list);pending=[]
for r in rows:
    title=clean_title(r['title'])
    if title=='未注明着法':
        pending.append(r);continue
    date=datetime.fromtimestamp(r['pubdate'],ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')
    groups[(date,title)].append(r)
kept=[];redirect={};new_audit=[]
for key,items in groups.items():
    rep=max(items,key=lambda r:(r['duration'],r['pubdate'],r['aid']))
    kept.append(rep)
    for r in items:
        if r['bvid']==rep['bvid']:continue
        redirect[r['bvid']]=rep
        new_audit.append({'removed_bvid':r['bvid'],'kept_bvid':rep['bvid'],'reason':'同日精简标题相同，保留较长版本','removed_title':r['title'],'kept_title':rep['title'],'removed_duration':r['duration'],'kept_duration':rep['duration']})
audit_path=Path('before_display_audit.json')
if not audit_path.exists():audit_path.write_text(Path('dedup_audit.json').read_text(),encoding='utf-8')
audit=json.loads(audit_path.read_text())
for a in audit:
    if a['kept_bvid'] in redirect:
        rep=redirect[a['kept_bvid']]
        a.setdefault('via_bvid',a['kept_bvid'])
        a['reason']+='；再按同日精简标题归并'
        a.update(kept_bvid=rep['bvid'],kept_title=rep['title'],kept_duration=rep['duration'])
audit+=new_audit
kept.sort(key=lambda r:(r['pubdate'],r['aid']),reverse=True)
for path,data in [('selected_videos.json',kept),('pending_videos.json',pending),('dedup_audit.json',audit)]:
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('catalog',len(kept),'pending',len(pending),'new merged',len(new_audit),'total merged',len(audit))
