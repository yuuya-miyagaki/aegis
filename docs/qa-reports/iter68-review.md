# iter68 Review Report — update-gate `approve --ref` 原子化＋SIGPIPE 耐性＋pending+ref advisory 降格

- 日付: 2026-07-13
- 対象: git 範囲 `8ab52ed..1956ac1`（実装 4 commit＋grill-code fix-forward 9cfd3d8＋review fix-forward 1956ac1）
- 仕様正本: docs/specs/2026-07-12-iter68-update-gate-ref-atomic-design.md
- 計画正本: docs/plans/2026-07-12-iter68-update-gate-ref-atomic-implementation-plan.md
- 体制: 1次4角度（仕様準拠・敵対バグ=opus／テスト強度=reviewer-testing／保守性=reviewer-maintainability）→ 親 verify（fable・実測裏取り）→ fix-forward → 盲検2次（fable・fresh）

## 対照表（plan タスク ↔ 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | RED テスト | tests/test_update_gate_ref_atomic.py（新規15→18本）・tests/test_check_status.py（1置換＋3追加） | 完了 | 2c92338・RED 分布 18 failed/124 passed（全て機能未実装由来） |
| 2 | check_status.py 降格＋ADVISORY 抑止 | scripts/check_status.py | 完了 | c9024c7・stderr WARNING（stdout=violation チャネル維持） |
| 3 | update-gate.sh --ref・書込み先行・trap | scripts/update-gate.sh | 完了 | cd96930・単一 sed 三態＋print_report best-effort |
| 4 | guidance 同期 | gate.md/CLAUDE.md/skill 5枚/onboarding 2枚 | 完了 | a66ac43＋70d0bc6（Task4 内 grill 指摘 G4/G5/G6/G8 fix-forward） |

## 1次レビュー verdict（4角度とも approve_with_notes・reject 0）

### 主要 finding と処置

| # | 角度 | Severity | Conf | 内容 | 処置 |
|---|---|---|---|---|---|
| F-1 | 敵対バグ | **Major** | 8→10 | pre-write sanity の `frontmatter_section \| grep -q` が EPIPE レースで正当 approve を偽拒否（reviewer 実測 3/500・trap 有無対照 43/100 vs 12/100）。**親の grill-code 時の安全主張（単一 printf で競合不発）を実験で反証**。親 verify で単離再現 **58/3000** を独立確認 | **修正済（1956ac1）**: pre-write を変数キャプチャ＋case インメモリ判定・CURRENT 読取を全量読み化（修正形は親実測 **0/3000**×2種・負例/インデント誤マッチ検査 OK）・trap 監査コメントを実測事実へ訂正・回帰構造ピン `test_no_early_exit_pipe_consumers_structure` 追加 |
| T-1 | テスト強度 | Major | 8 | 変異(a)「sed 書込みを2回に分割」が全テスト未検出（並行 reader の中間状態観測はプロセス間タイミング依存で動的テスト原理的困難） | **修正済（1956ac1）**: 静的ピン `test_single_write_structure`（単一 sed・単一 mv の出現回数=1） |
| T-2 | テスト強度 | Major | 8 | fixture が current_refs 直後に frontmatter 終端 `---` で本番と異なり、sed 範囲終端（`^[a-z]`）経路が未検証 | **修正済（1956ac1）**: fixture に top-level key `next_action` を追加（本番同型で範囲が閉じる） |
| T-3 | テスト強度 | Minor | 7 | `--ref ""`（空文字）が「未指定」扱いに化け approved+空の遅延 FAIL になる | **修正済（1956ac1）**: parser で非空必須＋`test_ref_empty_string_rejected` |
| F-2 | 敵対バグ | Low | 8 | sed 範囲終端 `/^[a-z]/` は `---` で閉じず、current_refs が frontmatter 末尾 key の異常 STATUS では body へ leak し得る。**pre-existing**（baseline の reset null 化と同一パターン）・canonical STATUS（external_evidence/next_action が続く）では到達不能 | **SF-013 起票**（security フェーズで docs/security-followups.md へ・iter69+ hardening 候補） |
| S-1 | 仕様準拠 | Minor | 6 | ship-and-docs skill が計画 File Structure 記載なのに diff 不在＝スキップ理由未記録 | **親 verify で解消**: 同 skill の update-gate 行は `dev_ready_for_client approve`（ref key 無し gate）のみ＝計画の「変更しない」対象。スキップは正当（本レポートで記録） |
| M-1 | 保守性 | Minor | 8 | REF_KEY_SED 計算のコピペ重複 | **修正済（1956ac1）**: 事前一括計算に統合 |
| M-2 | 保守性 | Minor | 7 | stdout=violation チャネル契約が check-task-completed.sh 側に相互参照コメントなし | **修正済（1956ac1）**: hook 側にチャネル契約コメント追加 |
| M-3 | 保守性 | Minor | 7 | client-workflow の表・手順に旧手順を連想させる短縮表現残存 | **修正済（1956ac1・9cfd3d8）**: 原子承認文言へ統一（budget 450 語以内に収めるためトークン等価で調整） |

