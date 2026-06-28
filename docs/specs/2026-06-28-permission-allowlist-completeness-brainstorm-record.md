# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-28（iteration 52）

## テーマ

- 確認(permission prompt)交通整理の継続。allow-list を **read-only 完全性ガード＋拡張**で前進させる。

## コンテキスト

- 現在の状況: iter51 で安全な read/record 系コマンド 10 件を `permissions.allow` に同梱（全プロファイル一律）。残る一次痛＝「確認が多い」（author の一次痛）と「知識の乏しい人には技術的確認が理解不能」（North Star ペルソナ）。
- きっかけ: iter51 close 後の rollover。当初候補 slice2「確認の平易化」を grill-premise でグリル → 非実在ユーザー向け＆検証不能で却下。対抗馬「プロファイル別 allow」も掘ると価値が薄く論争的と判明し、read-only 完全性へ再収束。

## 検討したアプローチ

### アプローチ A: slice2「確認の平易化」（hook で承認時に平易な根拠を添える）

- 概要: permission prompt 前後に grill/scrutiny 結果を平易な言葉で添え、知識の乏しい人が判断できるようにする。
- 利点: North Star に直結。`emit_ask`（`permissionDecisionReason`）で reason 注入の足場は実在（実証済み）。
- 欠点: **致命的＝ターゲットユーザーが今いない**（solo author・配布は将来）。「どこまで平易なら理解できるか」を観測できず憶測になる＝**検証不能**。症状（文言が難しい）と原因（そもそも判断させている）の取り違え。→ 却下。

### アプローチ B: プロファイル別 reversible-write allow（guard-coverage 連動）

- 概要: 許可の寛容さ＝導入済み guard hook 量で決め、standard/full に reversible-local（`git add`/`commit`/`stash` 等）を auto-allow。
- 利点: 原理が一貫・moat 保全（destructive hook が危険変種を `emit_ask` で依然プロンプト）・author が判断可能。
- 欠点: 解禁するコマンド群に価値が無い。`git commit`/`add` は **author の方針「コミットは必ず人が制御」に反する**（safety でなく oversight の問題で guard-coverage では解けない）。残る `mkdir`/`touch` は頻度が低く旨味薄。新 infra（profile 別 allow）が必要。→ **延期**（実在の第2 audience と「摩擦 vs 見届け」の具体トレードオフが出てから）。

### アプローチ C: read-only 完全性ガード＋拡張（採用）

- 概要: iter51 で漏れた**読み取り専用 framework スクリプト**（`check_reference_drift`/`context_budget`/`learnings_search`/`lint_names`）と安全 git-read（`git show`）を allow に追加。さらに iter49/50 と同じ**参照整合性ガード**として、「全 read-only スクリプトが allow に在る／全 mutating スクリプトは allow に無い」をテストで強制し drift を防ぐ。
- 利点: 全員に安全（read は mutate しない＝moat 無関係・profile 分け不要）。論争ゼロ。author の一次痛に直撃しつつ初心者にも効く（North Star）。**drift しない durable guard**。
- 欠点: 価値は「もっと多くの安全 read を無プロンプト化」に限定（write 系の摩擦は残す＝意図的）。

## 決定

- 採用アプローチ: **C（read-only 完全性ガード＋拡張）**
- 採用理由: (value × validatable ÷ risk) が最大。read-only は今すぐ author が分類でき・テストでき・moat リスクゼロ・commit oversight の論争も無い。承認済みゴール「確認を減らす」を一回限りの追記でなく anti-drift 契約で実現。
- 不採用理由: A=非実在ユーザー・検証不能。B=価値が薄く commit oversight と衝突、profile infra は時期尚早。

## スコープ境界

- やること: (1) 分類表（scripts → read_only_cli / mutating_cli / not_cli）。(2) 完全性ガードテスト（drift trip 付き）。(3) allow 拡張＝read-only スクリプト 4 件＋`git show`。(4) README allow 節更新。全プロファイル一律（generate_settings 変更不要）。
- やらないこと: profile 別 allow、reversible-write（`commit`/`add`/`mkdir`/`stash`）、`Edit`/`Write`/MCP 自動 allow、exec/eval 系スクリプト（`record-test-result`/`run-test-strength-drill`/`run_eval`/`eval_*`）、destructive 副形を持つ `git branch`/`git remote`/`git checkout` の broad allow。

## 未解決事項

- 各 read_only_cli スクリプトが真に read-only（ファイル書込み・サブプロセス exec sink 無し）かを implement で静的に確認し、分類表に根拠を残す。
- 完全性ガードを既存 `tests/test_permission_allowlist_install.py` に追記するか新ファイルにするか → plan で決定。
- allow エントリの matcher 形（`Bash(python3 scripts/<name>.py:*)`）の一貫性。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-28-permission-allowlist-completeness-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->
