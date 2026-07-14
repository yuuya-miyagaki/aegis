# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-14（iteration 69）

## テーマ

- B1 test-strength drill 強化: NO_RUN 拒否＋mutant parse 検証＋コメントラン floor 除外＋`since` baseline モード

## コンテキスト

- 現在の状況: docs/full-review-2026-07-06-six-dimensions-evolution.md §4 Phase 1 スイープの 5 番目（1-1✅iter64／1-2✅iter67／1-3✅iter68／1-4✅iter65）。残りは 1-5（本反復）と 1-6。
- きっかけ:
  - **R4（🔴 verified）**: `parse_spec` は test_command を非空文字列としか検証しない。`pytest --collect-only -q`＋構文破壊 mutant で**1件もテストを実行せず DRILL PASS が成立**（baseline=収集成功 green、mutant=収集エラーで全数 caught）。evidence 側の `AEGIS_TEST_NO_RUN_FLAG_REGEX`（patterns.sh:179）を drill 側が未消費という非対称。
  - **R4 併発**: mutant の意味的品質が未強制 — 構文破壊 mutant だけで coverage floor を充足でき「assert の強さ」を証明しない。
  - **罠 l（R6・設計で根絶可）**: 純コメント/docstring の孤立ハンクに behavior-catching mutant を置けず floor 不成立 → skip 強制（LEARNINGS:136・iter64 実痛=fingerprint.sh header／setup.sh 帰属コメント／test docstring）。
  - **罠 f（R6・軽減可）**: per-task コミット運用では qa 承認時の `git diff HEAD` が空＝追加(+)行ゼロで drill 不成立（LEARNINGS:76 恒久対応候補「iteration baseline ref への diff モード」既起票）。

## 検討したアプローチ

### アプローチ A: フルセット4点・drill 単体完結（採用）

- 概要: `scripts/run-test-strength-drill.py` に (1) NO_RUN 拒否＝patterns.sh を bash-source し **grep -qE をそのまま subprocess 実行**（evidence.sh と完全同一意味論）、(2) mutant 構文検証＝適用前 pre-pass で `.py`→py_compile／`.sh`→`bash -n`（temp file・構文破壊 mutant は spec エラー化）、(3) coverage floor から「コメント/空行/py docstring のみの連続ラン」を除外（言語別・AST docstring 込み）、(4) `.drill` spec の optional key `since` で diff baseline ref を指定（ancestor 検証＋report `since:` 行で透明化）。
- 利点: R4 と罠 l/f を一括根治。全変更が drill runner＋テストに閉じ、承認時経路（check_status.py::run_qa_drill）は無改修。single-source（patterns.sh）を意味論ドリフトゼロで消費。
- 欠点: 4 サブ項目で diff がやや大きい（ただし全て同一ファイル・独立サブ機能）。

### アプローチ B: R4 のみ（NO_RUN＋構文検証）に絞り、罠 l/f は次反復

- 概要: フォージ穴（R4）だけ塞ぎ、floor 除外と since は先送り。
- 利点: 最小 diff。
- 欠点: 1-5 のスコープに罠 l/f が明記されており（LEARNINGS:76/136 起票済）、スイープの目的＝罠根絶に反する。floor 除外・since は同じ関数群を触るため分割コスト＞一括コスト。

### アプローチ C: NO_RUN regex を Python re へ翻訳して消費

- 概要: build-judge-card.py の loader 前例に倣い regex を `re.compile` で消費。
- 利点: subprocess 不要。
- 欠点: `AEGIS_TEST_NO_RUN_FLAG_REGEX` は `[[:space:]]` POSIX クラスを含み、Python re では文字集合として誤解釈され **silent mis-match**（parity contract の対象外）。翻訳層 or parity 拡張のコストに対し、grep 直呼びは完全同一エンジン＋同一 regex で安価。

## 決定

- 採用アプローチ: A（フルセット・drill 単体完結）
- 採用理由: Phase 1 の 1-5 スコープ全項目を1反復で閉じ、変更を drill runner＋テストに閉じ込められる。NO_RUN は grep 直呼びで意味論ドリフトゼロ。`since` は spec key 化により承認時固定 argv 経路（run_qa_drill）を無改修で通せる（CLI flag では承認時に届かない）。
- 不採用理由: B=起票済みの罠を先送りしスイープ目的に反する／C=POSIX クラスの意味差で silent drift リスク。

## 主要設計判断（要点）

1. **`since` は CLI flag でなく `.drill` spec の optional key**: 承認時は `run_qa_drill` が固定 argv で runner を呼ぶため CLI では不達。spec key なら preview と承認が自動一致し、baseline ref が監査可能な証拠ファイルに残る。
2. **NO_RUN 判定は bash+grep subprocess**: `source patterns.sh; printf %s "$cmd" | grep -qE "$REGEX"`。regex 未定義・patterns.sh 不在・grep エラーは fail-closed（DrillError）。
3. **構文検証の precondition**: 元ファイルが parse 不能なら当該 mutant の検証は skip（帰責不能）。テストが import する .py が parse 不能なら baseline red で別途 block される。未知拡張子は検証対象外（py/sh が framework の実体）。
4. **floor 除外は緩和方向のみで gaming 面積を増やさない**: コメント行に mutant を置いても survived→FAIL になるため、除外は「不可能要求の削除」。混在ラン（コード＋コメント）は floor 維持。py docstring は AST（Module/ClassDef/FunctionDef body[0] の Constant str）で行範囲特定、parse 失敗時は除外なし（厳格側に劣化＝安全）。
5. **`since` の検証と透明化**: `rev-parse --verify <ref>^{commit}` ＋ `merge-base --is-ancestor <ref> HEAD` 必須（非 ancestor は DrillError）。report 機械ブロックに `since:` 行を常時出力（judge は `verdict:` のみ regex 抽出のため追加行は安全）。ref 選択自体は利用者委ね＝R6 の「軽減可」分類どおり、透明化＋レビュー人手が緩和策。

## スコープ境界

- やること: `scripts/run-test-strength-drill.py`（4 サブ機能）＋`tests/test_test_strength_drill.py`（新規＋既存ピン更新）＋`.claude/skills/qa-verification/SKILL.md`（since key・NO_RUN・floor 除外の利用者向け記述）。
- やらないこと: SF-011/012/013 の相乗り（テーマ純度・iter68 前例）／patterns.sh の regex 変更（single source 不変）／check_status.py・update-gate.sh の変更（承認時経路は無改修）／rollover 時の baseline ref 自動記録（since の値決めは利用者＋レビュー、機構化は将来候補）／py 以外の block comment（`/* */`）検出。

## 未解決事項

- なし（`since` の ref 選択ガバナンスは「軽減可」として透明化で受容 — 全体レビュー R6 の分類どおり）

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-14-iter69-drill-hardening-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->