### 記録して繰延（非ブロッキング・全て理由付き）

- **client_ready_for_dev `approve --ref`（translation）実行経路のテスト未カバー**（テスト強度 Minor conf7）: 書込み経路は gate 非依存（同一 sed・GATE_REF_KEY だけ相違）で、live 実行には client artifact 一式（C-3 sentinel 検査）の重量 fixture が必要。iter69/70 スイープ（drill/テスト強化テーマ）で拾う。
- **構造ピンの裸文字列（"JUDGE CARD" 等）の脆さ**（テスト強度 Minor conf7）: tripwire として意図的な設計（iter55 token-pin と同型）。誤トリップ時のコストは小。
- **ACK_SET/ACK_RECORD 命名**（保守性 Minor conf6）・**条件式の文字列重複**（Minor conf6）: 機能影響なし・次回同ファイル改修時に統合。
- **`--ack` と `--ref` の順序逆転テスト**（提案）: parser はループで順序非依存（構造上自明）。
- **変異(i)のコメント経路ズレ**（テスト強度 Minor conf6）: pre-write sanity 削除時の実障害モードがコメント想定（部分失敗）と異なる可能性の指摘。fixture 本番同型化（T-2 修正）後は sed 範囲が閉じるため素通り経路自体が変化。検知（rc≠0）は維持されており、動作契約に影響なし。

## 親 verify（fable）実測 evidence

1. F-1 単離再現: `frontmatter_section | grep -q`（trap '' PIPE 下・3000回）→ **偽 fail 58/3000** {action: scratchpad で単離ループ, expected: 反対仮説どおりなら 0, observed: 58, verdict: 反対仮説棄却＝F-1 実在}
2. 修正形検証: case インメモリ判定 **0/3000**＋負例（不在 key 不一致）＋4スペース行の誤マッチなし／CURRENT 全量読み形 **0/3000** {verdict: PASS}
3. S-1: `grep -n update-gate.sh .claude/skills/ship-and-docs/SKILL.md` → `dev_ready_for_client approve`（ref なし gate）のみ {verdict: スキップ正当}
4. fix-forward 後: 対象テスト 54 passed・full suite **1170 passed / 2 skipped**・`check_framework_contract` **PASS** {verdict: PASS}

## Evidence Checklist

- [x] diff を Read/Grep で実読した（親: update-gate.sh 全文・check_status.py diff・テスト・guidance。4角度: 各担当範囲）
- [x] plan/spec の受入条件と突合した（仕様準拠レビュー 項目1-4＋親対照）
- [x] 未カバーのエッジケースを列挙した（繰延リストとして記録）
- [x] 全 finding に severity と confidence を付与した（conf<7 は注意書き扱い）

## 総合判定: **PASS（approve）**

- Critical 0。Major 3（F-1/T-1/T-2）は全て本フェーズ内で修正・実測検証済み。Minor は修正済み6件＋理由付き繰延5件。
- F-1 は「罠根絶」テーマの実装が新しい 0.6〜2% 級の flaky 罠を持ち込みかけた事案であり、敵対レビュー（実証主義）が設計者の机上安全主張を覆した——プロセスが意図どおり機能した。
- pre-existing の F-2 は SF-013 として分離起票（iter67 教訓 line155 の「差分実走で回帰でないことを確定→gate approve＋SF 分離」パターン適用: baseline reset の null 化 sed と同一範囲パターンであることを敵対レビューが確認済み）。

## 盲検2次（self-attested）

