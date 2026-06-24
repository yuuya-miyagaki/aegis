# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-25-iter44-root-external-plan-gate-brainstorm-record.md`
- 要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（C5）

## 問題整理

- 背景: `check-gate.sh`（PreToolUse for Edit/Write）は plan-gate 未承認時に code 編集を deny する。
  だが ROOT 外の絶対パス（auto-memory `~/.claude/.../memory/*.md` 等）が docs allowlist にも
  control-file 判定にもマッチせず、plan-gate 判定に落ちて false-positive deny される。
- 判断が必要な論点: plan-gate を「project 外」に適用しないようにしつつ、
  **保護対象（project code・control file）の bypass を絶対に開かない**こと。
- 制約条件: lexical 判定のみ（FS 非アクセス＝既存方針）。相対パスは cwd 不明で分類不能。

## 推奨アプローチ

- 採用方針: control-file 判定の後・mode/plan-gate 判定の前に、
  ROOT 外の絶対パスを `emit_allow` で short-circuit する。
- 採用理由: 緩和対象が「project 外の非 control 絶対パス」に限定され、保護対象は不変。最小差分。
- 検討した代替案と不採用理由: B（plan-gate 行に条件埋込）=可読性低下／C（上流で external 一般化）=
  スコープ過大・control-file 順序破壊リスク。

## コンポーネント分解

- 分割方針: `check-gate.sh` 単一フックに 1 箇所追加。新 lib なし・新 helper なし。
- 各ユニットの責務:
  - ユニット A（既存）: docs allowlist → templates → control-file 判定（**変更なし・前段で完結**）
  - ユニット B（新規 short-circuit）: `$ROOT/*`・`$ROOT_REAL/*` 以外の絶対パスを allow
  - ユニット C（既存）: mode（Client deny）→ plan-gate（pending deny）（**変更なし**）

## インターフェース定義

- 公開 API: なし（フック内部ロジックのみ）。stdin=PreToolUse JSON、stdout=`emit_allow`/`emit_deny` JSON。
- 挿入位置: `is_control_file` ブロック（現 line 130-140）の直後、`MODE=` 取得（現 line 142）の直前。

## データフロー / 構造

- 入力: 正規化済み `TARGET_FILE`（`normalize_target` 適用後）。
- 処理（追加分）:
  ```bash
  case "$TARGET_FILE" in
    "$ROOT"/*|"$ROOT_REAL"/*) ;;   # ROOT 内 → 既存 gate へ通す
    /*) emit_allow; exit 0 ;;       # 絶対 & ROOT 外 → project 外 → allow
  esac
  ```
- 出力: ROOT 外絶対 → allow。ROOT 内絶対 / 相対 → 既存判定（mode・plan-gate）へ。
- **挿入位置（grill-plan #1・意識的決定）**: `MODE=`（line 142）・Client-mode deny（line 147）・
  plan-gate（line 153）の**すべての前**。plan-gate も Client-mode deny も「project の code を編集させない」
  ゲートであり、ROOT 外絶対パスは定義上 project の code ではない → 両ゲットの適用対象外とするのが正しい
  （auto-memory はモード非依存で動くべき）。Edit/Write の file_path は常に絶対なので相対分岐は防御的（dead）。

### 判定表

| TARGET_FILE 種別 | 例 | 追加 case の結果 | 最終 |
|---|---|---|---|
| 絶対・ROOT 外 | `/Users/x/.claude/.../memory/M.md` | `/*` arm → allow | **allow（修正）** |
| 絶対・ROOT 内 | `$ROOT/src/main.py` | 第1 arm → 通過 | plan-gate（pending→deny） |
| 相対 | `src/main.py` | 非マッチ → 通過 | plan-gate（pending→deny） |
| 相対 ROOT 外 | `../../ext/f` | 非マッチ → 通過 | plan-gate（保守的 deny 維持） |
| docs | `$ROOT/docs/x.md` | 前段 allowlist で既に allow | allow（不変） |
| control file | `$ROOT/hooks/x.sh` | 前段 control 判定で deny/allow | 不変 |

## 依存関係

