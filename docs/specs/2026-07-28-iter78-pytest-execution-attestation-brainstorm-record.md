# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-28（iter78）

## テーマ

- pytest execution attestation — テスト実行証跡を「出力テキストの marker 解析」から「argv spawn＋構造化イベント」の positive proof へ一本化する（roadmap＝`docs/full-review-2026-07-19-dual-codex-fable.md` §5 行77）

## コンテキスト

- 現在の状況: iter77（SF-020/021 封鎖・v1.31.4）完全クローズ。evidence 層の green 証明は全て**出力ベース**（`hooks/lib/marker.sh` の 6-stage 出力解析）。SF-014/SF-022 が実証した通り、denylist（NO_RUN flag / fail-token 語彙）と出力 marker は原理的に不完全（LEARNINGS conf9）: fake 出力・echo-class・reporter 妨害・exit 洗浄は列挙で塞ぎ切れない。SF-015（all-xfail 偽陰性）も出力解析の粒度限界。
- きっかけ: full-review §5 が iter77(=繰延で iter78)を P0/P1「pytest execution attestation」と指定。完了条件＝「argv spawn＋structured event（executed/passed/failed/skipped/collection_error/exit）・`src=attested` のみ decisive green・fake 出力は event 不能」。judge には iter76 時点で `A future legitimate src (e.g. "attested", iter77) must be added HERE` の前方コメント済み（`build-judge-card.py:334`）。

## 検討したアプローチ

### アプローチ A: pytest カスタムプラグイン attestation（採用）

- 概要: 新 CLI `scripts/attest-test-run.py "<pytest cmd>"` が (1) コマンドを検証（pytest family 限定・シェル演算子/エンジェクション拒否）、(2) **shell なし argv spawn** で pytest を起動し `-p aegis_attest_plugin`（新規 `scripts/aegis_attest_plugin.py`・stdlib のみ）を注入、(3) プラグインが構造化イベント（collectreport / runtest_logreport / sessionfinish）を attestor 指定のイベントファイルへ JSONL 書込、(4) attestor が waitpid の実 exit code とイベントを突合して verdict を計算し、`src:"attested"`＋実数カウントで evidence-log に記録。judge は src allowlist に `attested` を追加し、**pytest family の decisive green を attested のみに制限**（observed/manual の pytest 'ok' は transparent skip）。B1 drill への統合は roadmap 行78（次 iter）に分離。
- 利点: (a) 子プロセスの stdout/stderr を**一切パースしない**＝fake 出力は構造的に不能（echo-class 全滅）。(b) shell を経由しない＝exit 洗浄（`; true`）が入力段階で不能。(c) call-phase イベントの実数計数＝zero-run/all-skip の positive proof（NO_RUN denylist 不要）＋ all-xfail 偽陰性（SF-015）も attested 経路で解消。(d) roadmap 完了条件のイベント語彙と 1:1 対応。(e) stdlib のみ・外部依存ゼロ。
- 欠点: (a) pytest 限定（他ランナーは marker 経路のまま＝文書化残余）。(b) in-process 妨害（conftest でのプラグイン無効化・イベント偽造）は残る（下記「残余天井」）。(c) judge の pytest green 制限で既存テストの一部が契約変更（書き替えを明示管理）。

### アプローチ B: pytest 組み込み `--junit-xml` の解析

- 概要: プラグインを書かず、attestor が `--junit-xml=<path>` を注入して XML を解析。
- 利点: 注入物が少ない（pytest core 機能のみ）。
- 欠点: (a) イベント語彙が roadmap 完了条件（executed/collection_error 等）と一致せず、xfail/エラーの意味論が XML スキーマ越しに不明瞭。(b) XML は最後に一括書込＝クラッシュ時の部分証跡なし。(c) 残余天井は A と同一（ファイル偽造可能性は同等）で利点が薄い。→ 不採用。

### アプローチ C: 全ランナー strict（attested 以外は green 不可）

- 概要: judge の decisive green を全面的に src=attested のみとする。
- 利点: 最も強い一貫性。
- 欠点: 非 pytest エコシステム（jest/go/cargo/unittest…）の green が全て 🟡 化し配布先を即破壊。roadmap §6 が「全 test ecosystem の同時 adapter」を明示的に却下（Aegis 自身の pytest から始める）。→ 不採用。

### 併せて却下

- 署名/HMAC による擬似 attestation: 同一ユーザー権限内では trust boundary が増えない（roadmap §6 で両者一致却下）。
- record-test-result.py への attestation 内蔵: record は汎用ランナー契約（marker 経路）の正本。責務混在よりも「pytest は attest へ誘導（rc2）」の単方向リダイレクトが単純。

## 決定

- 採用アプローチ: A（pytest カスタムプラグイン attestation・judge の pytest-family green 制限つき）
- 採用理由: roadmap 完了条件と 1:1・出力非依存の構造保証・依存ゼロ・scope が M に収まる（新規 2 src＋judge/record 改修）。
- 不採用理由: B はイベント忠実度と部分証跡で劣り天井は同じ。C は roadmap §6 違反・配布破壊。

## スコープ境界

- IN: attest CLI＋plugin 新規、judge（src allowlist＋pytest green 制限）、record（pytest family rc2 誘導）、scripts-manifest 登録、qa-verification skill の手順更新、差分 pin（旧緑/新赤 differential 含む）。
- OUT（明示繰延）: B1 drill の attestation 統合（roadmap 行78・次 iter）、非 pytest ランナーの adapter（§6 却下）、evidence-log 自体の改竄防止（HMAC・§6 却下）、hook observer 側の attestation（observer は受動観測のまま）。

## 残余天井（正直な限界主張・実証方針つき）

attestation が**構造的に閉じる**もの: (1) fake 出力（出力を読まない）、(2) exit 洗浄（shell 不在）、(3) zero-run/all-skip/collect-only（call-phase 実数）、(4) fail-token/NO_RUN denylist treadmill（positive proof 化）。
**残る**もの（いずれも pre-existing 天井と同クラス・非拡大）: (a) in-process 妨害＝conftest.py がプラグインを unregister/イベント偽造（echo-class の構造版）、(b) evidence-log への手書き偽造エントリ（既存 manual と同一）、(c) fake pytest バイナリ（PATH 差し替え）。全て「自分の qa gate を欺く」故意行為で、多層（drill・人手プレビュー・fingerprint）で contained。(a) は fail-closed 側（プラグイン死＝イベント欠落＝green 不能）に倒れることを pin で実証する。

## 未解決事項（plan で確定）

- judge の pytest green 制限で契約変更となる既存テストの列挙と書き替え方針（削除ではなく契約更新として1件ずつ記録）。
- attest 実行の timeout・イベントファイル置き場（`.claude/` 配下 tmp）の細部。
- 版数: 公開契約追加（新 CLI・judge 挙動変更）につき MINOR（v1.31.4→v1.32.0）想定。
