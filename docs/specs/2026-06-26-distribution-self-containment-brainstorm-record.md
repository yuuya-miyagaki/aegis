# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-26（iteration 48）

## テーマ

- 配布の参照整合性（self-containment）強化: shipped artifact の依存閉包を profile に
  保証する横断検査と、現存 2 穴（D5 / JNY-07）の解消。

## コンテキスト

- 現在の状況: full-review backlog triaged-complete（残実コード修正タスク=ゼロ）。
  backlog 枯渇後の最初の実需テーマとして「(c) 配布強化」を選定（ユーザー委任）。
- きっかけ: grill-premise で配布テーマを精査した結果、install 単体は厚く硬化済みで
  限界効用が低い一方、「self-containment（参照整合性）が無検査」という網の隙間から、
  すでに 2 件の shipped 機能が現場で死んでいることを**実証**（D5 / JNY-07）。

## 検討したアプローチ

### アプローチ A: D5 穴だけを単発修正

- 概要: status_doctor→check_framework_contract の 1 穴のみ塞ぐ。
- 利点: 最小。
- 欠点: 同一クラスの再発（F6→D5→JNY-07）を止められない。JNY-07 を見落とす。
  D5 は maintainer 専用で field 価値が薄く、単発修正の費用対効果が低い。

### アプローチ B: 横断的な参照整合性チェック（採用）

- 概要: 各 profile で「shipped .py の実行時依存が同梱 or 理由付き allow-list」を恒久
  検査するテストを 1 本追加。現存 2 穴を RED で捕まえ、JNY-07 を実修正・D5 を
  allow-list 明記で GREEN。
- 利点: F6/D5/JNY-07 の CLASS を恒久封鎖。iter41 D1（judge toolchain 依存閉包）の
  個別対処を一般化。bounded（テスト 1 本＋小修正）。
- 欠点: 「どこまでの参照辺を見るか」のスコープ判断が要る（YAGNI 線引き）。

### アプローチ C: 全参照辺（command→script・skill→asset 含む）の網羅スキャナ

- 概要: あらゆる artifact のあらゆるパス参照を静的解析。
- 利点: 最も網羅的。
- 欠点: スコープ膨張・ノイズ源（skill 散文の擬似パス等）・YAGNI。first slice に不適。

## 決定

- 採用アプローチ: **B**。
- 採用理由: 実証済み 2 穴を含む CLASS を、最小侵襲（テスト 1 本＋実修正 1＋allow-list 1）
  で恒久封鎖。投機性が最も低い（再発が一次情報で確認済み）。
- 不採用理由: A=再発を止められず費用対効果が低い。C=スコープ膨張で YAGNI、first slice
  に不適（将来スライスへ）。

## スコープ境界

- やること: Python モジュール import 辺 + status_doctor→check_framework_contract の
  既知 string-read 辺の横断検査。JNY-07 実修正（`_artifact_template_map.py` を full 同梱）。
  D5 allow-list 明記。README 件数同期。
- やらないこと: command(.md)→script / skill 散文参照の網羅 / 対話的インストーラ /
  downgrade ガード / orphan 削除（現アーキで害が投機的）/ contract ツールチェーンの
  install 同梱。

## 未解決事項

- D5 の最終処遇（allow-list vs ship）は SPEC で確定 → **allow-list**（理由: contract
  ツールチェーン = check_framework_contract+platform_manifest+context_budget の依存閉包を
  install に引きずり込むのは過大。D5 ドリフトは maintainer→install 方向の検査で、install
  単体では構造的に新版を観測不能＝field no-op は by-design）。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-26-distribution-self-containment-design.md`
- テンプレート名: `SPEC.template.md`
