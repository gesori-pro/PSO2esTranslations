#!/usr/bin/env python3
"""Generate Korean candidates for exact JP patterns; never edit translation TXT.

Rules follow the EN SeraphyNotes, GaidenEffects, LinkSkills, PlugTokens and
ItemSets tools. Every candidate still requires Japanese/Korean review.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata

FILES = {
    'SeraphyRoom_SeraphyNote.txt': ('text',),
    'UI_Weaponoid_BondsEffect.txt': ('text',),
    'UI_Weaponoid_ReleaseAbility.txt': ('text',),
    'ChipExplain_BoostSkillExplain.txt': ('explainShort', 'explainLong'),
    'Awakening_Skill_Explain_Token.txt': ('token',),
    'Item_Stack_ItemBag.txt': ('explain',),
}
WEAPONS = dict(zip(
    '大剣 自在槍 長槍 双小剣 両剣 鋼拳 銃剣 長銃 大砲 双機銃 抜剣 強弓 魔装脚 飛翔剣 長杖 導具 短杖'.split(),
    ['소드','와이어드 랜스','파르티잔','트윈 대거','더블 세이버','너클','건슬래시','어설트 라이플','런처','트윈 머신 건','카타나','불릿 보우','제트 부츠','듀얼 블레이드','로드','탈리스','완드']))
ELEMENTS = dict(zip('炎 氷 雷 風 光 闇'.split(), '염 빙 뇌 풍 광 암'.split()))
SHORT = {
 '特定操作時ＣＰ回復':'특정 조작 시 CP 회복','特定操作時ＨＰ回復':'특정 조작 시 HP 회복',
 '発動率アップ':'발동률 증가','追加ダメージ付与':'추가 데미지 부여','チップパラメータ増加':'칩 능력치 증가',
 '発動ＣＰダウン':'발동 CP 감소','ＣＰ消費量軽減':'CP 소비량 감소','ダメージカット付与':'받는 데미지 감소 부여',
 'ダメージアップ':'데미지 증가','敵状態異常時ダメージアップ':'상태 이상인 적에게 주는 데미지 증가',
 '属性ダメージアップ':'속성 데미지 증가','効果時間延長':'효과 시간 연장','ＨＰ自動回復':'HP 자동 회복',
 'ダウン・のけぞり無効付与':'다운과 경직 무효 부여','属性値上限アップ':'속성치 상한 증가',
 '技・法終了時パラメータＵＰ':'필살기와 테크닉 종료 시 능력치 증가','プレイヤーパラメータ加算':'플레이어 능력치 가산',
 'プレイヤーパラメータ増加':'플레이어 능력치 증가','ラッシュアーツダメージアップ':'러시 아츠 데미지 증가',
 'シールド':'실드','状態異常回復':'상태 이상 회복','ダメージ軽減':'데미지 경감','戦闘不能回避':'전투 불능 회피',
 'ボーナス属性':'보너스 속성','効果発動変更':'효과 발동 조건 변경','チップコストダウン':'칩 코스트 감소',
 '消費ＣＰダウン':'CP 소비 감소','効果適用拡大':'효과 적용 대상 확대','パラメータアップ':'능력치 증가',
 '継続パラメータ回復':'능력치 지속 회복','特定状態異常付与':'특정 상태 이상 부여',
}
TOKENS = {**{j+'属性': k+'속성' for j,k in ELEMENTS.items()},
          '攻撃ヒット時':'공격 명중 시','ＪＡ成功時もしくはスライド操作時':'JA 성공 시 또는 슬라이드 조작 시'}
PHRASES = {
 'アビリティは\n「<%abi>」。':'어빌리티는\n「<%abi>」예요.',
 'アビリティは\n「<%abi>」。\n効果の内容は、チップの詳細情報で\n確認できますよ。':'어빌리티는\n「<%abi>」예요.\n효과의 내용은 칩 상세 정보에서\n확인할 수 있어요.',
 '解放には\nこのようなチップが必要です。':'해방하려면\n이런 칩이 필요해요.',
 '素材チップは\n日替わりクエストなどで\n手に入りますよ！\nぜひ解放してみてくださいね！':'소재 칩은\n일일 퀘스트 등에서\n얻을 수 있어요!\n꼭 해방해 보세요!',
 '素材チップは\n緊急クエストなどで\n手に入りますよ！\nぜひ解放してみてくださいね！':'소재 칩은\n긴급 퀘스트 등에서\n얻을 수 있어요!\n꼭 해방해 보세요!',
 'ぜひ解放してみてくださいね！':'꼭 해방해 보세요!',
 'チップが解放され\nアビリティ性能が高まりました！':'칩이 해방되어\n어빌리티 성능이 향상됐어요!',
 'ますます強力になった効果を\nぜひ試してみてくださいね！':'더욱 강력해진 효과를\n꼭 시험해 보세요!',
 'チップが解放されアビリティが\n「<%abi>」に\nなりました！\n性能もより強化されていますよ！':'칩이 해방되어 어빌리티가\n「<%abi>」로\n바뀌었어요!\n성능도 한층 강화됐답니다!',
 'チップが真・解放されアビリティが\n「<%abi>」に\nなりました！\n性能もさらに強化されていますよ！':'칩이 진 해방되어 어빌리티가\n「<%abi>」로\n바뀌었어요!\n성능도 더욱 강화됐답니다!',
 '必殺技を記録した\nチップのようです。':'필살기를 기록한\n칩인 것 같아요.',
 '法術を記録した\nチップのようです。':'테크닉을 기록한\n칩인 것 같아요.',
 'アイテムの効用が記録された\nチップのようです。':'아이템의 효능이 기록된\n칩인 것 같아요.',
 'どんな効果があるのか\nぜひ入手して確かめてみてください！':'어떤 효과가 있는지\n꼭 구해서 확인해 보세요!',
 'チップの新技術により生まれた\n「ウェポノイドチップ」の\nひとつのようです。':'칩의 신기술로 탄생한\n「웨포노이드 칩」 중\n하나인 것 같아요.',
 'こちらは\nチップの新技術によって生まれた\n新世代のチップ「ウェポノイドチップ」\nのひとつです。':'이것은\n칩의 신기술로 탄생한\n차세대 칩 「웨포노이드 칩」 중\n하나예요.',
 'さらなる解放には\nこのようなチップが必要です。':'추가로 해방하려면\n이런 칩이 필요해요.',
 'チップの解放（属性変換）は\n何度でも可能です。':'칩 해방(속성 변환)은\n몇 번이고 할 수 있어요.',
 '解放（属性変換）には\nこのようなチップが必要です。':'해방(속성 변환)하려면\n이런 칩이 필요해요.',
}
for jp,ko in {**WEAPONS, '<%wep>':'<%wep>'}.items():
    PHRASES['このチップは'+jp+'専用となります。\n入手された際は\n武器と合わせて装備してくださいね。'] = '이 칩은 '+ko+' 전용이에요.\n얻게 되면\n무기와 함께 장비해 주세요.'


def valid_candidate(source, text):
    if not text or '\u00b7' in text or source.count('\n') != text.count('\n') or source.count('\\n') != text.count('\\n'):
        return False
    tags = r'<[^>]*>|\$\([^)]*\)|\{[^}]*\}'
    if re.findall(tags,source) != re.findall(tags,text):
        return False
    numbers = lambda s: re.findall(r'\d+(?:\.\d+)?', unicodedata.normalize('NFKC',re.sub(tags,'',s)))
    return numbers(source) == numbers(text) and not re.search(r'[ぁ-ゟ゠-ヿ一-鿿]',re.sub(tags,'',text))


def effect(source):
    # Preserve actual line breaks and literal backslash-n independently.
    escaped = '\\n' in source
    s = source.replace('\\n','\n') if escaped else source
    patterns = [
      (r'このチップのアビリティの発動率が(?P<n>[０-９0-9]+)％上昇する。',lambda m:f"이 칩의 어빌리티 발동률이 {m['n']}％ 증가한다."),
      (r'このチップのアビリティの効果時間を(?P<n>[０-９0-9]+)秒延長する。',lambda m:f"이 칩의 어빌리티 효과 시간을 {m['n']}초 연장한다."),
      (r'このチップの(?P<t>コスト|アビリティの消費ＣＰ)が(?P<n>[０-９0-9]+)減少する。',lambda m:f"이 칩의 {'코스트가' if m['t']=='コスト' else '어빌리티 CP 소비량이'} {m['n']} 감소한다."),
      (r'このチップの効果の発動を攻撃ヒット時に変更する。',lambda m:'이 칩의 효과 발동 조건을 공격 명중 시로 변경한다.'),
      (r'このチップのアビリティ(?P<i>[①②]?)の効果の対象に\n(?P<e>[炎氷雷風光闇])属性を追加する。',lambda m:f"이 칩의 어빌리티{m['i']}의 효과 대상에\n{ELEMENTS[m['e']]}속성을 추가한다."),
      (r'装備したサポートチップの発動率が (?P<n>[０-９0-9]+)％ 上昇する。',lambda m:f"장비한 서포트 칩의 발동률이 {m['n']}％ 증가한다."),
      (r'装備したアクティブチップの消費ＣＰが (?P<n>[０-９0-9]+)％ 減少する。',lambda m:f"장비한 액티브 칩의 CP 소비량이 {m['n']}％ 감소한다."),
      (r'装備したチップの消費ＣＰを (?P<n>[０-９0-9]+)％ 軽減する。',lambda m:f"장비한 칩의 CP 소비량을 {m['n']}％ 줄인다."),
      (r'装備した必殺技・法術のダメージ量を (?P<n>[０-９0-9]+)％ 増加する。',lambda m:f"장비한 필살기와 테크닉의 데미지를 {m['n']}％ 증가시킨다."),
      (r'ラッシュアーツのダメージ量を (?P<n>[０-９0-9]+)％ 増加する。',lambda m:f"러시 아츠의 데미지를 {m['n']}％ 증가시킨다."),
      (r'装備した必殺技・法術がヒットした時に\n追加で (?P<n>[０-９0-9]+)％ のダメージを与える。',lambda m:f"장비한 필살기와 테크닉이 명중하면\n추가로 {m['n']}％의 데미지를 준다."),
      (r'装備した必殺技・法術発動中は\n受けるダメージを (?P<n>[０-９0-9]+)％ 軽減する。',lambda m:f"장비한 필살기와 테크닉을 발동하는 동안\n받는 데미지를 {m['n']}％ 줄인다."),
      (r'(?P<e>[炎氷雷風光闇])属性 が弱点の敵に対し\nその属性によるダメージを (?P<n>[０-９0-9]+)％ 増加する。',lambda m:f"{ELEMENTS[m['e']]}속성이 약점인 적에게\n해당 속성으로 주는 데미지를 {m['n']}％ 증가시킨다."),
      (r'(?P<e>[炎氷雷風光闇])属性 の上限値が (?P<n>[０-９0-9]+) 上昇する。',lambda m:f"{ELEMENTS[m['e']]}속성의 상한이 {m['n']} 증가한다."),
      (r'装備したチップの (?P<e>[炎氷雷風光闇])属性 を (?P<n>[０-９0-9]+)％ 増加する。',lambda m:f"장비한 칩의 {ELEMENTS[m['e']]}속성을 {m['n']}％ 증가시킨다."),
      (r'スライド操作時 に\n(?P<t>ＣＰ|ＨＰ)が (?P<n>[０-９0-9]+)(?P<p>％?) 回復する。\(発動確率： 小 \)',lambda m:f"슬라이드 조작 시\n{m['t'].translate(str.maketrans('ＣＰＨ','CPH'))}를 {m['n']}{m['p']} 회복한다.(발동 확률: 낮음)"),
    ]
    for pattern,render in patterns:
        m=re.fullmatch(pattern,s)
        if m:
            text=render(m)
            return text.replace('\n','\\n') if escaped else text
    return None


def item_names(directory):
    names=defaultdict(set)
    for path in Path(directory).glob('Item_*.txt'):
        for row in json.loads(path.read_text(encoding='utf-8-sig')):
            jp,ko=row.get('jp_text'),row.get('tr_text')
            if isinstance(jp,str) and isinstance(ko,str) and ko and not re.search('[ぁ-ゟ゠-ヿ一-鿿]',ko):
                names[jp].add(ko)
    return {j:next(iter(v)) for j,v in names.items() if len(v)==1}


def item_set(source,names):
    if not source.startswith('以下のアイテムを獲得する。\n'):
        return None
    lines=source.split('\n');output=['다음 아이템을 획득한다.']
    for line in lines[1:]:
        matches=list(re.finditer(r'「(?P<name>[^「」]+)」(?P<count>[０-９0-9]+個)?',line))
        if not matches or ''.join(m.group() for m in matches)!=line:
            return None
        result=''
        for m in matches:
            name=names.get(m['name'])
            if not name:return None
            result+='「'+name+'」'+(m['count'][:-1]+'개' if m['count'] else '')
        output.append(result)
    return '\n'.join(output)


def phrase_candidate(filename, field, source):
    data = json.loads(Path(__file__).with_name('KoreanTemplatePhrases.json').read_text(encoding='utf-8'))
    matches = set()
    for entry in data['templates']:
        if entry['file'] != filename or entry['field'] != field:
            continue
        slots = re.findall(r'⟦N([0-9]+)⟧', entry['source'])
        pattern = re.escape(entry['source'])
        for number in slots:
            pattern = pattern.replace(re.escape('⟦N'+number+'⟧'), '(?P<n'+number+'>[０-９0-9]+)')
        match = re.fullmatch(pattern, source)
        if match:
            text = entry['translation']
            for number in slots:
                text = text.replace('⟦N'+number+'⟧', match['n'+number])
            matches.add(text)
    return next(iter(matches)) if len(matches) == 1 else None


def generate_candidates(directory):
    directory=Path(directory);names=item_names(directory);candidates=[];unsupported=[];preserved=0
    for filename,fields in FILES.items():
        path=directory/filename
        if not path.exists():continue
        rows=json.loads(path.read_text(encoding='utf-8-sig'))
        for index,row in enumerate(rows):
            for field in fields:
                source=row.get('jp_'+field);current=row.get('tr_'+field)
                if not isinstance(source,str) or not source:continue
                if current!='':preserved+=1;continue
                if not re.search('[ぁ-ゟ゠-ヿ一-鿿]',source):continue
                if filename=='SeraphyRoom_SeraphyNote.txt':text=PHRASES.get(source)
                elif filename=='Item_Stack_ItemBag.txt':text=item_set(source,names)
                elif field=='token':text=TOKENS.get(source)
                else:text=SHORT.get(source) if field in ('explainShort','text') else None;text=text or effect(source)
                text = text or phrase_candidate(filename, 'jp_'+field, source)
                record={'file':filename,'source_index':index,'field':'jp_'+field,'source_jp':source,'native_key':row.get('__key')}
                if text and valid_candidate(source,text):candidates.append({**record,'translation':text})
                else:unsupported.append({**record,'reason':'확인된 전체 문장 패턴과 일치하지 않아 별도 번역 필요'})
    return {'candidates':candidates,'unsupported':unsupported,'existing_nonempty_preserved':preserved}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--translations',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=generate_candidates(args.translations)
    with args.out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(f"Candidates: {len(result['candidates'])}; unsupported: {len(result['unsupported'])}")


if __name__=='__main__':main()
