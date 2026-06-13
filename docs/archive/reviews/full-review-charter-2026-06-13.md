# 全力レビュー charter（第6回・2026-06-13、対象 v1.6.1／HEAD `2ac5eb6`）

## 目的

v1.6.1（HEAD `2ac5eb6`、第5回の C-1〜C-9 大半を含む 13 コミット）の aegis を、過去 5 回のレビューと**重複しない 6 軸**で並列精査し、

1. v1.6.1 の修正が**本当に穴を塞いだか**（攻撃側からの独立再 PoC）
2. 過去 5 回が**機能空間に偏っていた**ため**手薄な運用空間**に未踏所見はないか

の 2 段で「全力で疑う」。所見は次の改善サイクル（v1.6.2／v1.7）の入力。

## 過去レビューとの差別化（重複禁止リスト）

| 回 | 日付 | 軸 | 出典 |
|----|------|-----|------|
| 1 | 2026-06-06 | 機械契約→哲学の 2 層監査＋最新フレーム web 調査 | docs/audit-report-2026-06-06.md |
| 2 | 2026-06-07 | 機能整合性（install 経路の死角） | docs/functional-integrity-audit-report-2026-06-07.md |
| 3 | 2026-06-10 | 哲学×Web比較×欠陥監査の 3 軸 | docs/evolution-review-2026-06-10.md |
| 4 | 2026-06-11〜12 | 行動レビュー（実運転検証） | docs/behavioral-review-report-2026-06-12.md |
| 5 | 2026-06-12 | 敵対バイパス／保守性／北極星 UX／arch drift／エコシステム現行性の 5 軸 | docs/full-review-2026-06-12.md |

上記で解決済み・受容済みの事項（v161-* 受容残余を含む）の再報告は**ノイズとして禁止**。新規所見のみ。

## v1.6.1 の修正コミット（Phase A の再 PoC 対象）

| Commit | 対応 | 修正対象 |
|--------|------|---------|
| `073c477` / `a273edb` | C-9 | secrets-patterns 単一所有 lib + check-secrets ルート |
| `135fc6b` / `2001a6a` | C-1 / A-Crit-1 | 変数展開 control-plane 書込 deny |
| `1587a69` / `4a27b09` | C-2 / A-Crit-2 / B-Critical | test-marker sentinel 要求＋no-run flag guard |
| `9a111df` | C-3 | client 6 成果物 sentinel + ≥200 バイト |
| `b4d5543` | C-4 | SessionStart matcher に `resume` 追加 |
| `c282d3d` | C-5 / C-6 | arch-overview の hook/lib/drift カウント・user-invocable 修正 |
| `00ae7b5` | S-11 | phase-skills.sh / secrets-patterns.sh を REQUIRED 登録 |
| `ce82c55` / `f0eb9ac` | S-3 / A-Crit-4 / A-S4 | git --git-dir / -C / stage / update-index / GIT_PRE_OPTS の .env 阻止 |

## 今回の 6 軸

### 軸A（締め）: v1.6.1 独立再検証
v1.6.1 に入った 13 修正の**回帰検証＋攻撃側 PoC**。修正が「regex の隙間」「環境変数の別ルート」「fast-path 復活」「テストの偽 marker 通過」等で**穴を残していないか**を、コミット差分・テスト・周辺コードを横断して再構築。CI green は信用せず、PoC を構築して試行。

### 軸C1（未踏）: 障害モード / 復旧
- hook が exec 失敗（permission denied / interpreter 不在 / signal）した時の挙動
- hook timeout / Claude Code のタイムアウト挙動
- emit.sh crash / patterns.sh source 失敗
- ディスク full / read-only fs / `.git/index.lock` 残存
- STATUS.md 破損・gate-snapshot 欠損からの自動復旧
- session-recovery skill の出口

「fail-open / fail-closed」ポリシー（`docs/hook-failure-policy.md`）と実装の一致を中心に。

### 軸C2（未踏）: パフォーマンス / スケール
- hook 1 回あたりの実測遅延（特に check-control-plane / check-secrets / patterns.sh）
- 508 tests・実走 130s 超の 3 年後（テスト数線形成長＋ロック sleep の累積、CI コスト）
- リポ成長（docs / qa-reports / evidence-archive の蓄積）と grep / glob のスケール
- emit.sh の JSON 構築コスト、bash 多用の cold start

第5回 C-7 は既知。**そこから先の波及・再発系統**を抜く。

### 軸C3（未踏）: 配布パス（setup / upgrade / 衝突）
- `setup.sh` を**既存 .claude を持つプロジェクト**に当てた時の衝突挙動
- 中断・再実行（partial install）からの一貫性
- アップグレード（v1.5.x → v1.6.1）の経路と差分適用
- 例: ユーザがテンプレを手で改変していた／hook を追加していた時の挙動
- examples/minimal-project の役割（mirror or starter）と setup.sh の意図整合
- bin/aegis-doctor 系の自己診断粒度

### 軸C4（未踏）: 競合 / 借用余地
- superpowers（特に brainstorming / writing-plans / TDD / subagent-driven-development の trigger description 品質と起動経路）
- gstack（ETHOS preamble / 31 skills / Bun-TS の workflow）
- cursor rules / windsurf rules（プロジェクトルール伝播）
- aider（CONVENTIONS.md / repo map）
- antigravity-kit（multi-agent templates）

aegis に**取り込んだら北極星に効く差別点**と**既に aegis 優位な点**を分けて提示。

### 軸C5（未踏）: 非エンジニア E2E ジャーニー（実演）
README → setup → onboarding → Client phase → 6 成果物 → handover → Dev phase → QA → deploy → 保守ループ を**非エンジニア視点でなぞり**、各継ぎ目の摩擦・離脱点・誤誘導を列挙。第5回 T4／S-16〜S-19 は既知。**実走ジャーニーで新たに見えた継ぎ目**のみ。

## 方法

- 軸ごとに独立サブエージェント（互いの所見を見ない）。Phase A と Phase C は並列。
- 読み取り専用（repo 変更禁止。/tmp への scaffold 実行・実 PoC は可）
- 所見は `file:line` ＋根拠＋修正方針、重大度 🔴（防御破綻・北極星阻害）/ 🟡（要修正）/ 🟢（任意）
- **監査と再設計の分離**: 本レビューは所見の提示まで。修正の実施・優先順位の確定は別途ユーザー判断

## 成果物

- 統合レポート: `docs/full-review-2026-06-13.md`（軸別所見＋横断テーマ＋優先順位付き提案バックログ）
- 各サブエージェントの raw 所見は統合レポートに inline 引用
