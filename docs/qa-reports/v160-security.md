# v1.6.0 fix-forward P1×4 バッチ — security エビデンス（2026-06-12）

## 位置づけ

behavioral-review-report-2026-06-12 §5.1 の P1×4 是正バッチ。行動レビューが実証した
「後半フェーズの正規機械全滅 → LLM 即興代替」（skill 起動不能 × テンプレ未配布 ×
Client ゲート無検査）を決定論側の構造で封鎖する。

## 防御強度の変化点と評価

| 変更 | 方向 | 評価 |
|------|------|------|
| P1-A: phase 必読 skill の SessionStart／phase 遷移注入 | 可視化・構造起動（advisory） | 注入は `hookSpecificOutput.additionalContext` のみ＝deny/block 系の出力経路は不変。未対応クライアントでは注入が消えるだけ（fail-safe）。`hooks/lib/phase-skills.sh` 不在時は source で死ぬ＝emit.sh/patterns.sh と同じ「lib 不在＝install 不全＝fail-closed」ポリシーに整合 ✅ |
| P1-A: skill 到達性チェック（drift＋install 先 smoke） | 契約化（vacuous-green 封鎖） | 「起動経路のない skill」を機械検出。存在マニフェスト（check_framework_contract.py）の root 化除外（`SKILL_REF_EXCLUDE`）と names regex の非コメント行 anchor（grill S1、a8411fb）で、検査が恒久 CLEAN 化する false-negative 経路を 2 系統とも封鎖。いずれもテストでピン ✅ |
| P1-B: templates 配布＋参照実在の契約化 | install 死角封鎖（F6 級） | repo 静的（drift）と install 出力（smoke）の二重契約。skill が参照するテンプレ不在は機械 FAIL ✅ |
| P1-C: scanner の decode 耐性 | 可用性（fail-closed 維持） | バイナリ混在 repo で crash → 該当ファイル skip。skip は分類対象の縮小＝unverified 方向であり green 偽装には使えない ✅ |
| P1-C: judge card のゲート承認時 transcript push | 可視化強化 | push は承認経路（🟢／🟡+ack）で決定論実行。deny 経路（🔴／ack なし 🟡）は従来どおり exit 1＋🟡理由列挙＝防御不変 ✅ |
| P1-D: client_ready_for_dev の 6 成果物検査（承認側＋完了側） | fail-closed 方向の強化 | 承認時 pre-approve と完了時 evidence integrity の対称検査。検査追加のみで緩和なし ✅ |
| drill の vendor/build 区画恒久除外 | scan 縮小（補償あり） | vendored コード内の stub/secret は drill/judge の走査対象外になるが、judge card は advisory 層。秘密情報の書込時点では `check-secrets.sh`（deny 系・未変更）が独立に効く。`dist`/`build` 等は深さ問わず除外のため `src/dist/` の名前衝突も対象外（境界はテストでピン・false-OK 方向のみ） |

## 受容済みリスク（設計上の明示トレードオフ、今回記録）

1. **PostToolUse additionalContext のクライアント依存**: phase 遷移注入は未対応クライアントで無視される。fail-safe（deny/block 不変）。SessionStart 注入が冗長カバー
2. **JUDGE_GATES の二重定義**: update-gate.sh（bash）と check_status.py で判定対象ゲートが別々に列挙。drift 非検査。クロス参照コメントで運用（bash から python の import 不可）
3. **same-turn ack の LLM 層残余**: /gate のカード提示→確認の並びは手順であって強制ではない。card push（承認時の決定論提示）が実質補償
4. **judge card の double-render と ACK 行の揮発（grill B-S3 で補強）**: /gate プレビューと承認時 push の間で評価系出力が変化すると差分が出うる（低頻度・push 側＝記録が正）。`## ACK` 追記はカード再生成（build-judge-card 再走）で消える — **transcript 記録が正・ファイル側は揮発**。builder 側での ACK 保存は v1.6.1 検討
5. **到達性チェックは静的・path 形式限定**: 動的に組み立てた path（変数展開）は edge として見えない。phase map root は `names="` パース契約（phase-skills.sh ヘッダコメント）で結合 — v1.6.0 で非コメント行 anchor に強化済み。書式変更時は両方を直すこと
6. **template 参照チェックは `templates/*.template.md` 形のみ**: 別形式の参照は regex に掛からない。標準形を保つ運用前提
7. **制御ファイル内コメントの false-root**: 到達性チェックは hooks/scripts のコメント中の skill path 文字列も root として扱う（過剰許可方向のみ）。「制御ファイルに skill path を書く＝起動経路を宣言する」を規約とする（names= 例文の偽 root 化は S1 で封鎖済み・skill path 形のコメントはこの規約の対象）
8. **🔴／ack なし 🟡 経路では card 全文は push されない（grill B-S2、v1.6.1 検討）**: 設計契約は「承認時 push」。deny 経路でも GATE_CHECK の 🟡/🔴 理由列挙は transcript に出る（実測確認）
9. **judge card push の 🟢 経路は mutation 未ピン（grill B-S4、v1.6.1 送り）**: push は tri-state 判定後の共通枝にあり 🟢/🟡 両経路で実行されるが、テストは 🟡(--ack) のみピン。🟢 化には test 記録/claims/第2意見の staging が必要なことを probe 実証済み（fixture brittle 化回避のため次版で record-test-result 系 fixture と合わせて追加）

## 残余リスク

新規の fail-open 方向の残余なし。本バッチは追加・強化のみで deny/block 系の緩和ゼロ
（grill A が gate-tamper / phase-skip / mode-tamper / placeholder contract の hook 実走無傷を独立確認）。
上記受容済みリスクはいずれも advisory／unverified／可用性方向（green 偽装・deny バイパスには使えない）。

## 検証

- 508 tests OK / contract 本体+example PASS / drift（到達性込み）PASS / scaffold smoke 3 プロファイル PASS（install 先到達性＋テンプレ参照込み）/ tier 0/1/2/3 PASS / check_status --strict PASS
- 検出力の負実証: 壊した install（唯一 root の削除）で到達性 FAIL 1 件、存在マニフェスト偽 root・コメント例文偽 root の 2 系統は RED→GREEN テストで封鎖
- grill-code 独立 2 本（A: マージ可 / B: S1 修正後マージ → 充足）の詳細は v160-review.md
