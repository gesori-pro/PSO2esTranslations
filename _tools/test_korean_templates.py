import contextlib
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

import KoreanTemplates as templates


class KoreanTemplatesTest(unittest.TestCase):
    def test_whole_pattern_and_unknown_condition(self):
        source='このチップのアビリティの消費ＣＰが20減少する。'
        self.assertEqual(templates.effect(source),'이 칩의 어빌리티 CP 소비량이 20 감소한다.')
        self.assertIsNone(templates.effect(source+'ただし、ＨＰを消費する。'))

    def test_two_distinct_values_and_literal_newlines(self):
        source='装備したチップの 闇属性 を 17％\\nCP を 23％ 増加する。'
        actual=templates.phrase_candidate('ChipExplain_BoostSkillExplain.txt','jp_explainLong',source)
        self.assertEqual(actual,'장비한 칩의 암속성을 17％\\nCP를 23％ 증가시킨다.')
        self.assertTrue(templates.valid_candidate(source,actual))

    def test_weakness_condition_and_direction(self):
        source='炎属性 が弱点の敵に対し\\nその属性によるダメージを 37％ 増加する。'
        result=templates.effect(source)
        self.assertIn('약점인 적',result)
        self.assertIn('37％ 증가',result)
        self.assertTrue(templates.valid_candidate(source,result))

    def test_rejects_lost_numbers_tags_and_newlines(self):
        self.assertFalse(templates.valid_candidate('10秒<%x>\n','10초'))
        self.assertFalse(templates.valid_candidate('10秒','20초'))
        self.assertFalse(templates.valid_candidate('10秒','10초·'))

    def test_set_preserves_counts_and_line_layout(self):
        source='以下のアイテムを獲得する。\n「赤い服」２個\n「青い服」'
        actual=templates.item_set(source,{'赤い服':'빨간 옷','青い服':'파란 옷'})
        self.assertEqual(actual,'다음 아이템을 획득한다.\n「빨간 옷」２개\n「파란 옷」')
        self.assertTrue(templates.valid_candidate(source,actual))
        self.assertIsNone(templates.item_set(source,{'赤い服':'빨간 옷'}))
        self.assertIsNone(templates.item_set(source+'追加条件',{'赤い服':'빨간 옷','青い服':'파란 옷'}))

    def test_only_literal_empty_fields_are_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'UI_Weaponoid_ReleaseAbility.txt'
            jp='このチップのコストが8減少する。'
            rows=[{'jp_text':jp,'tr_text':value,'assign':str(i)} for i,value in enumerate(['',' ','English','기존 번역'])]
            path.write_text(json.dumps(rows,ensure_ascii=False));before=path.read_bytes()
            result=templates.generate_candidates(directory)
            self.assertEqual(len(result['candidates']),1)
            self.assertEqual(result['existing_nonempty_preserved'],3)
            self.assertEqual(path.read_bytes(),before)

    def test_unknown_sentence_remains_untranslated(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'UI_Weaponoid_ReleaseAbility.txt'
            rows=[{'jp_text':'このチップのコストが8減少する。ただし条件あり。','tr_text':''}]
            path.write_text(json.dumps(rows,ensure_ascii=False))
            result=templates.generate_candidates(directory)
            self.assertEqual(result['candidates'],[])
            self.assertEqual(len(result['unsupported']),1)

    def test_new_ticket_api_and_in_place_preservation(self):
        spec=importlib.util.spec_from_file_location('ticket_templates',Path(__file__).with_name('TicketDescriptions.py'))
        ticket=importlib.util.module_from_spec(spec);spec.loader.exec_module(ticket)
        self.assertEqual(ticket.parse_arguments(['-l','KO']).lang,'KO')
        ticket.LANG=1;ticket.TRANS_ALL=False;ticket.REDO_ALL=False
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'Item_AvatarWPN_Sword.txt'
            base={'assign':'101010201','jp_text':'＊テスト','tr_text':'＊테스트',
                  'jp_explain':'装備の見た目を変更する武器迷彩。\n<yellow>※対応：ソード／ワイヤードランス　ほか<c>', 'tr_explain':''}
            rows=[base,dict(base,assign='101010202',tr_explain='기존 번역')]
            path.write_text(json.dumps(rows,ensure_ascii=False));ticket.json_loc=directory
            with contextlib.redirect_stdout(io.StringIO()):ticket.main_update('AvatarWPN_Sword')
            result=json.loads(path.read_text())
            self.assertIn('※지원: 소드',result[0]['tr_explain'])
            self.assertEqual(result[1],rows[1])
            self.assertEqual({k:v for k,v in result[0].items() if k!='tr_explain'}, {k:v for k,v in rows[0].items() if k!='tr_explain'})


if __name__=='__main__':unittest.main()
