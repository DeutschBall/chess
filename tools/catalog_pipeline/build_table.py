import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
import sys
sys.path.insert(0, 'chess/tools')
from clean_titles import clean_title

TZ = ZoneInfo('Asia/Shanghai')
rows = []
totals = set()
for path in sorted(Path("bilibili_data").glob("*.json"), key=lambda p:int(p.stem)):
    pn = int(path.stem)
    data = json.loads(Path(f'bilibili_data/{pn}.json').read_text())
    assert data['code'] == 0, pn
    page = data['data']['page']
    assert page['num'] == pn and page['size'] == 50, page
    totals.add(page['total'])
    items = data['data']['archives']
    assert len(items) == min(50, page["total"]-(pn-1)*50), (pn, len(items))
    assert all(x['upMid'] == 1667150867 for x in items), pn
    rows.extend(items)
assert totals == {len(rows)}, totals
assert len(rows) == len({x['bvid'] for x in rows}) == len(rows)
assert len({x['aid'] for x in rows}) == len(rows)
assert all(x['title'] and x['pubdate'] and x['bvid'].startswith('BV') for x in rows)
rows.sort(key=lambda x: (x['pubdate'], x['aid']), reverse=True)
original_count = len(rows)
rows = json.loads(Path('selected_videos.json').read_text())
seen_titles = {row['title'] for row in rows}
table = [['链接', '标题', '日期']] + [
    ['https://www.bilibili.com/video/' + x['bvid'] + '/', clean_title(x['title']), datetime.fromtimestamp(x['pubdate'], TZ).strftime('%Y-%m-%d')]
    for x in rows
]
with Path('黄丹青_B站视频.csv').open('w', encoding='utf-8-sig', newline='') as f:
    csv.writer(f).writerows(table)

# Portable XLSX using the standard OOXML package, with clickable video links.
ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
rel_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
package_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
sheet_rows = []
for ri, row in enumerate(table, 1):
    cells = []
    for ci, val in zip('ABC', row):
        assert not any(ord(c) < 32 and c not in '\t\n\r' for c in val)
        style = ' s="1"' if ci == 'A' and ri > 1 else ''
        cells.append(f'<c r="{ci}{ri}" t="inlineStr"{style}><is><t xml:space="preserve">{escape(val)}</t></is></c>')
    sheet_rows.append(f'<row r="{ri}">' + ''.join(cells) + '</row>')
links = ''.join(f'<hyperlink ref="A{i}" r:id="rId{i}"/>' for i in range(2, len(table)+1))
rels = ''.join(f'<Relationship Id="rId{i}" Type="{rel_ns}/hyperlink" Target="{escape(table[i-1][0])}" TargetMode="External"/>' for i in range(2, len(table)+1))
sheet = f'<worksheet xmlns="{ns}" xmlns:r="{rel_ns}"><dimension ref="A1:C{len(table)}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="49" customWidth="1"/><col min="2" max="2" width="110" customWidth="1"/><col min="3" max="3" width="14" customWidth="1"/></cols><sheetData>{"".join(sheet_rows)}</sheetData><autoFilter ref="A1:C{len(table)}"/><hyperlinks>{links}</hyperlinks></worksheet>'
files = {
    '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
    '_rels/.rels': f'<Relationships xmlns="{package_ns}"><Relationship Id="rId1" Type="{rel_ns}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
    'xl/workbook.xml': f'<workbook xmlns="{ns}" xmlns:r="{rel_ns}"><sheets><sheet name="视频列表" sheetId="1" r:id="rId1"/></sheets></workbook>',
    'xl/_rels/workbook.xml.rels': f'<Relationships xmlns="{package_ns}"><Relationship Id="rId1" Type="{rel_ns}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{rel_ns}/styles" Target="styles.xml"/></Relationships>',
    'xl/styles.xml': f'<styleSheet xmlns="{ns}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><sz val="11"/><color rgb="FF0563C1"/><name val="Calibri"/><u/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf fontId="0" fillId="0" borderId="0" xfId="0"/><xf fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
    'xl/worksheets/sheet1.xml': sheet,
    'xl/worksheets/_rels/sheet1.xml.rels': f'<Relationships xmlns="{package_ns}">{rels}</Relationships>',
}
with ZipFile('黄丹青_B站视频.xlsx', 'w', ZIP_DEFLATED) as z:
    for name, xml in files.items():
        z.writestr(name, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + xml)

report = {'account_mid': 1667150867, 'source': 'https://space.bilibili.com/1667150867', 'endpoint': 'https://api.bilibili.com/x/series/recArchivesByKeywords', 'checked_at': datetime.now(TZ).isoformat(), 'count': len(rows), 'unique_bvid': len({x['bvid'] for x in rows}), 'pages': len(list(Path('bilibili_data').glob('*.json'))), 'date_timezone': 'Asia/Shanghai', 'earliest': table[-1][2], 'latest': table[1][2]}
Path('validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
report.update(original_count=original_count, removed=original_count-len(rows), unique_titles=len(seen_titles), deduplication='date plus cleaned title; longest then newest', pending=len(json.loads(Path('pending_videos.json').read_text())))
Path('validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
