# 設計ノート（spec-delta: ドッグフード由来 改善・上流実行版）
<!-- 正本: dogfood セッションの brainstorming（下記「入力」参照）。本ファイルは上流本体での実行に固有な判断のみを捕捉する delta。 -->

## 入力

- ブレインストーミング記録 / 設計（正本・別リポ）:
  - `~/Desktop/personal/aegis-dogfood-reservation-lp/docs/specs/2026-06-15-aegis-dogfood-improvements-brainstorm-record.md`
  - `~/Desktop/personal/aegis-dogfood-reservation-lp/docs/specs/2026-06-15-aegis-dogfood-improvements-design.md`
  - 一次情報: 同リポ `docs/dogfood-backlog.md` / `dogfood-notes/observations.md`（OBS-001〜022）
- 実装計画（本リポ）: `docs/plans/2026-06-15-dogfood-driven-improvements-plan.md`
- 要件（本リポ）: `docs/full-review-2026-06-13-context-futureproof.md`

## 問題整理

- 背景: スタジオ・ナギ予約LP で Aegis v1.10.0 を Client→Dev 一周ドッグフードし、ハーネス自身の摩擦 OBS-001〜022 を抽出。dogfood リポから本リポを編集すると本リポの Aegis ゲートが発火せず保護を迂回する（OBS-002）ため、**本リポを root にした CC セッション**で新 iteration として消化する。
- 判断が必要な論点: (1) control-plane フックの精度を上げつつ moat を緩めない境界、(2) install 配布物と本リポ実体の整合をどう機械保証するか。
- 制約条件: セキュリティ後退禁止（fail-closed 優先）。残すべき勝ち（OBS-010/014/016/019/021/022）をリグレッションさせない。

## 推奨アプローチ

- 採用方針: 根本原因クラスタでバッチ化し、配布ブロッカー（P0）を先頭に。Batch1=A(control-plane フック精度)+B(git baseline) / Batch2=C(skill/契約/**配布**整合) / Batch3=D(Client 書込み)。横断 X.1/X.2 は関連バッチに便乗。
- 採用理由: 非エンジニアの初回 Client→Dev 一周が「規定どおり進めて弾かれない」状態を最短で達成し、配布欠落（install が参照する script が配布されない）を不変条件化して再発を断つ。
- 検討した代替案と不採用理由: P1-5（ブラウザ QA 方式）・P2-9（subagent 粒度例外）は n=1 では方式確定不能 → 2周目ドッグフード（n=2）まで保留。

## 上流実行固有の判断（delta の核）

1. **配布整合の不変条件（新規）**: install へ配布される hooks/CLAUDE/scripts が参照する全 `scripts/*.py` が `bin/setup.sh` の配布集合に含まれることを `tests/test_setup_distribution.py` で機械保証する。OBS 由来の配布バグ（`check_framework_contract.py`・`_artifact_template_map.py` が本リポに実在するが install へ配布されず、install 側の allowlist / CLAUDE / import が不在を参照）の再発防止。
2. **セキュリティ感応度の段階管理**: Batch1.A は allowlist/deny の moat を緩めうる。新規許可は「読み取り専用 or 証拠記録に限定」、曖昧なら fail-closed。Task 1.5/1.6 は control-plane フック本体の判定変更で感応度が最も高く、**security ゲートで盲検2次レビュー必須**。
3. **各タスク Step 0**: dogfood は v1.10.0 install を参照したが本リポは更に進んでいる可能性があるため、着手時に `git log`/`grep` で「既済/部分済/健在」を判定してから TDD に入る。

## テスト戦略

- 単体: 各タスク TDD（失敗テスト→実装→緑→commit）。control-plane 変更は `tests/test_control_plane_var_expansion.py`・`tests/test_patterns_parity.py`・`tests/test_secrets_*` を緑に保つ。
- 結合: 配布整合 `tests/test_setup_distribution.py`、skill 注入 `tests/test_phase_skill_injection.py`、judge `tests/test_judge_card.py`。
- エッジケース: REDTEAM 回帰（`git add -A`・`x && rm y`・`git apply`・`> $(echo hooks)/lib`・`"validator && malicious"`）を deny 維持。
- 手動確認: 新規 install→初回ドッグフードの review ゲートが framework 由来 stub 🔴 を出さない（1.1+1.2）。Client→Dev リハーサル（2.2）。

## 依存関係

- 依存方向: 1.4→1.1、A群→B群、Batch1→2→3。循環なし。保留 E は n=2 依存。

## 次のステップ

- [x] 実装計画は既存 → `docs/plans/2026-06-15-dogfood-driven-improvements-plan.md`
- [ ] plan ゲート承認後、implement で Batch1 から着手。
<!-- exit-check: 上流実行固有の判断を捕捉・plan と整合 → plan へ -->
