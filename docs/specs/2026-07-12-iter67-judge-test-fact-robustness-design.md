# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-07-12-iter67-judge-test-fact-robustness-brainstorm-record.md`
- 要件: なし（framework 内部改修・retro 合意 改善#1 が動機正本）

## 問題整理

- 背景: judge tier-1 test-fact（`scripts/build-judge-card.py::read_test_result`）は
  evidence-log（rotated `.1` → current の順に読み、新しい順に走査）の**最初の**
  test-runner マッチエントリで判定を打ち切る。そのエントリが observed かつ
  `marker_verified≠true`（以下 undecidable）だと、直下に fp 一致の trusted green
  （manual / observed+marker_verified=true）があっても `unverified` を返す。
  iter64/65/66 で3回、record green 後の生 pytest（`--collect-only` 件数確認・
  pipe 切詰め）1回で gate が 🟡 降格した（LEARNINGS conf9 line137）。
- 判断が必要な論点: (1) undecidable エントリに終端拒否権を残すか、
  (2) status=fail の undecidable の扱い、(3) fp 不一致の扱い、(4) スコープ
  （候補 #2/#3 の同梱可否）。
- 制約条件: silent-green の絶対禁止（証明されていない green を返さない）・
  C-2（marker 検証）/K-1（zero-run gate）/fp backstop の防御は一切緩めない・
  既存ピンテスト（単一エントリ5件）と衝突しない・reader（python）のみの変更で
  bash 側複製を生まない（parity 負債を増やさない）。

## 推奨アプローチ

- 採用方針: **trust-scan（信頼走査）** — 走査中、undecidable **かつ status=ok** の
  エントリは「green/red いずれも証明できない＝情報ゼロ」として**透明**（skip して
  走査継続）。判定は最新の decidable エントリ（src=manual、または observed で
  marker_verified=true）が下す。以下は不変:
  - undecidable かつ status=fail → 終端 `unverified`（何かが失敗した信号を保持）
  - decidable で fp ≠ 現在 worktree fingerprint → 終端 `unverified`（stale）
  - decidable エントリが1つも無い → `unverified`
- 採用理由: C-2 の信頼モデル（証明能力の無いエントリは判定を確定できない）を
  走査意味論まで一貫させる。green 側の安全性は fp（committed tree-hash）一致の
  trusted green の実在が担保し、red 側はむしろ厳格化（decidable red の後に
  no-run コマンドを走らせて red→🟡 に洗浄する経路が閉じる）。
- 検討した代替案と不採用理由: RECORD 参照（B=writer 側抑制は網羅性欠如＋責務違反、
  C=手続き hook は誤爆と複雑さ、A1=fail も透明は fail-visible 後退）。

## コンポーネント分解

- 分割方針: reader 1関数の走査ループ内の分岐順序変更のみ。新規コンポーネントなし。
- 各ユニットの責務:
  - `read_test_result`（変更）: 走査順を「(1) status ok/fail 以外 skip →
    (2) runner 非マッチ skip → (3) **undecidable-ok → skip（透明・新規）** →
    (4) fp 不一致 → 終端 unverified → (5) undecidable-fail → 終端 unverified →
    (6) green/red」に再構成。
  - `_evidence_entries` / `_test_runner_patterns` / `_tr_strip_patterns`（不変更）。
  - `hooks/lib/evidence.sh`・`patterns.sh`・`record-test-result.py`（不変更）。

## インターフェース定義

- 公開 API: `read_test_result(root: Path) -> str`（"green"/"red"/"unverified"）—
  シグネチャ・戻り値集合とも不変。呼び出し側（`collect_facts`）変更なし。
- 判定順序の契約（docstring に明文化）:
  1. decidable = `src=="manual"` または `marker_verified is True`
  2. undecidable-ok（observed・marker 未検証・status=ok）は走査透明
  3. 最新 decidable の fp が現在 fingerprint と不一致 → unverified
  4. 最新 decidable（fp 一致）の status で green/red
  5. undecidable-fail は従来どおり終端 unverified（透明化の対象外）

## データフロー / 構造

- 入力: evidence-log entries（新→旧）＋現在 worktree fingerprint（64-hex 必須）
- 処理: trust-scan（上記判定順序）
- 出力: "green" / "red" / "unverified"

判定マトリクス（走査中の各エントリ・上から先勝ち）:

| エントリ条件 | 挙動 | 現行との差 |
|---|---|---|
| status が ok/fail 以外 | skip（継続） | 不変 |
| cmd が runner 非マッチ（マスク後） | skip（継続） | 不変 |
| observed・marker≠true・status=ok | **skip（継続）** | **旧: 終端 unverified** |
| fp ≠ current（上記以外＝decidable と undecidable-fail） | 終端 unverified | 不変 |
| observed・marker≠true・status=fail（fp 一致） | 終端 unverified | 不変 |
| decidable・fp 一致・status=ok | green | 不変 |
| decidable・fp 一致・status=fail | red | 不変 |

注: undecidable-ok の透明化は fp 検査**より前**（情報ゼロのエントリは stale か
どうかも問わず透明）。undecidable-fail は fp 検査後（fp 不一致なら従来どおり
stale として終端・検査順を変えても結果同値）— 実装は「undecidable-ok → continue」を
fp 検査の直前に挿入する1分岐のみ。

## 依存関係

- 依存方向: `build-judge-card.py::read_test_result` → `_evidence_entries` /
  patterns（不変・循環なし）
- 外部依存: なし（新規依存ゼロ）

## エラーハンドリング

- 想定失敗: patterns 読込不能・fp 非 64-hex・log 破損行 — 全て既存の fail-closed
  （unverified）経路を維持。透明化は「走査継続」なので新たな例外経路を作らない。
- エラー伝播の方針: 既存どおり（JudgeError / build() の包括 🟡 化は不変）。

## テスト戦略

- 単体（`tests/test_test_runner_realness.py` に系列テストクラスを新設・
  既存 `_scratch_repo` ハーネス再利用・TDD RED-first）:
  1. [罠の再現＝RED-first 主役] manual green(fp=X) → observed undecidable-ok(fp=X)
     の順で書き、current=X → **green**（現行 unverified で RED）
  2. observed marker=true green(fp=X) → undecidable-ok(fp=X) → **green**
  3. [red 洗浄封鎖] decidable red(fp=X) → undecidable-ok(fp=X) → **red**
     （現行 unverified で RED＝厳格化の歯）
  4. [保守ピン] manual green(fp=X) → undecidable-**fail**(fp=X) → **unverified**
  5. [fp backstop] manual green(fp=STALE) → undecidable-ok(fp=X) → **unverified**
  6. [v1.6.0 スキーマ] marker_verified キー無し・status=ok の observed →（系列中で）
     透明＝単一なら unverified 維持
  7. [既存意味論保存] manual green(fp=X) → decidable red(fp=X) → **red**
- 結合: 既存単一エントリピン5件が無修正 green のまま（変更が系列のみに閉じる証明）。
- エッジケース: undecidable-ok のみで decidable ゼロ → unverified／
  rotated `.1` を跨ぐ系列でも透明化が機能。
- 手動確認: 実リポジトリで `record-test-result` green →
  `python3 -m pytest --collect-only -q | tail -1` → `/judge` プレビューで
  tests=green を実測（qa フェーズで hook 実発火込み）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-07-12-iter67-judge-test-fact-robustness-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->
