# iter66 review レポート — SF-010 封鎖＋frontmatter 読取意味論統一

- **対象**: `deb4a8a..HEAD`（実装 10 コミット `abf6d04`〜`6148a60`）
- **task_type/size**: framework / M（control-plane につき review+qa+security 必須・deploy skip）
- **仕様正本**: `docs/specs/2026-07-12-iter66-sf010-parser-unification-design.md`
- **計画**: `docs/plans/2026-07-12-iter66-sf010-parser-unification-implementation-plan.md`
- **動機正本**: `docs/security-followups.md` SF-010
- **判定**: **PASS**（1次4角度＋親 verify＋盲検2次が approve に収束・Major×4 は fix-forward で解消済み）

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | コミット | 状態 |
|---|------------|------------|---------|------|
| 0 | STATUS 読点 census（enforcement/advisory/writer 分類） | （調査・台帳のみ） | a78de80（盲点補正） | 済（新規 enforcement hit 0・2 regex 再実行一致） |
| 1 | frontmatter_value スコープ化（Fix②） | hooks/lib/frontmatter.sh・tests/test_frontmatter_lib.py | abf6d04 | 済 |
| 2 | gate_value 本文 fallback 厳格化（Fix④・F-2） | hooks/lib/frontmatter.sh・tests/test_frontmatter_lib.py | c5f5fd2 | 済 |
| 3 | snapshot 生成スコープ化＋regen 潜在バグ修復（Fix③） | hooks/lib/snapshot.sh・tests/test_snapshot_helper.py | c5f63e4 | 済 |
| 4 | migration-grace 絞り込み task+gate（Fix①・SF-010 本丸） | hooks/post-status-audit.sh・tests/test_post_status_audit_task_tamper.py・tests/test_snapshot_writers.py | feff60c | 済 |
| 5 | python 意味論同期（Fix⑤・F-1） | scripts/check_status.py・tests/test_check_status_parsers.py | 6229fd5 | 済 |
| 6 | check-gate dedup（意味論の単一ソース化） | hooks/check-gate.sh | c3d7e76 | 済 |
| 7 | parity drift-guard（fixture a-f） | tests/test_parser_parity_driftguard.py | fba9b08 | 済 |
| FF-grill | regression 関数読点スコープ化（census 盲点）＋---判定終端許容整合＋snapshot gate 節ガード | hooks/lib/snapshot.sh・frontmatter.sh・tests | 1934c98 | 済（🟡3＋🟢1） |
| FF-review | bash 値正規化を python に一致（_strip_scalar）＋gate_value 行頭アンカー＋parity fixture g-k | hooks/lib/frontmatter.sh・tests・design spec | 6148a60 | 済（Major×4 解消） |

全タスク実装済み・未着手ゼロ。`git diff --stat deb4a8a..HEAD -- hooks/ scripts/ tests/` = 11 files / +650 / -58。

## 1次レビュー（4角度・finder=opus・親 verify=fable）

### 角度1: gate 迂回 / セキュリティ穴 — **approve_with_notes**（confidence 9-10）
scratch で実 hook 発火。SF-010 全ベクタが block/無害化を実測:
- A1 empty-baseline `task_size: S` 注入 → `[task-tamper]` block（`post-status-audit.sh:220-234`・`SNAP_IS_CURRENT_FORMAT`）
- A2 gate 行欠落 snapshot `deploy: approved` → `[gate-tamper]` block（`:151-166`・`SNAP_HAS_GATE_SECTION`）
- A3 本文 spoof → frontmatter スコープ読みで不可視 / A4 真の旧フォーマット → grace 温存
- **脅威モデル境界確定**: `.claude/.gate-snapshot` は OS-lock 対象外・Edit 偽造可能（Bash 書込みのみ deny）。gate 節剥がしは「snapshot を OLD==NEW に完全偽造」より厳密に弱く、完全偽造は文書化済み境界（tamper-evidence であって forgery-proof ではない・SF-006 較正）。narrowing は「gate 節在・1行欠落の stale/silent-fail snapshot（現実に発生しうる）」への defense-in-depth＝正味プラス・regression なし。
- note: `--- `（末尾空白）predicate は plan の完全一致から逸脱するが fail-closed 強化方向（穴を閉じる・実装 comment 文書化済み）。

### 角度2: 正規フロー回帰 / 誤 block — **approve**（confidence 高）
scratch で real hooks 実発火。遷移列 7 段（rollover→update-task→Edit→gate approve→audit→phase 遷移→plan approve）全て allow を実測。正規 writer（update-gate/update-task）は snapshot 原子更新で OLD==NEW＝誤 block なし。`aegis_write_snapshot` 全 4 呼出が `|| true` ガード確認。正常系 snapshot は byte-shape 同値（旧 range-sed の本文毒込みを修復）。gate-loop narrowing は正規生成 snapshot（常に 8 gate 完備）では発火せず。full 1127 passed（fix-forward 前時点）。

