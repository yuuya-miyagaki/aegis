# iter54 レビュー — ドッグフード前 Critical バッチ修正

- 対象: 2026-07-02 徹底グリルで再現した Critical 4件＋Should 2件＋grill-code 追加 1件（C-1b）を1イテレーションで修正。
- 参照: plan/spec `docs/plans/2026-07-02-iter54-critical-batch-design.md`
- diff: `hooks/lib/safety.sh`（プローブ追加）/ `hooks/check-control-plane.sh`・`check-gate.sh`・`check-secrets.sh`・`check-destructive.sh`・`post-status-audit.sh`（判定 fold・noglob）/ `bin/setup.sh`（fail-closed install・argv・.bak）/ `scripts/run-test-strength-drill.py`（quotepath）/ `scripts/check_framework_contract.py`＋`templates/STATUS.template.md`（v1.15.0）/ 新規テスト4＋既存テスト2更新。

## 対照表（欠陥 → 実装 → 状態）

| # | 欠陥 | 実装ファイル | 状態 | 備考 |
|---|------|------------|------|------|
| C-1 | ケース非依存FS moat/gate/secrets バイパス | safety.sh / check-control-plane.sh / check-gate.sh / check-secrets.sh | 完了 | 条件付き fold（-ef プローブ）＋高速ゲート fold＋対称 strip |
| C-1b | STATUS.MD の gate tamper 監査スキップ | post-status-audit.sh | 完了 | grill-code 自己グリルで追加検出・同 probe で fold |
| C-2 | fail-open install（壊れ JSON / `'` パス） | bin/setup.sh | 完了 | JSON 冒頭検証＋全 heredoc argv 化＋parse_json_array rc 検査 |
| C-3 | --force 無バックアップ上書き | bin/setup.sh | 完了 | copy_file に diff-gated .bak（失敗時 abort） |
| C-4 | 日本語ファイル名 silent 消失 | run-test-strength-drill.py | 完了 | quotepath=off＋残存 quote は DrillError（fail-closed） |
| S-glob-1 | `rm -rf *` 警告漏れ | check-destructive.sh | 完了 | SAFE_TARGETS ループを set -f |
| S-glob-2 | `[id]`/`[h]ooks` 歪み | check-gate.sh | 完了 | normalize_target を set -f |

未着手タスクなし。構造リアーキ（FS解決/OS-lock 昇格・894行退役）は設計どおり別テーマへ切り出し（非スコープ）。

## moat 確認（fold の方向性）

- **deny 側のみ fold**: control-plane 一致・gate 保護 case・secrets credential 判定・audit filter は fold で deny を**広げる**方向のみ。allow 側カーブアウト（allowlist スクリプト・read-only starts・bare git stage）は case-sensitive のまま＝fold で allow が広がる退行なし。
- **弱体化不能**: fold は FS プローブ（safety.sh の `-ef`）駆動。`AEGIS_CASE_FOLD_FORCE=1` は strengthen-only（ON のみ・OFF 環境変数なし）。python へ渡す `AEGIS_CASE_INSENSITIVE` は呼び出し時に明示代入＝session env 汚染で無効化不能。
- **case-sensitive 非退行**: プローブ偽で現行挙動据置。既存 control/gate/secrets/destructive 回帰スイート全緑（deny/allow 決定不変）。
- **判定汚染なし**: setup.sh の変更は install 経路のみ・hook 判定ロジックは fold 追加以外に触れていない。

## findings（severity・出所・disposition）

| severity | finding | 出所 | disposition |
|---|---|---|---|
| 🔴 Critical | C-1b: post-status-audit.sh の `*STATUS.md` filter が case-sensitive＝macOS で `Edit(docs/STATUS.MD)` の gate/task tamper が監査ごとスキップ（C-1 と同一クラス・check-gate の docs/* allowlist が Edit を通す） | grill-code | **修正済**: probe 条件付き fold＋`\|*status.md`・TestStatusAuditCaseFold(4) |
| 🟡 Should | check-secrets.sh Check2（commit トリガ `git ... commit`）が raw $CMD 一致＝`GIT COMMIT` を取りこぼす | grill-code | **修正済**: CMD_LC 一致に変更（-C パス抽出は raw 維持）・test_uppercase_git_commit_with_staged_pem_denied 追加 |
| 🟢 Minor | post-status-audit の filter を無条件 `\|*status.md` 追加＝case-sensitive Linux で `build-status.md` 等を over-audit（fail-closed 方向だが設計の「据置」と非一致） | 盲検2次(review Minor-2) | **修正済**: fold は case-insensitive FS 時のみ分岐（`else` 節で byte-exact `*STATUS.md`）・over-audit 解消 |
| 🟢 Minor | 非ASCII homoglyph（U+212A→k 等）で bash 高速ゲートを回避 | 盲検2次(review Minor-1) | **受容・別テーマ**: FS 実解決リアーキ範囲。security レポート residual に明記 |
| 🟢 Minor | safety.sh `-ef` プローブの判別テストは case-insensitive FS で skipIf＝当該 macOS で mutation 実測できない | grill-code | **受容**: `-ef` は case-sensitive Linux で実在別 dir HOOKS/ を誤検知しないための判別＝その FS でのみ意味を持ち Linux で捕捉。macOS 側は FORCE 経路で fold 挙動を決定論テスト |
| 🟢 Minor | 大文字コマンド名（`CP`/`MV` が exec FS lookup で解決）は write-indicator regex 小文字前提のまま | 設計時 | **受容・別テーマ**: mention/redirect 層で大半 deny-eligible・security レポートに明記 |

## tests

- 新規4ファイル＋既存2更新。full suite は qa ゲートで実施（test 実行は qa の領分）。
- docs-only でない大型 diff の tests=unverified🟡 は review 段では ack 可（qa が権威実行）。

## verdict

🔴 Critical（C-1b）は grill-code で自己検出し実装内で解消。🟡 Should（commit fold）も解消。
盲検2次レビュー（approve_with_notes）の Minor-2（over-audit）は修正、Minor-1（非ASCII）は
別テーマで受容・明記。残る 🟢 は FS 依存の構造的制約／別テーマ。moat は deny-only fold・
strengthen-only override・判定汚染なしを確認。**approve_with_notes**（notes は上記のとおり解消/受容）。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "2次(reviewer・盲検)は diff/spec/plan の fresh context で独立実行し全7欠陥が閉じたことを確認（新規54+2skip・変更16テスト緑を自走）。bash 3.2.57 実機で空配列展開の安全も実証"
    - "2次が Minor-2（post-status-audit の Linux over-audit）を指摘→case-insensitive 時のみ fold する分岐に修正"
    - "2次が Minor-1（非ASCII homoglyph fast-gate バイパス）を指摘→FS 実解決リアーキ(別テーマ)範囲として受容・security 残余に明記"
```
