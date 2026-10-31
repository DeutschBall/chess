"""Refresh public uploads, rebuild in isolation, then publish validated local files."""
import argparse, gzip, json, math, shutil, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile
from zoneinfo import ZoneInfo
import csv

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data/huang-danqing.json.gz'
STATE=ROOT/'data/huang-danqing-state.json'
FIELDS=('aid','bvid','title','pubdate','duration','upMid')
TZ=ZoneInfo('Asia/Shanghai')

def request_page(pn):
    url=f'https://api.bilibili.com/x/series/recArchivesByKeywords?mid=1667150867&keywords=&pn={pn}&ps=50'
    error=''
    for attempt in range(5):
        try:
            req=Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://space.bilibili.com/1667150867/'})
            with urlopen(req,timeout=25) as response:data=json.load(response)
            if data.get('code')!=0:raise RuntimeError(f"API code {data.get('code')}")
            page=data['data'];items=page['archives']
            if page['page']['num']!=pn or any(r['upMid']!=1667150867 for r in items):raise RuntimeError('Invalid page/owner')
            if not items and pn<=math.ceil(page['page']['total']/50):raise RuntimeError('Unexpected empty page')
            return page
        except Exception as exc:
            error=str(exc)
            if attempt<4:time.sleep(attempt+1)
    raise RuntimeError(f'Cannot fetch page {pn}: {error}; existing catalog preserved')

def same_file(src,dst):
    if not dst.exists():return False
    if src.suffix=='.xlsx':
        with ZipFile(src) as a, ZipFile(dst) as b:
            return set(a.namelist())==set(b.namelist()) and all(a.read(n)==b.read(n) for n in a.namelist())
    return src.read_bytes()==dst.read_bytes()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Rebuild using repository cache without network')
    args=parser.parse_args()
    rows=json.loads(gzip.decompress(CACHE.read_bytes()))
    before={r['bvid']:r for r in rows};merged=dict(before)
    state=json.loads(STATE.read_text()) if STATE.exists() else {'snapshot_date':'2026-11-01'}
    if not args.offline:
        cutoff=max(r['pubdate'] for r in rows)-7*86400
        pn=1
        while True:
            page=request_page(pn);items=page['archives']
            for r in items:merged[r['bvid']]={k:r[k] for k in FIELDS}
            known=bool(items) and all(r['bvid'] in before for r in items)
            if (known and min(r['pubdate'] for r in items)<=cutoff) or pn>=math.ceil(page['page']['total']/50):break
            pn+=1
        if merged==before:
            print(json.dumps({'changed':False,'new_videos':0,'message':'No new or changed uploads'},ensure_ascii=False));return
        state['snapshot_date']=datetime.now(TZ).strftime('%Y-%m-%d')
    rows=sorted(merged.values(),key=lambda r:(r['pubdate'],r['aid']),reverse=True)
    with tempfile.TemporaryDirectory(prefix='huang-danqing-') as temp:
        stage=Path(temp);pages=stage/'bilibili_data';pages.mkdir()
        for offset in range(0,len(rows),50):
            data={'code':0,'data':{'page':{'num':offset//50+1,'size':50,'total':len(rows)},'archives':rows[offset:offset+50]}}
            (pages/f'{offset//50+1}.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        clone=stage/'chess';clone.mkdir()
        shutil.copytree(ROOT/'resources',clone/'resources')
        shutil.copytree(ROOT/'tools',clone/'tools',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(ROOT/'README.md',clone/'README.md')
        (stage/'catalog_context.json').write_text(json.dumps(state))
        pipeline=ROOT/'tools/catalog_pipeline'
        for script in ['deduplicate_videos.py','display_dedup.py','build_table.py','export_catalog.py']:
            result=subprocess.run([sys.executable,'-B',str(pipeline/script)],cwd=stage,capture_output=True,text=True)
            if result.returncode:raise RuntimeError(script+' failed: '+result.stderr[-3000:])
        selected=json.loads((stage/'selected_videos.json').read_text());pending=json.loads((stage/'pending_videos.json').read_text());audit=json.loads((stage/'dedup_audit.json').read_text())
        kept={r['bvid'] for r in selected+pending};removed={r['removed_bvid'] for r in audit}
        assert len(kept)==len(selected)+len(pending) and len(removed)==len(audit)
        assert not kept&removed and kept|removed==set(merged)
        assert all(r['kept_bvid'] in kept for r in audit)
        catalog=clone/'resources/huang-danqing'
        with (catalog/'黄丹青_B站视频.csv').open(encoding='utf-8-sig',newline='') as f:table=list(csv.DictReader(f))
        assert len(table)==len(selected)==len({(r['日期'],r['标题']) for r in table})
        assert all(r['标题']!='未注明着法' and '#' not in r['标题'] for r in table)
        # No destination changes until all pipeline stages and invariants have passed.
        changed=[]
        for src in [clone/'README.md',*catalog.rglob('*')]:
            if not src.is_file():continue
            dst=ROOT/src.relative_to(clone)
            if not same_file(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);changed.append(str(dst.relative_to(ROOT)))
        for old in (ROOT/'resources/huang-danqing/monthly').glob('*.md'):
            if not (catalog/'monthly'/old.name).exists():old.unlink();changed.append(str(old.relative_to(ROOT)))
        payload=gzip.compress(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode(),mtime=0)
        if CACHE.read_bytes()!=payload:CACHE.write_bytes(payload)
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'changed_files':changed,'new_videos':len(set(merged)-set(before)),'catalog':len(selected),'pending':len(pending),'merged':len(audit)},ensure_ascii=False))

if __name__=='__main__':main()
