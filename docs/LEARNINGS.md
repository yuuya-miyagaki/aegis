# 蓄積された教訓

> このファイルは Claude Code 向け運用から得た durable learning を残すための場所です。
> 一時的な作業メモや会話の要約ではなく、次回以降に再利用できる学びだけを残します。

## 技術

<!-- category: tech -->

- [confidence:8] `CLAUDE.md` は薄く保ち、詳細ルールは pull-based にした方が Claude Code では安定しやすい。

## プロセス

<!-- category: process -->

- [confidence:9] `docs/STATUS.md` を短い状態ファイルとして維持すると、再開時の迷いが減る。
- [confidence:8] `docs/plans/` の設計書（design）は決定の正典として durable に保ち、必要なら更新する。実装計画（implementation）は実行時点のスナップショットとして commit するが、マージ後は更新しない（行番号・厳密文字列が陳腐化し将来の読者を誤誘導するため）。design＋implementation＋git 差分＋親設計の §チェックリスト反映で「決定・手順・差分・追従」が揃う。

## コミュニケーション

<!-- category: communication -->

- [confidence:8] gate 承認は会話中で曖昧にせず、明示的に記録した方が後続の判断がぶれない。

## フレームワーク改善

<!-- category: framework -->

- [confidence:7] specialist を増やす前に、token と routing の実利があるかを確認する。
- [confidence:8] agent の skills preload を追加する際は profile 定義（templates/profiles/*.json）も同時に更新しないと scaffold drift が起きる。
- [confidence:8] MCP テンプレートは npx に `-y` フラグを付けないと初回起動時の対話プロンプトで止まる。ワークスペース内の既存例に合わせること。
- [confidence:8] settings の hook コマンド形式を変えるときは、それを解析する全消費者（bin/setup.sh の抽出、check_framework_contract の参照解決、eval_scaffold_smoke の判定、test_hook_required_coverage の regex）を同時に更新する。v1.4.0 の `"${CLAUDE_PROJECT_DIR:-.}"` 化で contract の参照解決が 16 件 FAIL し、共有ヘルパー（script_rel_from_command）で恒久対応した。
- [confidence:7] extensions/ に配置する設定テンプレートは、実サーバー接続検証まではスコープに含めにくい。構造検証と実接続検証を明示的に分けて記録すべき。
- [confidence:9] `update-gate.sh` は `current_refs.<gate>` を "approved" 文字列で上書きする。ゲート承認後に手動で正しいファイルパスを復元する必要がある。将来のバージョンで修正すべきバグ。**→ v1.4.0 で解消**: 単一パス書込（P3-3）により approve は current_refs に触れなくなった（reset の null 化は仕様）。v1.4.0 の 4 ゲート承認で refs 無傷を実証。
- [confidence:8] contract validator のエージェント構造チェック（hallucination guard, turn limit）は大文字小文字を区別する。"Do not" ではなく "do not"、"Complete" ではなく "complete" で書く必要がある。
- [confidence:8] standard profile は Dev-lean に保つべき。Client 専用 artifact（docs/client/, docs/translation/）を standard に含めると、対応する skill/agent なしでは不整合になる。Client 機能は full profile に集約する。
- [confidence:7] 大規模変更（L サイズ）の実装は Phase 分割+並列サブエージェントが効果的。v0.8.0 では 18 タスクを 6 フェーズに分割し、各フェーズ内で最大 5 並列実行した。
- [confidence:9] B1 テスト強度ドリルは framework タスクの混在 diff に構造的に適用不能（v1.3.3 で実証）: (1) L サイズの未コミット diff はハンク数が MAX_MUTANTS=25 を超えやすい（38 ハンク）、(2) coverage floor が docs/STATUS.md 等の簿記ハンクにも mutant を強制するが、テストは fixture ベースのため捕獲不能＝必ず FAIL。設計 §11 のスキップ宣言で回避したが、恒久対応の候補は「coverage floor から docs/** を除外（DRILL_ARTIFACT_PREFIX と同型）」「対象ファイルの opt-in スコープ指定」。次バッチ（P2/P3 群）で改善を検討。**→ v1.4.0 で恒久対応済み**: run-test-strength-drill.py が docs/** を mutant 生成と coverage floor の両方から除外（DRILL_EXCLUDED_PREFIXES）。