### 角度3: テスト強度 / vacuous 検出 — **approve**（confidence 高）
変異 9/9 KILL 実測（scratch コピー）。block-for-the-right-reason を stdout で裏取り（`gate-tamper`/`task-tamper` の種別文字列まで load-bearing）。正常系 snapshot byte ピンは全文 assertEqual。vacuous/stub/skip/xfail なし。Minor 1件（parity fixture f の python 側短絡）は文書化済み境界で修正不要。

### 角度4: bash↔python パーサ整合 — 1次 **reject**（Major×4）→ **fix-forward で解消**
1次 finder（パーサ整合）が spec line 38「python は bash と同一の値・parity guard で機械保証」に対する実測割れを4件検出:
1. single-quote 値: bash `'S'` / python `S`（`frontmatter.sh` は double-quote のみ剥がす）
2. 末尾空白: bash `S ` / python `S`
3. 4-space インデント gate: bash `approved`（`grep "  ${gate}:"` 部分一致で誤検出）/ python `''`
4. parity fixture a-f がこれらを一切カバーせず（機械保証に歯なし）

**親 verify 裁定**（fable・実測で裏取り）: 事実主張は Case A/B/C を実行して確認。ただし live gate-bypass は無い（値割れは tamper 保護＝audit は bash-vs-bash 比較で相殺・python は表示/検査系で gate 判定正本ではない・かつ全て fail-closed 方向）。**しかし設計正本が明示する「機械保証」が成立していない穴は実在**。ユーザー基準（moat は網羅性・限界主張は実証）に照らし Minor で流さず **fix-forward**（`6148a60`）:
- `_strip_scalar` ヘルパーで bash を python `.strip().strip('"').strip("'")` にバイト一致（single-quote 剥がし＋前後空白 trim）
- `gate_value` の grep を `^  ${gate}:` 行頭アンカー化（4-space 部分一致誤検出封鎖・fail-closed）
- parity fixture g-k 追加（single-quote scalar/末尾空白/4-space gate/single-quote gate/double-quote scalar）＝これらに歯
- 設計ノート line 70 に parity 契約の範囲と残余限界を実証ベースで明記（多重ネストクォート `""S""` は authorized writer 非生成＋tamper-block＝契約外・fail-closed）
mutant flip で歯を確認（single-quote strip 削除→test_g/test_j FAIL）。full **1138 passed**・contract PASS。

## Evidence Checklist
- [x] diff を Read/Grep で実読（chat summary ではなく実ファイル・実 hook 発火）
- [x] plan/spec の受入条件と突合（対照表・全タスク写像）
- [x] エッジケース列挙（本文 spoof/重複キー/未終端/4-space/quote 各種/末尾空白/CRLF/snapshot 手彫り）
- [x] 全 finding に severity と confidence 付与

## canonical SF-010 の閉塞実測（baseline → HEAD）

| ケース | baseline `deb4a8a` | HEAD `6148a60` |
|--------|--------------------|-----------------|
| canonical SF-010（task_size empty-baseline 注入・gate 節在） | **ALLOWED（穴）** | **BLOCKED** ✓ |
| gate 1行欠落 snapshot `deploy: approved` | ALLOWED（grace） | **BLOCKED** ✓ |
| 本文 spoof task_size | whole-file grep が拾い spoof | scoped 読みで**不可視** ✓ |
| 真の旧フォーマット（task_type 行なし） | grace | grace 温存 ✓ |

全変更 deny 方向のみ（allow が増える経路ゼロ）を実測。

## テスト実測
- full suite: `python3 -m pytest tests/ -q` → **1138 passed / 2 skipped / 0 failed**
- contract: `python3 scripts/check_framework_contract.py` → **PASS**
- 既知 flaky `test_update_gate_lock`（lock 待ちタイミング・本 diff 不接触＝回帰外・full-review R10 test#8）は fix-forward 走で顕在化せず

## 盲検 第2意見（self-attested）

1次（4角度・親 verify）は Major×4 を検出し fix-forward `6148a60` で全解消・統合 verdict は approve_with_notes（notes＝parity 契約の範囲/残余限界・`--- ` predicate 逸脱は fail-closed 強化・脅威モデル境界は SF-006 較正どおり）。盲検2次（fable・fresh context・1次結論未参照）は独立実測で approve。結論レベルの割れなし。

```claims
tests_pass: true
no_stubs: true
verdict: approve_with_notes
second_opinion:
  verdict: approve
  divergence_points: []
  evidence: "scratch で hook 実発火。SF-010 (i)(ii)(iii) 実 block（P1/P2/P3）・回避経路 P6-P10 全て fail-closed・正規フロー N1-N4 無影響・mutant 5件全赤（python旧2-pass/gate アンカー緩め/SNAP_IS_CURRENT_FORMAT除去/SNAP_HAS_GATE_SECTION除去/single-quote strip削除）・1138 passed・contract PASS・census 2 regex 新規 enforcement hit 0・tree clean。findings なし。"
```

## 結論
**review PASS**。SF-010 本丸＋(iii) gate 経路を Task 4 grace 絞り込みで構造閉鎖、bash/python パーサ意味論を _strip_scalar＋行頭アンカーで一致させ parity drift-guard（a-k）で機械保証。全変更 fail-closed・full 1138 passed・contract PASS。qa フェーズへ。
