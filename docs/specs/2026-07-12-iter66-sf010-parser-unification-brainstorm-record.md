# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-12（iter66）

## テーマ

- SF-010 封鎖＋frontmatter 読取意味論の統一（task_size empty-baseline raw-Edit×migration-grace 穴・パーサ二重実装 drift 3 件）

## コンテキスト

- 現在の状況: iter65（S サイズ修復）で task_size が gate 判定に昇格した結果、`hooks/post-status-audit.sh` の migration-grace（snapshot 側の値が空なら block スキップ）が初めて gate-bypass に転化（SF-010・Medium・OPEN）。iter65 security 盲検2次で residual ack 済み・専用反復での対応が正本（docs/security-followups.md SF-010）に宣言済み。
- きっかけ: iter65 review 1次 finder（gate 迂回角度）が独立再現・CONFIRMED。同根としてパーサ二重実装 drift 3 件（i: gate_approvals 重複キーの bash 先勝ち/python 後勝ち乖離、ii: extract_scalar_value の引用形優先＝F-1、iii: gate_value の raw_section 本文フォールバック＝F-2）が明示スコープ宣言された。
- 探索で確定した事実:
  - bash `frontmatter_value`（hooks/lib/frontmatter.sh）は whole-file `grep -m1` ＝本文行も拾う。snapshot 生成（hooks/lib/snapshot.sh:35-36 と gate_approvals ブロック sed）も whole-file ＝監査 baseline 側も毒込み可能。
  - iter65 b9c95f7 は check-gate.sh **だけ**を frontmatter スコープ化した局所修復（読点ごとの穴塞ぎ）。
  - python `extract_scalar_value` は引用形を frontmatter 全域から優先探索（bash=M / python=S の割れを実測済）。`extract_approval_map` は重複キー後勝ち。

## 検討したアプローチ

### アプローチ A: grace 絞り込み＋意味論統一（library 級）

- 概要: ①migration-grace を「snapshot に task_type 行が無い真の旧フォーマット」限定に絞る ②`frontmatter_value` を library 級でスコープ化（`---` あり→frontmatter 内 first-match／bare→whole-file 温存／未終端→空＝fail-closed） ③snapshot 生成もスコープ化 ④`gate_value` の本文 fallback を「`---` 無しファイル限定」に ⑤python を行順 first-match・先勝ちに同期 ⑥bash↔python parity drift-guard テスト。
- 利点: 「frontmatter 内の最初の値」という単一意味論で同根を一括根治。audit の比較元・比較先の毒込みも一点で封鎖。呼出契約（absent→空+rc0）不変で 9 hook 消費側は無改修。
- 欠点: library 変更のため回帰面が広い（full suite 1096＋scaffold smoke でピン）。

### アプローチ B: grace 絞り込み＋読点限定スコープ化

- 概要: ①④⑤⑥ は A と同じ。②を library 変更ではなく security-relevant な読点（audit/snapshot の task fields）だけ個別スコープ化。
- 利点: diff が小さい。
- 欠点: 「同じ穴を読点ごとに塞ぐ」b9c95f7 の反復＝5 個目の読点が増えたら再発。意味論の drift 面が残る。

### アプローチ C: grace 絞り込みのみ（最小）

- 概要: SF-010 の直接経路だけ封鎖。パーサ drift 3 件は OPEN のまま次反復送り。
- 利点: 最小 footprint。
- 欠点: 正本が「SF-010 修正時に明示スコープに含める」と宣言済みの 3 件を先送り＝トラッカー更新も必要。F-1（audit-evading enforcement 緩和）が残る。

## 決定

- 採用アプローチ: A（grace 絞り込み＋意味論統一 library 級）
- 採用理由: 同根（読取意味論の不統一）を機構で根治し parity guard で将来 drift を機械検知する構え。iter65 教訓「gate 判定への昇格は読取厳格性・監査カバレッジとセットで検証」「緩い bash を厳しい python に意味で揃え parity guard をセットに」に整合。
- 不採用理由: B は読点単位のモグラ叩き再発リスク。C はトラッカー宣言違反かつ F-1 残置。単一パーサ統合（bash→python 委譲）は fail-open 退行のため iter65 却下済み前提を踏襲し検討対象外。

## スコープ境界

- やること: Fix ①〜⑤（post-status-audit.sh / frontmatter.sh / snapshot.sh / check_status.py / check-gate.sh dedup）＋TDD RED-first テスト＋parity drift-guard＋SF-010 CLOSED 化（i/ii/iii 消化明記）。
- やらないこと: 単一パーサ統合（fail-open）／敵対的 chmod・snapshot 削除耐性（脅威モデル外・SF-006 較正）／update-gate approve --ref 原子化（full-review 1-3・別反復）／YAML 完全準拠パーサ化（YAGNI）。

## 未解決事項

- なし

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-12-iter66-sf010-parser-unification-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->