1次確定後・fix-forward 済み状態（1956ac1）に対し、1次結論非開示の fresh エージェント（fable・reviewer・qa-reports 読取禁止）で独立実施。結果は **reject**（正常系・SIGPIPE 根治・guidance 整合は「堅牢」と評価しつつ、新規 Major を実証）。

### 盲検2次 findings と処置

| # | Severity | Conf | 内容 | 処置 |
|---|---|---|---|---|
| 4-A | **Major** | 9 | `sed > "$TMP" && mv …` は bash の **AND-OR リスト errexit 免除**により書込み失敗（権限・ディスク満杯）でも abort せず、`[gate-approve] … → approved`＋`updated` の**偽成功出力＋exit 0** に化ける（scratch で chmod 555 実証・3経路とも後続到達）。本 iter が立てた STATE-FIRST 不変条件の反例（機構は baseline から pre-existing だが不変条件を掲げた本 diff のスコープ内欠陥） | **修正済（review 内 fix-forward）**: TDD RED（chmod 555 で exit 0 を確認）→ 明示 `if !` 分解で fail-closed 化＋TMP 削除＋回帰テスト `test_write_failure_fails_closed_no_false_success`（rc≠0・STATUS 不変・承認主張出力ゼロ）→ GREEN。spec §エラーハンドリングの誤記述（「set -e で abort」）も訂正 |
| 3-1 | Minor | 9 | trap 構造ピン `assertIn("trap '' PIPE")` は監査コメント中の同一文字列でも通る＝実コマンド削除を検知できない（mutation 実証） | **修正済**: 行アンカー正規表現 `(?m)^\s*trap '' PIPE\s*$` へ差し替え |
| 4-B | Minor | 6 | --ref が repo 内シンボリックリンク経由で repo 外実ファイルを指せる（`-f` はリンクを辿る）。single-user・ref は非実行の証跡ポインタ・tamper writer 前提で実害限定 | **記録して繰延**（realpath 包含チェックは YAGNI 気味との2次自身の評価に同意。SF-013 の sed 範囲 hardening と同時に iter69+ で検討） |

1次との相違点: 1次（敵対バグ角度）は書込み**成功後**の出力経路と EPIPE レースに深く、**失敗経路**の errexit 免除は未検出。盲検2次が独立に掘った（盲検の分担価値が実証された形）。逆に 1次の F-1（EPIPE レース）は2次は「再導入なし」を確認したのみ＝相互補完。

```claims
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["4-A: sed&&mv の errexit 免除による書込み失敗 fail-open（1次未検出・Major・初回 verdict=reject の根拠・fix-forward c42af84 後に同一エージェント再検証で根治実測＝rc1/STATUS不変/偽出力ゼロ・回帰テストの RED 検証まで確認）", "3-1: trap 構造ピンのコメント欺瞞（行アンカー化で修正・mutation 再実行で検知確認）", "4-B: --ref symlink 越境（Minor conf6・両者合意で iter69+ 繰延）"]
resolution: "初回 reject（4-A 根拠）→ fix-forward c42af84 → 同一エージェント再検証 approve_with_notes に収束（183 passed・contract PASS 実測）。"
```

## 追補: ドッグフード発見ギャップ（judge × 原子承認）

review gate を本 iter の成果物 `approve --ref` で承認しようとした時点で発覚: judge（build-judge-card）は claims を `current_refs.<gate>` からのみ読むため、原子フローでは pre-approve 時 ref=null → **judge gate の黄金経路が常に「claims 無し 🟡」＋ack** になり、ack が常態化して evidence 規律を汚す。

- 処置（review 内 fix-forward・TDD RED→GREEN）: `resolve_gate_report` が `AEGIS_PENDING_REF`（update-gate が実在検証済みで export し同一書込みで確定する path）を claims 源として尊重する 1 分岐を追加。tier-1 facts（fp/tests）は不接触＝信頼モデル無変更（claims はもともと self-attested）。ref key を持たない gate は env があっても None（update-gate 側の --ref 拒否と整合・テストでピン）。
- テスト: `test_pending_ref_env_overrides_null_ref`／`test_pending_ref_env_ignored_for_refless_gate`（tests/test_judge_card.py）。

## 最終判定（fix-forward 後）: **PASS（approve）**

4-A/3-1＋judge ギャップ修正後: full suite **1173 passed / 2 skipped**・contract PASS。Critical 0・Major 4件（F-1/T-1/T-2/4-A）全て本フェーズ内で実測検証付き修正済み。
