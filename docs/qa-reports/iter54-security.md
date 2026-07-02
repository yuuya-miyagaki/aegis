# iter54 セキュリティレビュー — ドッグフード前 Critical バッチ修正

- 対象: deny hook 群（check-control-plane / check-gate / check-secrets / check-destructive / post-status-audit）の判定ロジック変更、bin/setup.sh の install 経路、run-test-strength-drill.py の judge 入力。
- 参照: `docs/plans/2026-07-02-iter54-critical-batch-design.md`
- 前提: 変更は moat の**判定ロジック本体**に及ぶため security 必須。盲検2次監査を case-insensitive FS 上のスロウアウェイ複製で実施。

## 監査結論

**approve_with_notes。** moat を弱める新規経路なし。ケースフォールドは一貫して deny を
**広げる方向のみ**（allow 側カーブアウトは case-sensitive のまま＝allow は広がらない）。
新規失敗経路は全て fail-closed（setup abort / DrillError / audit block）。deny-narrowing 回帰なし。

## 確認事項（盲検2次の実測に基づく）

| 質問 | 結論 |
|------|------|
| fold 強制OFF / プローブ汚染 / fold 悪用で moat 弱体化できるか | 不可。`rm -rf HOOKS`・`cp evil HOOKS/lib/emit.sh`・`echo > SCRIPTS/x.sh`・`rm -rf HOOK?`・`CLAUDE.MD`(tee)・`rm -rf TEMPLATES` は全て deny 実測。プローブは case-insensitive FS で `-ef`=同一 inode＝fold-off にするには hooks/ 自体の除去が必要（=hook 機能停止） |
| AEGIS_CASE_FOLD_FORCE / AEGIS_CASE_INSENSITIVE は弱体化ベクタか | ならない。FORCE は `="1"` の strengthen-only（OFF スイッチなし・`=0`/`=off` でも probe が deny 継続）。AEGIS_CASE_INSENSITIVE は python 起動行でインライン明示付与＝session env 注入を上書き |
| 新規失敗経路は fail-closed か | はい。壊れ profile JSON→exit 1（install 0 件実測）／parse_json_array 全 caller rc 検査／.bak 失敗→abort／quoted 残存→DrillError／残る `\|\| true` は framework 所有の best-effort（ソース復元可・iter54 前から存在） |
| インジェクション（argv/heredoc・tr/grep） | なし。`'`＋スペース入り framework パスで install 完遂実測（旧 inline 形なら SyntaxError）。tr/grep は `printf '%s'` 済み文字列処理で eval 非含 |
| 差分のシークレット literal / 危険な一時ファイル | シークレット混入なし。`.bak.$(date +%s)` は非シークレット運用ファイルの同一 dir 複製（下記 residual） |
| deny-narrowing 回帰（$CMD→$CMD_LC / cp_targets fold 保存） | なし。パターンは全て小文字リテラル＝小文字化は「非マッチ→マッチ」拡大のみ。case-sensitive FS では `_fold`=恒等・`IGNORECASE`=0＝HEAD と同一挙動。fnmatch→fnmatchcase は case-sensitive で別物 HOOKS/ の false-deny を落とす正当性改善 |

## findings（severity・disposition）

| severity | finding | 出所 | disposition |
|---|---|---|---|
| 🟢 Low (N-1) | post-status-audit の fold プローブ基点が `CLAUDE_PROJECT_DIR` 由来 ROOT で兄弟 hook（SCRIPT_DIR 固定）と不一致。汚染で `docs/STATUS.MD` の tamper 監査スキップの可能性 | 盲検2次 | **修正済**: プローブ専用 `PROBE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"` を導入し env 非依存化（`post-status-audit.sh:44`）。※回帰ではない（iter54 前は STATUS.MD 元々スキップ）・CLAUDE_PROJECT_DIR 汚染時は STATUS_FILE 解決自体が既に破綻＝現行脅威モデル非到達 |
| 🟢 Low (N-2) | `.bak.$(date +%s)` の予測可能名（`setup.sh:190` 他） | 盲検2次 | **受容**: 対象は非シークレットの運用ファイルのみ・同一 dir 複製。symlink race は「対象 dir への既存書込権＋秒予測」を要し、その権限があればより直接的攻撃が可能。iter54 前から既存（copy_file_force 踏襲）。mktemp 化は Nice-to-have |
| 🟢 Low (residual) | 非ASCII homoglyph（U+212A KELVIN→`k` 等）で bash 高速ゲート（ASCII `tr`）を回避＝resolver 未起動でバイパス。resolver は到達すれば casefold で捕捉 | 盲検2次(review) | **受容・別テーマ**: 全 homoglyph/正規化の恒久修正は FS 実解決（realpath＋inode 比較）＝設計が明示スコープ外にした構造リアーキ。高速ゲートで非ASCII 全起動にすると日本語コマンドのホットパスに常時 python spawn コスト＝過大。次テーマ（OS-lock 昇格）で解消 |
| 🟢 Low (residual) | 大文字コマンド名（`CP`/`MV` が exec FS lookup で /bin/cp に解決）は write-indicator regex 小文字前提 | 設計時 | **受容・別テーマ**: mention/redirect 層で大半 deny-eligible。同上の FS 実解決リアーキ範囲 |

🔴 Critical・🟠 High・🟡 Medium なし。

## 実測エビデンス（盲検2次・スロウアウェイ複製）

- 大文字綴りの制御プレーン書込み6形態を全て deny 実測。
- FORCE=`0`/`off` 注入・AEGIS_CASE_INSENSITIVE=`0` 注入でも deny 継続（弱体化不能を実証）。
- 壊れ profile JSON→install 0 件／`'`＋スペースパス→install 完遂。
- credential: `key.PEM`/`ID_RSA`/`SERVICE-ACCOUNT.JSON`/`.ENV` deny・`.ENV.EXAMPLE` allow（対称 fold）。
- full suite 1232 passed / 3 skipped（回帰なし）・全 hook `bash -n` OK。

## verdict

**approve_with_notes。** N-1 は修正済（env 非依存プローブ）。N-2・非ASCII・大文字コマンド名は
低リスク／別テーマ（FS 実解決リアーキ）で受容し明記。moat は deny-only fold・
strengthen-only override・fail-closed・deny-narrowing なしを実測で確認。ドッグフード開始可。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "2次(security agent)は case-insensitive FS のスロウアウェイ複製で独立実測。fold は deny 拡大方向のみ・弱体化ベクタなしを6形態＋env注入で実証"
    - "2次が N-1（post-status-audit の CLAUDE_PROJECT_DIR 依存プローブ）を指摘→PROBE_ROOT で env 非依存化して修正"
    - "2次が N-2（.bak 予測可能名）と非ASCII homoglyph fast-gate バイパスを指摘→いずれも低リスク／別テーマ(FS実解決)で受容・明記"
```
