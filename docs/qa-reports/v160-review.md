# v1.6.0 fix-forward P1×4 バッチ — review エビデンス（2026-06-12）

対象: behavioral-review-report-2026-06-12 §5.1 の P1×4（P1-A skill 到達性 / P1-B templates 配布 / P1-C judge card crash+push / P1-D Client ゲート対称検査）。v1.5.2..HEAD の実装コミット群（Task 1〜15）。
出典: docs/plans/2026-06-12-fix-forward-p1-implementation-plan.md（grill-plan 独立 2 本反映済み）
方式: 2段グリル実装段（grill-code）。独立サブエージェント 2 本（A/B とも opus・互いの所見を見ない）で差分全体を file:line 裏取り・実測検証付きで精査。

## レビュー結果

- **A**: 🔴0・🟡3・🟢3 → マージ可
- **B**: 🔴0・🟡4・🟢3 → 修正後マージ（S1 のみマージ前推奨）

両者の合流点 S1（=A🟡1）は同セッションで充足済み（commit `a8411fb`）。

| ID | 指摘 | 対応 |
|----|------|------|
| A🟡1 / B-S1 | `PHASE_MAP_NAMES_RE = r'names="([^"]*)"'` が phase-skills.sh のヘッダコメントを横断マッチし偽 root を量産（実測 49 トークン中 33 個がゴミ）。現状は `name in skills` 交差で fail-safe だが、コメント例文に実 skill 名を書いた瞬間 false-reachable ＝到達性が恒久 CLEAN 化（vacuous green の再演リスク） | **修正済み**（a8411fb）。`^[^#\n]*\bnames="([^"\n]*)"` (re.M) に anchor — コメント接頭辞除外＋クォート内改行禁止。B 提案の `^\s*` 形は `implement) names="..."` 単行 case 形を取りこぼすため不採用。`test_comment_names_example_is_not_root` で RED→GREEN を実証（コメント中の偽 skill 名が root 化されないことをピン）。修正後の実 repo トークン集合＝実 skill 名 15 件ちょうどを実測 |
| A🟡2 | `SKILL_REF_EXCLUDE` の `path.relative_to(root)` と `Path` literal 比較は Windows/symlink 経由で不成立の可能性 | **不採用（理由付き記録）**: aegis の実行面は bash hooks 前提＝POSIX 限定。sources は全て `root / ...` から構成されるため relative_to は安定。Windows 対応は非要件 |
| A🟡3 | post-status-audit.sh の snapshot 更新コメントと P1-A 注入ブロックの読み順が misleading | **記録のみ**: コメントは到達時点の状態として正確（deny 経路は手前で exit 済み）。注入ブロック自体が P1-A の理由コメントを保持しており、誤読での挙動変更余地は小 |
| B-S2 | 🔴 / ack なし 🟡 経路では JUDGE CARD が transcript に push されない | **不採用（v1.6.1 検討として記録）**: 計画 Task 4（OBS-019）の契約は「承認時 push」。ack なし 🟡 でも GATE_CHECK の 🟡 理由列挙は transcript に出る（fixture 実測で確認）。提示経路は /gate Task 5 のプレビューが担う。deny 経路への push 拡張は挙動変更＝計画外のため次版で判断 |
| B-S3 | `## ACK` 追記はカード再生成（build-judge-card 再走）で揮発し「transcript に残るがファイルから消える」不整合 | **v160-security.md の残余 #7（double-render）補強として記録**: ACK は transcript 記録が正・ファイル側は揮発。builder 側での ACK 保存は v1.6.1 検討 |
| B-S4 | judge card push のテストが 🟡(--ack) 経路のみで、🟢 経路 push が mutation 未ピン | **後送（理由付き）**: git fixture でも tri-state は 🟡（テスト記録なし/claims 未提出/第2意見なし）と probe 実証。🟢 化には evidence 一式の staging が必要で fixture が brittle 化する。B 自身も v1.6.1 容認。次版で record-test-result 系 fixture と合わせて追加 |
| A🟢1 | update-gate.sh ↔ check_status.py の JUDGE_GATES クロス参照を双方向化 | 記録のみ（残余リスク #3 の既知事項。片方向コメントは実装済み） |
| A🟢2 | `aegis_phase_skill_paths` の `for n in $names` に IFS 局所化 | 記録のみ（names は names="..." リテラル由来でスペース区切りのみ。残余 #5 のパース契約に内包） |
| A🟢3 / B-N2/N3 | テスト可読性（replace 形）/ verify 関数の定義位置 / strict 出力の列挙形式 | 記録のみ（挙動影響なし） |
| B-N1 | phase map の Client 系フェーズが client-workflow 1 本で粗い | 記録のみ（到達性は充足。マップ細分化は将来の体験改善テーマ） |

## レビューの検証メソッド（両者の独立実証）

- **A**: /tmp scaffold で minimal/standard/full 全 profile の install 先 reachability CLEAN・templates 6 件配布を実測。deny 系（gate-tamper / phase-skip / mode-tamper / placeholder contract）を hook 実走で無傷確認。507 tests・tier 0/1/2/3・--strict・drift・mirror identity 全 PASS を再現
- **B**: PHASE_MAP_NAMES_RE の偽トークン混入を実機 re 実行で実証（S1 の根拠）。update-gate.sh の経路分岐（rc=0/2/1 × ack 有無）を行単位で追跡し push 到達条件を特定。bash 構文・mirror byte-identical・install 実配布を実測
- 実装側: S1 修正後に 508 tests OK・drift PASS・実 repo トークン集合 15 件を実測（本ドキュメント記載）

## 仕様との整合性（両レビュー一致）

- 計画 Task 1〜15 全充足（両者の Task 別判定表が全行 ✅/OK で一致）
- 計画乖離は 2 点、いずれもチェック強化方向: ① Task 13 で `SKILL_REF_EXCLUDE` 追加（check_framework_contract.py の存在マニフェストが全 skill を root 化し検査が空洞化するのを除外＋テストでピン。両レビューが妥当と評価）② tier 0 timeout 120→300s（スイート 479→508 tests への成長追従。コメントで理由固定）
- 付随修正: hook fixture への phase-skills.sh staging（Task 11/12 の lib 依存追加に伴う、c6e4937）

## 判定

**マージ可**（A: マージ可、B: S1 修正後マージ → S1 は a8411fb で充足、Critical 0）。最終状態: 508 tests OK・tier 0/1/2/3・--strict・drift・mirror identity 全 PASS（v160-qa.md 参照）。
