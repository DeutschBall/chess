"""Regression checks for distinguishing unknown titles from concrete lessons."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LessonDedupTests(unittest.TestCase):
    def group(self, items):
        rows = [dict(aid=1, bvid='BV1fUx16tEMA', title='五六炮',
                     pubdate=1700000000 - 30 * 86400, duration=500,
                     upMid=1667150867)]
        for index, (title, duration) in enumerate(items, 2):
            rows.append(dict(aid=index, bvid=f'BVtest{index}', title=title,
                             pubdate=1700000000 + index * 60,
                             duration=duration, upMid=1667150867))
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            (stage / 'bilibili_data').mkdir()
            (stage / 'bilibili_data/1.json').write_text(
                json.dumps({'data': {'archives': rows}}), encoding='utf-8')
            (stage / 'chess/tools').mkdir(parents=True)
            shutil.copyfile(ROOT / 'tools/clean_titles.py',
                            stage / 'chess/tools/clean_titles.py')
            subprocess.run([sys.executable, '-B', str(
                ROOT / 'tools/catalog_pipeline/deduplicate_videos.py')],
                cwd=stage, check=True, capture_output=True, text=True)
            kept = json.loads((stage / 'selected_videos.json').read_text())
            audit = json.loads((stage / 'dedup_audit.json').read_text())
        return {r['bvid'] for r in kept} - {'BV1fUx16tEMA'}, audit

    def test_unknown_game_and_review_stay_separate(self):
        kept, audit = self.group([
            ('这盘棋你们能看懂吗？', 424),
            ('这盘棋你们能看懂吗复盘？', 1031),
        ])
        self.assertEqual(kept, {'BVtest2', 'BVtest3'})
        self.assertEqual(audit, [])

    def test_clear_unknown_duplicate_keeps_newest(self):
        kept, audit = self.group([
            ('这盘棋你们能看懂吗复盘？#象棋', 1031),
            ('这盘棋你们能看懂吗复盘？#教学', 1031),
        ])
        self.assertEqual(kept, {'BVtest3'})
        self.assertEqual([(r['removed_bvid'], r['kept_bvid']) for r in audit],
                         [('BVtest2', 'BVtest3')])

    def test_concrete_lesson_still_keeps_longest(self):
        kept, audit = self.group([
            ('骑河车对付中炮盘河马常用手段复盘', 1031),
            ('骑河车对付中炮盘河马常用手段实战', 424),
        ])
        self.assertEqual(kept, {'BVtest2'})
        self.assertEqual([(r['removed_bvid'], r['kept_bvid']) for r in audit],
                         [('BVtest3', 'BVtest2')])


if __name__ == '__main__':
    unittest.main()
