import csv,collections,shutil,re,html,json
from pathlib import Path
import sys
sys.path.insert(0, 'chess/tools')
from clean_titles import clean_title

root=Path('chess');out=root/'resources'/'huang-danqing';monthly=out/'monthly'
with Path('黄丹青_B站视频.csv').open(encoding='utf-8-sig',newline='') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==len({(r['日期'],r['标题']) for r in rows}), 'Run final date/title deduplication before export'
assert all(r['标题']!='未注明着法' for r in rows), 'Unclassified entries belong in pending list'
audit=json.loads(Path('dedup_audit.json').read_text())
pending=json.loads(Path('pending_videos.json').read_text())
source_count=json.loads(Path('validation.json').read_text())['original_count']
rule=f'主目录共 {len(rows):,} 条，同一天的精简标题不重复；另有 {len(pending):,} 条缺少着法信息的投稿列入待分类清单。从原始 {source_count:,} 条中累计合并 {len(audit):,} 条。'
snapshot_date=json.loads(Path('catalog_context.json').read_text())['snapshot_date']
meta=f'日期采用北京时间，数据获取日期：{snapshot_date}。标题仅保留着法、局面及战术手段，去掉头衔、广告、复盘标记和话题标签。发布日期及排序沿用所选视频。'
def esc(s):
    s=html.escape(s,quote=False);s=re.sub(r'([\\`*_{\}\[\]])',r'\\\1',s)
    return s.replace('|','&#124;').replace('\r\n','<br>').replace('\r','<br>').replace('\n','<br>')
def table(items):
    return ['| 链接 | 标题 | 日期 |','| --- | --- | --- |']+[f"| [观看视频]({r['链接']}) | {esc(r['标题'])} | {r['日期']} |" for r in items]
full=['# 黄丹青 B 站视频课题列表','','来源：https://space.bilibili.com/1667150867','',rule,'',meta,'','[归并规则与说明](METHOD.md) · [待分类投稿](pending.md)','']+table(rows)
(out/'黄丹青_B站视频.md').write_text('\n'.join(full)+'\n',encoding='utf-8')
for ext in ['csv','xlsx']:
    shutil.copyfile(f'黄丹青_B站视频.{ext}',out/f'黄丹青_B站视频.{ext}')
groups=collections.defaultdict(list)
for r in rows:groups[r['日期'][:7]].append(r)
for p in monthly.glob('*.md'):
    if p.stem not in groups:p.unlink()
for month,items in groups.items():
    lines=[f'# 黄丹青 B 站视频 · {month}','','[返回月份索引](../README.md) · [归并规则](../METHOD.md)','',f'共 {len(items)} 个课题条目。{meta}','']+table(items)
    (monthly/f'{month}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
lines=['# 黄丹青 B 站视频资料','','来源：[B 站用户页](https://space.bilibili.com/1667150867)，UID `1667150867`。','',rule,'',meta,'',
       '先精简标题，再按“日期＋精简后标题”去重，同组保留较长版本，时长相同则保留最新投稿。不同日期的相同棋题仍按日期分别列出。','',
       '[归并规则及示例](METHOD.md) · [整理过程与每日更新](PROCESS.md) · [逐条合并记录 CSV](dedup-audit.csv) · [待分类投稿](pending.md)','',
       '## 按月阅读','','各表均为“链接｜标题｜日期”三列。','','| 月份 | 课题条目数 |','| --- | ---: |']
lines += [f'| [{m}](monthly/{m}.md) | {len(groups[m])} |' for m in sorted(groups,reverse=True)]
lines += ['','## 完整文件','','- [Markdown 完整列表](黄丹青_B站视频.md)','- [CSV 表格](黄丹青_B站视频.csv)','- [Excel 表格](黄丹青_B站视频.xlsx)','', '完整文件较大，若 GitHub 无法预览，可点击文件页的 Raw / Download 下载。']
(out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(root/'README.md').write_text(f'# 信球中国象棋学习资料\n\n记录中国象棋学习资料、练习与复盘。\n\n## 视频资料\n\n- [黄丹青 B 站视频：{len(rows):,} 条（按日期及精简标题去重），按月索引及完整表格](resources/huang-danqing/README.md)\n- [待分类投稿：{len(pending):,} 条](resources/huang-danqing/pending.md)\n',encoding='utf-8')
from datetime import datetime
from zoneinfo import ZoneInfo
pending_rows=[[f"https://www.bilibili.com/video/{r['bvid']}/",datetime.fromtimestamp(r['pubdate'],ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')] for r in pending]
with (out/'pending.csv').open('w',encoding='utf-8-sig',newline='') as f:
    csv.writer(f).writerows([['链接','日期']]+pending_rows)
pending_lines=['# 待分类投稿','','[返回主目录](README.md)','',f'共 {len(pending):,} 条。原题没有提供可用于命名的具体着法或局面，无法仅凭“未注明着法”判定内容相同，因此保留全部链接，暂不放入棋题主目录。','', '[下载 CSV](pending.csv)','','| 链接 | 日期 |','| --- | --- |']
pending_lines += [f'| [观看视频]({url}) | {date} |' for url,date in pending_rows]
(out/'pending.md').write_text('\n'.join(pending_lines)+'\n',encoding='utf-8')
with (out/'dedup-audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f)
    w.writerow(['合并的链接','保留的链接','依据','合并的精简标题','保留的精简标题','合并视频时长（秒）','保留视频时长（秒）','初次匹配的链接（若随后归入课题长版）'])
    for r in audit:
        w.writerow([f"https://www.bilibili.com/video/{r['removed_bvid']}/",f"https://www.bilibili.com/video/{r['kept_bvid']}/",r['reason'],clean_title(r['removed_title']),clean_title(r['kept_title']),r['removed_duration'],r['kept_duration'],f"https://www.bilibili.com/video/{r['via_bvid']}/" if r.get('via_bvid') else ''])
print(f'Exported {len(rows)} entries, {len(audit)} audit records, {len(groups)} months')