- 依存方向: なし新規。既存 `$ROOT`/`$ROOT_REAL`（line 24/52 で算出済）を再利用。
- 外部依存: なし。

## エラーハンドリング

- 想定失敗: `$ROOT_REAL` 未算出 → 既に line 52 で算出済（フック先頭で fail-closed safety lib 経由）。
- 対応: short-circuit は allow のみ。判定不能（相対）は従来の保守的 deny にフォールバック。
- エラー伝播: 変更なし。emit_allow/emit_deny の既存スキーマ。

## セキュリティ分析

- **bypass 非発生の保証**: templates/control-file/docs 判定は short-circuit より前段で完結。
  project code（ROOT 内）も gate 維持。挙動が変わるのは「ROOT 外の非 control 絶対パス」のみ。
- **正直な残留**: グローバル `~/.claude/settings.json` も plan pending 時 allow になる。
  ただし plan-gate は workflow ゲートで、plan approved になれば従来も allow＝
  **グローバル設定の整合性保護を提供していない**。これは別機能（スコープ外）。security report に明記。
- **Client-mode 相互作用（grill-plan #1）**: short-circuit は Client-mode deny の前にも入るため、
  Client モードでも ROOT 外絶対パスが allow になる。これは意図的＝Client-mode deny は project code の
  ロックであり外部ファイル（auto-memory）は対象外。Client モードでも記憶は書ける必要があるため正しい。
  Client × ROOT 内は引き続き deny（test_f で担保）。
- **lexical / case 限界（grill-plan #5 ＋ 盲検 security 訂正・受容）**: symlink 偽装・case-insensitive FS
  （macOS）での大文字小文字ゆらぎにより ROOT 内絶対パスが外部判定されうる。**正確な特徴づけ（当初「新規の穴ではない」は不正確だった）**:
  control file への **case-variant 絶対パス**（例 `/PATH/AEGIS/hooks/x.sh`）は、PRE-C5 では `is_control_file` の
  case-sensitive マッチを外れても **plan-gate の偶発 backstop で deny** されていた。POST-C5 は short-circuit で
  **allow** になる＝C5 は plan-gate の *incidental な case-variant backstop を除去する*。
  **重大度 Low（conf 7・受容）**: (1) 自己誘発のみ（agent が非 framework 作業中に自分の hooks へ非正規 case の
  絶対パスを発行する必要があり非現実的）、(2) `is_control_file` は approved-plan 窓で既に同 lexical limit を共有、
  (3) plan-gate は security 境界でない。FS-aware case-folding は lexical-only 設計原則に反するため導入しない。受容。

## テスト戦略

- 単体: なし（bash フック）。
- 結合（新規 `tests/test_check_gate_root_external.py`、harness は `test_control_plane_allowlist.py` 流用）:
  hook を temp root に copy・libs（safety.sh/extract-input.sh/emit.sh/frontmatter.sh）を symlink・
  temp `docs/STATUS.md` を mode/plan/task_type ごとに設定して invoke（6 ケース・RED は厳密 assert）:
  1. test_a: Dev・plan=pending・絶対 ROOT 外 → allow（**修正前は deny ＝ RED 厳密 assert**）
  2. test_b: Dev・plan=pending・絶対 ROOT 内 `{root}/src/main.py` → deny（回帰・ROOT/ROOT_REAL 両形）
  3. test_c: control file `{root}/hooks/x.sh`（task_type=feature）→ deny（回帰）
  4. test_d: `{root}/docs/foo.md` → allow（回帰）
  5. test_e: Client mode・絶対 ROOT 外 → allow（mode 非依存・#1）
  6. test_f: Client mode・絶対 ROOT 内 `src/x.py` → deny（Client code ロック維持・#1）
- RED 厳密 assert（#2）: `if out:` ガード不使用。`emit_allow` 実出力を `emit.sh` で確認し allow を明示 assert、
  修正前に test_a が deny で必ず FAIL することを実測。
- 手動確認: full suite（record-test-result）green・`bash -n hooks/check-gate.sh`。

## 次のステップ

- [x] 実装計画を作成する → `docs/plans/2026-06-25-iter44-root-external-plan-gate-implementation-plan.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
