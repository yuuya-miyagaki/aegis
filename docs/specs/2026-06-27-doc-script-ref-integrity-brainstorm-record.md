# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-27（iteration 50）

## テーマ

- 配布 self-containment 検査の射程を、残る install surface の doc（`CLAUDE.md` / `.claude/rules/*.md`）→ `scripts/*` 参照へ拡大する（(A)）。

## コンテキスト

- 現在の状況: iter48（profile の script→script 依存）＋ iter49（skill→script）で install surface の2面を参照整合性で固めた。残る未検査面が rules/CLAUDE.md。
- きっかけ: 「全 install surface を1原理で覆う」完了宣言。ただし grill-premise で **install 実体には壊れた参照がゼロ**と判明（下記）。

## grill-premise の結論（premise 縮小・重要）

- install 実体で grep すると **既存の壊れた参照はゼロ**:
  - `rules/state-machine.md` → `update-task.sh` は、それを同梱する full/standard で両方とも同梱済（minimal は doc も script も積まない＝参照なし）＝**充足済**。
  - install される CLAUDE.md は `templates/CLAUDE.template.md` で、参照 script は `check_framework_contract.py` ただ1つ。これは iter48 で「maintainer 専用・意図的非同梱」と確定済＝**穴でなく allow-list 対象**。
- よって本イテレーションは **実穴を直す仕事ではなく regression 防止 guard**。最初から GREEN になる性質。honest framing を厳守（「実穴を直した」と言わない）。
- dogfood の repo-root CLAUDE.md は4 script を参照するが、install されない版。**install 実体（resolve_source の source）を読む**規律（iter49 conf8）がここで効く。

## 検討したアプローチ（doc → install-source の解決方式）

### アプローチ A: 明示 resolver ＋ アンカーテストで drift 封鎖（採用）

- 概要: test 内に `_DOC_TEMPLATE_REMAP`＋`_doc_install_source(rel)` を置き、CLAUDE.md→template / rules→verbatim を mirror。別途アンカーテストが setup.sh:resolve_source の case 行を正規表現抽出し、resolver が setup.sh と一致することを assert。
- 利点: 本ファイルの static/fast を維持・install 実体に忠実・drift をアンカーが**明示 fail** で捕捉・検査本体は parse に依存しない（fail-closed）。
- 欠点: resolver を二重持ち（ただしアンカーが同期強制）。

### アプローチ B: setup.sh を毎回パースして remap を動的構築

- 概要: 明示 map を持たず検査時に setup.sh から remap を組む。
- 利点: 二重持ちゼロ。
- 欠点: bash 整形に密結合で脆い。parse 失敗が空 map→verbatim fallback→**false-clean**（D5 型 fail-open）になりうる。

### アプローチ C: install e2e（temp install して installed 実体を scan）

- 概要: `test_profile_checker_parity.py` の install e2e に倣い各 profile を temp install し installed CLAUDE.md/rules を読む。
- 利点: 最も忠実（真の install 実体）。
- 欠点: 重い・遅い・static 中心の本ファイルに e2e を混在＝性格分裂。guard 1 件には機会費用過剰。

## 決定

- 採用アプローチ: **A（明示 resolver ＋ アンカー）**。
- 採用理由: install 実体への忠実さ（iter49 教訓）を満たしつつ static/fast を保ち、drift を明示 fail で捕捉。明示 map で fail-closed（B の fail-open を回避）。
- 不採用理由: B は parse 脆性＋fail-open リスクでアンカーに劣る。C は guard 1 件に過剰で本ファイルの性格を割る。

## スコープ境界

- やること: `CLAUDE.md`（template 実体）＋ `.claude/rules/*.md`（verbatim）の → `scripts/*.(py|sh)` 参照を各 profile で「同梱 ∨ 理由付き `INTENTIONAL_UNSHIPPED_DOC`」で検査。`check_framework_contract.py` を3 profile で allow-list 明示化。negative-control／rot 検知／アンカーで歯を担保。
- やらないこと: 実穴修正（存在しない）。`.claude/commands/*.md`（iter49 で scaffold-safe remap と確定＝別問題）。`.claude/agents/*.md`（script 参照ゼロ実証済）。新 script の profile 同梱（不要）。production code 改変。

## 未解決事項

- サイズ: 実 footprint は test 1 ファイル＝素直には S。guard の独立 qa mutation 実証（iter48/49 踏襲）を取るなら M。**M 推奨・S も弁護可能**。最終確定は plan の Step D（update-task.sh）。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-27-doc-script-ref-integrity-design.md`
- テンプレート名: `SPEC.template.md`
