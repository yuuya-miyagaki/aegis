# iter50 レビュー — doc(CLAUDE.md/rules)→script 参照整合性 guard

- 対象 diff（uncommitted・production 相当）:
  - `tests/test_profile_referential_integrity.py`（+約290）: iter50 セクション＝install 実体の doc(CLAUDE.md=template remap / rules=verbatim)→script 参照整合性検査を追加。
  - `docs/STATUS.md`: フェーズ/ゲート/refs（プロセス状態）。
- 参照: spec=`docs/specs/2026-06-27-doc-script-ref-integrity-design.md`／
  plan=`docs/plans/2026-06-27-doc-script-ref-integrity-implementation-plan.md`／
  record=`docs/specs/2026-06-27-doc-script-ref-integrity-brainstorm-record.md`
- 方針: **guard-only**（grill-premise で実穴ゼロを実証）。成果＝「全 install surface を1原理で覆う regression guard ＋ maintainer 参照の allow-list 明示化」。「実穴を直した」とは主張しない。
- 検証: 各 helper TDD RED→GREEN・本体 guard の歯は allow-list トグルで3 profile 違反検出を手動実測・アンカーの歯は drift/dead-key/parse 失敗の3 mutation 全捕捉・**test file 36 passed**（full suite 再検証は qa）。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装 | 状態 | 備考 |
|---|------------|------|------|------|
| T1 | doc resolver | `_DOC_TEMPLATE_REMAP`＋`_doc_install_source`＋2単体 | ✅ | CLAUDE.md→template/rules→verbatim・明示 map で fail-closed |
| T2 | アンカー（コメント耐性 parse） | `_SETUP_CASE_RE`＋`_setup_resolve_remap`＋`test_doc_resolver_matches_setup_sh`＋parse 4単体 | ✅ | 健全性 assert＋全 surface 一致＋dead-key 禁止・コメント行除去で quoted-comment 耐性 |
| T3 | doc edge 抽出（再利用） | `_doc_script_edges = _skill_script_edges`＋1単体 | ✅ | 新ロジックなし（YAGNI）・呼び出し側自己説明化 |
| T4 | `_shipped_doc_surfaces` | 実装＋2単体 | ✅ | CLAUDE.md∪rules 選別・commands/agents/skills 除外 |
| T5 | allow-list＋governance | `INTENTIONAL_UNSHIPPED_DOC`＋reason 非空＋rot 2単体 | ✅ | 3 profile×check_framework_contract.py・referrer 差明記＋cross-ref |
| T6 | 本体 cross-check | `test_every_profile_doc_script_ref_is_self_contained` | ✅ | install 実体読込・allow-list トグルで RED→GREEN 実測 |

未着手タスクなし。

## Findings（severity＋confidence）

### 1次レビュー（grill-code 由来・self）
- **Minor/🟡（conf 8）**: doc パイプラインが `_skill_script_edges` を doc 本文に直接適用＝命名で読み手が二度見 → **解消**（`_doc_script_edges` 別名で呼び出し側自己説明化・呼び出し3か所置換）。
- **Minor/🟢（conf 6）**: `_all_doc_surfaces` 単一使用・profile 反復が3か所散在 → 受容（テスト独立性・iter48/49 と同スタイル）。
- **Minor/🟢（conf 5）**: `(.*?)\besac\b` 非貪欲＝case 本文に "esac" 文字列があると早期 truncate → 理論上・現 setup.sh で非発生・受容。

### 2次レビュー（盲検・reviewer-testing・fresh context）
- **F1 Minor（conf 7）**: `_SETUP_CASE_RE` の `[^"]*?` がコメント中の `"` で停止＝quoted-comment の case を取りこぼす（fail-closed だが未文書化の robustness gap） → **解消**（`_setup_resolve_remap` で行コメント事前除去＋`test_setup_parse_tolerates_quoted_comment_in_case` を RED→GREEN で固定）。
- **F2 Minor（conf 8）**: アンカーは CLAUDE.md+rules 以外の新 doc surface（例 docs/STATUS.md が profile required に追加）を `_shipped_doc_surfaces` が除外して silently skip → **受容＝iter50 の明示 scope 境界**（spec 記載・現状 rules/CLAUDE.md 以外の doc は script 非参照＝YAGNI。穴が出たら同機構で別スライス、iter49 の agents 同様）。
- **F3 Minor（conf 6）**: `test_doc_edge_picks_check_contract_from_prose` は既テスト関数の pass-through で marginal coverage 低 → **受容＝plan 明示の最小 fixture**（alias 再代入/regex 変更の回帰は捕捉＝tautological でない）。

Critical/Major: 1次・2次とも **ゼロ**。

## Evidence Checklist

- [x] diff を実読（chat summary でなく実ファイル・1次は grill-code、2次は git diff 実読）
- [x] plan/spec の受入条件と突合（対照表・全 T1-T6 ✅）
- [x] 未カバーのエッジ列挙（F2 scope 境界・F3 marginal を明記）
- [x] 全 finding に severity＋confidence 付与（<7 は F1=7 が境界・解消済／🟢 advisory に注記）

## 判定

**PASS（approve_with_notes）。** Critical/Major ゼロ。actionable な 🟡（命名）と 2次 F1（quoted-comment robustness）は本レビュー中に解消し RED→GREEN/再走で実証。残る Minor は scope 境界・意図的最小として裁定一致。tests=verified（test file 36 passed・full suite は qa で再検証）。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "1次/2次に実質的相違なし。両者 approve_with_notes。2次 F1(quoted-comment parse の取りこぼし=fail-closed だが robustness gap)を行コメント事前除去＋専用テストで解消。F2(非 CLAUDE/rules の新 doc surface 非保護)は iter50 の明示 scope 境界として裁定一致、F3(doc-edge テストの marginal coverage)は plan 明示の最小 fixture として一致。Critical/Major は双方ゼロ。"
```
