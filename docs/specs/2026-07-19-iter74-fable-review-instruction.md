# Aegis 網羅レビュー指示書（Fable 向け・独立盲検レビュー）

あなたは、`aegis` という Claude Code 用の開発フレームワーク／ハーネスの、**独立した盲検レビュアー**です。
このリポジトリ（あなたに与えられた物理隔離 clone）が丸ごとレビュー対象です。全力で、徹底的に、証拠ベースで批判してください。

**重要（盲検条件）**: あなたはもう一人の独立レビュアー（別モデル・外部エージェント）と**同一の層1チャーター**で並行レビューされ、出力が突合されます。相手の所見は見えません。突合の価値は「一致＝高確度」「乖離＝バグの在処」にあります。だからこそ、相手に合わせにいかず、**あなた自身が再現・実証できたことだけを、構造化して**報告してください。忖度や妥協した所見は突合を汚すだけで価値がありません。過去、1次 approve と盲検2次 reject の**乖離の場所にこそ High 級バグ**がいた実績があります（iter72 F-CRIT-1）。あなたはその盲検2次の役です。

---

## 0. 最初にやること（アンカリング）

1. **対象の固定**: このレビューの対象コミットは **`77566eda7d15cb70d6ca68377fdbd764834d6fe5`** である。`git rev-parse HEAD` がこれと一致することを確認せよ。**不一致なら中断し、その旨だけを報告せよ**（別コミットをレビューすると突合が無効になる）。`docs/STATUS.md` の `framework_version` も記録する。
2. **実行環境の記録（突合の生命線）**: 成果物の冒頭に、必ず次を記録せよ — OS（`uname -a`）／`grep --version` の1行目（**BSD か GNU か**）／`bash --version` の1行目／`python3 -V`／`locale`。locale/byte 次元の挙動は grep 実装に依存して変わるため、これが無いと突合時に「真の乖離」か「環境差」かを判別できない（作者の基準環境は macOS＝BSD grep）。
3. 作業ツリーを**汚さない**こと（§4 の制約を厳守）。read-only レビューである。
4. **fresh-first（アンカリング回避・特に重要）**: あなたは内部を熟知しているため既知に強く引っ張られる。下記「既知事項」を読む**前に**、まず白紙で1パス走らせ、「あなたが最も危険と見る経路 top3」を証拠つきで挙げ、成果物に `FRESH-1/2/3` として残せ。**その後に**既知事項を読み、known-map を作る。白紙 top3 が既知なら known-confirmed へ落とし、既知の外なら新規として深掘りせよ。既知の再確認は `known-confirmed` タグ1行で足りる。主眼は**新規発見**と**既知が本当に閉じているかの再攻撃**:
   - `docs/security-followups.md` — 脅威モデル（canonical）＋ SF-001〜016（OPEN/CLOSED/accepted residual の別を含む）
   - `docs/full-review-2026-07-06-six-dimensions-evolution.md` — 前回の6次元網羅レビュー（所見 R1〜R10 と外部比較・進化プラン）
   - `docs/LEARNINGS.md` — confidence 付き教訓ログ
   - `docs/STATUS.md` — 現状（iter73 まで。直近で locale/byte・marker/evidence 系の掃討が入っている。session_history に経緯あり）

---

## 1. Aegis とは何か（判定基準の土台・必読）

- **North Star（北極星）**: 「知識の乏しい人が、AI と一緒に、堅牢にソフトウェアを作って運用できる足場」を提供すること。現在は作者ソロでのドッグフード運用、将来は配布予定。
- **複雑さの許容基準は「作者一人が保守でき続けられるか」**。過剰な機構は北極星に反する負債である。
- **設計原理の3層**: 「保証＝決定論的に強制（フック/スクリプト）」「手順＝モデルに委譲（スキル/ドキュメント）」「揮発値＝隔離（manifest）」。
- **差別化資産（moat）**: tamper-evident gate（承認の改竄検知）／OS レベル file lock／evidence fingerprint／B1 mutation drill（テストの強度をミューテーションで検証）／盲検セカンドオピニオン。これらは調査済みの主要 OSS フレームワーク（superpowers・spec-kit・BMAD 等）に相当機構がない唯一無二の強み。**進化はこの軸を守り・磨く方向であるべき**。
- **運用モデル**: Claude Code ネイティブ。`CLAUDE.md`（操作契約）＋`docs/STATUS.md`（現在フェーズと次の一手）＋hooks（moat）＋skills（フェーズ手順）＋subagents。Dev フェーズは brainstorm→plan→implement→review→qa→security→deploy→ship→docs のステートマシンで、ハードゲートが遷移を律速する。

**判定は必ず North Star 基準で行うこと。** 「一般的ベストプラクティスだから」という理由だけの推奨（CI を足せ／型注釈を足せ／カバレッジを上げよ 等）は、**具体的な失敗シナリオ（再現手順つき）と North Star への影響に結びつかない限り、書くな**。ノイズは突合コストを増やすだけで害になる。

---

## 2. あなたのレビュー次元

### 層1: 共通コア（徹底的に・実証必須。もう一人と逐語同一のチャーター。ここでの乖離が最も価値を持つ）

1. **moat バイパス（最重要）**: enforcement（deny/ask/block）を迂回する新規経路を探せ。対象フックとライブラリ:
   - `hooks/check-destructive.sh`, `hooks/check-secrets.sh`, `hooks/lib/patterns.sh`（破壊/秘密パターン）
   - `hooks/lib/emit.sh`（出力スキーマ・pure-bash・fail-open しない設計になっているか）
   - `hooks/session-start.sh`, `hooks/lib/cp-lock.sh`（OS lock）, `hooks/lib/snapshot.sh`
   - コマンド抽出（extract_command 系）のクォート除去・トークン連結・glob・cmdsub・interpreter `-c`/`-e`・locale/encoding/生バイトによる分割/取りこぼし。SF-001〜005 の系譜の「続き」を探す姿勢で。
2. **SF 再裁定**: `docs/security-followups.md` の OPEN 全件（少なくとも SF-011/012/013/015/016）と、iter72 の F-CRIT-1（locale 依存 grep）を、**現行コードで再現を試み**、severity・exploitability・「accepted residual」の妥当性を再判定せよ。閉じたと主張されている項目（例: SF-014 の marker positive proof、iter73 の byte-wise 決定化）が**本当に閉じているか再攻撃**せよ。
3. **locale / encoding / byte（1次元として明示指定）**: iter72（`LC_ALL=C` で grep を byte-wise 化）・iter73（deny 側フックの byte-wise 決定化）の掃討が**完全か**。同型の locale 依存が他のフック/スクリプト（`hooks/lib/runtime-state.sh`・deploy-gate・`scripts/*.py`・`scripts/*.sh`）に残っていないか。非 ASCII・不正 UTF-8・Unicode 空白での差分を実測せよ。
4. **test-strength（偽造耐性）**: `scripts/run-test-strength-drill.py`（B1 drill）・`hooks/lib/marker.sh`（positive proof）・`hooks/lib/evidence.sh`（4段検証）・`scripts/build-judge-card.py`（judge 判定）で、「テストを実行していないのに green/PASS が成立する」経路、mutant の意味的品質が未強制な穴、judge の newest-entry 即断（前回 R6）系の残穴を探せ。前回 R4 の parse_spec NO_RUN 系が閉じているか再攻撃。
5. **前回 fix の regression 攻撃**: 前回レビュー R1〜R10 のうち「修正済み」とされた項目（iter60 事故防御の三層／S サイズ／upgrade × OS-lock 衝突／quality-pin の Fable 世代反転／fingerprint HEAD-sha 束縛 等）に対し、fix が本当に効いているか・回避経路が残っていないかを実地で突け。
6. **North Star 整合・複雑性収支（両者共通で測る＝乖離が最重要シグナル）**: 73 iterations・1300+ tests まで育った現状は、**作者一人が保守でき、非エンジニアが使える水準か**を問え。あなたは内部を熟知した立場なので「この複雑さは正当」と擁護しがちな偏りに注意し、意図的に懐疑側に立て（もう一人は外部視点で「作りすぎ」に気づきやすい。ここの乖離が「作りすぎか否か」の判定になる）。
   - 機構の重複・過剰・使われていない抽象はないか（YAGNI 違反）
   - 「正しい操作列の暗記（職人芸）」を人間に要求している箇所（＝設計負債の人間側転嫁。前回 R6 の「罠の6割は設計で根絶可能」の続き）
   - 常時ロードされるコンテキスト（`CLAUDE.md`＋`STATUS.md`＋rules）の肥大と thin 哲学の自己矛盾（前回 R8）
   - 配布に向けて、今のうちに単純化すべき負債はどれか（impact×保守コストで）

### 層2: Fable 特化（あなたの固有優位＝Claude Code 内部仕様の正確な知識。もう一人はこの次元をやらない）

> **負荷配分**: 層1（共通6次元）が突合の本体で最優先。層2はその後。層2 内の優先度は **7 ハーネス結合度 > 9 モデルポリシー > 8 context 経済**。**8 context 経済は前回 R8 で既知**のため known-confirmed 中心とし、前回未指摘の新規のみ深掘りせよ（既知の肥大数値の再測は1回で足りる）。

7. **ハーネス結合度・変化耐性**: Aegis は Claude Code に深く結合している。以下の結合面が、Claude Code 側の将来変更で**サイレントに壊れる/縮退する**箇所を探せ。
   - hook イベント（PreToolUse/PostToolUse/SessionStart/TaskCreated/TaskCompleted/PreCompact 等）への依存と、`hooks/lib/emit.sh` の出力スキーマが現行 Claude Code の期待と整合しているか（fail-open せず deny/block が効くか）
   - subagent API（frontmatter の `model`/`effort`/`maxTurns`/`disallowedTools`）、skill loading（`disable-model-invocation`・`user-invocable`）への依存
   - platform 側イベント増加（前回 R1 の `SubagentStart` 注入案など）で埋められる防御の空白
   - `bin/setup.sh` が生成/配布する settings.json・hooks 配線が、Claude Code の設定スキーマ変更に対して脆くないか
8. **context 経済**: thin L0 哲学と実測の乖離を突け。
   - 常時ロード（`CLAUDE.md`＋`STATUS.md`＋`.claude/rules/*`＋session-start 注入）の実 token を**実測**し、`scripts/context_budget.py` の計数が実費と乖離していないか（CJK 未計数・budget-exclude 機構の穴・前回 R8/budget#3）
   - `next_action`・`session_history`・LEARNINGS の肥大と、恒久知識の重複（CLAUDE.md「auto-memory は LEARNINGS を複製するな」の非対称）
   - budget 契約（raw word_count か `_budget_word_count` か）の headroom 地雷（skill 追加→drift 契約→CLAUDE.md 追記強制→即超過）
9. **モデルポリシー**: `scripts/platform_manifest.py` を精査せよ。
   - `ALLOWED_MODELS`／lineage alias／quality-pin（`opus`=max, `security`=max, `reviewer`=xhigh, `qa`=high 等）が **Fable 5 世代で反転していないか**（前回 R5: 品質役ほど弱いモデルで走る事故）。`fable` alias の受理状況を実機確認。
   - `CLAUDE_CODE_SUBAGENT_MODEL` による全 pin 一括降格（security 含む）の挙動と、その advisory が十分か
   - effort 配分（`OPUS_ONLY_EFFORTS` 等）の妥当性、系譜追随の staleness 窓（180日はモデル市場に不適合という前回指摘）
   - `check_framework_contract.py` によるモデル契約の enforcement に抜けがないか

---

## 3. 判定規律（Aegis の既存原則を継承）

- **実証してから書く**: severity を付ける所見は、可能な限り**実際にコマンドを走らせて再現**せよ（該当フックに JSON 入力を stdin で流して出力を観察／grep で該当行を特定／`pytest --collect-only` や dry-run 等）。「原理的限界」「到達不能」の類の主張は、**実証（トリガ入力が実際に emit 可能かの確認を含む）してからでなければ書くな**。iter73 の教訓: 「prior High と pattern-match でも、トリガ入力の到達可能性を実証してから severity を付けよ」。
- **到達可能性を較正せよ**: 脅威モデル上、モデルが emit するコマンドは常に valid UTF-8 である等の前提がある。理論上の穴が**実際に到達可能か**まで踏み込んで判定する（accepted residual を無闇に格上げしない／逆に「residual だから無害」を鵜呑みにもしない）。
- **既知はタグ1行、新規に注力**: 既知事項の再確認は `known-confirmed` の1行で足る。既知の「閉じた」主張への再攻撃で穴を見つけたら、それは新規（高価値）。
- **確度を明示**: 各所見に「実証済み（reproduced）／仮説（hypothesis）」を必ず付す。
- **優先順位**: 時間/コンテキストは有限。**moat → test-strength → locale/byte** を先に完走し、次に SF 再裁定・regression、次に North Star、最後に層2（層2 内は §2 の優先度 7>9>8）。突合の本体は層1なので層1を薄くして層2に流れるな。
- **完了規律（partial は final ではない）**: **全項目に evidence が付くまで「完了」を宣言するな。** 力尽きたら成果物冒頭に `STATUS: PARTIAL` と明記し、「未着手の次元」「再現できなかった所見（hypothesis 止まり）」を列挙せよ。一通り眺めただけで final を出すのは、突合相手との間に「両者とも触れていない＝安全」という誤った空白を作る最悪の結果を招く。
- **severity ルーブリック（2モデルで基準を揃えるため厳守）**:
  - **Critical** = moat を実際に迂回して破壊的/秘密漏洩コマンドを通せる、または green を偽造できる（reproduced・到達可能）。
  - **High** = 同上だが到達に非自明な前提が要る、または reproduced だが影響が限定的。
  - **Medium** = 防御の縮退・fail-visible の欠け・誤判定（実害はあるが直接の bypass ではない）。
  - **Low** = accepted residual 相当・理論上の穴（到達可能性が低い/未実証）。
  - **Info** = 観察・改善余地（バグではない）。
  - 到達可能性が実証できないものは Critical/High を付けるな（iter73 の格下げ教訓）。

---

## 4. 制約（read-only・厳守。違反はレビュー全体を無効化する）

- 既存ファイルを**一切変更しない**。`git checkout`/`restore`/`reset`/`clean`/`stash`/`commit`/`push` を**実行しない**。
- 許可される書き込みは、成果物ファイル（下記 §6 の1本）**のみ**。
- コマンドは read-only 目的のみ（`grep`/`cat`/`git log`/`git diff`/フックへの stdin 流し込み/`pytest --collect-only`/構文チェック 等）。**システム状態・ネットワーク・リポジトリ状態を変える操作は禁止**。
- 万一ツリーが汚れたら（`git status` が dirty になったら）: **即座に停止し、その旨を報告し、自分で戻そうとしない**（`git checkout` 等での「復元」も禁止＝過去に復元操作がツリー破壊事故を起こした前例がある＝iter60）。
- **盲検の担保**: この指示文と対象 clone 以外の文脈を**持ち込むな**。レビュー設計の議論内容、想定済みの攻撃仮説、もう一人のレビュアーの存在以上の情報を前提にしてはならない。あなたは白紙のコンテキストで、この clone だけを見て判断する。

---

## 5. 出力スキーマ（各所見をこの形で。もう一人と同一スキーマ＝突合のため厳守）

**ID 規約（突合の要）**: ID は **`<次元プレフィックス>-<連番>`** とせよ。プレフィックスは次元と1対1: `MOAT` / `SF` / `LOCALE` / `TEST` / `REGR` / `NORTH`（以上は Codex 版と共通）／層2 は `HARNESS` / `CTX` / `MODEL`。白紙 top3 は `FRESH-1/2/3`。同一次元内で連番。**層1 の6プレフィックスは Codex 版と逐語一致**させること（突合側が同次元内マッチングを機械的に行うため）。

所見ごとに次のフィールドを埋める:

```
### [ID] 一行タイトル
- 次元: moat / SF / locale-byte / test-strength / regression / north-star / harness / context / model-policy のいずれか
- severity: Critical / High / Medium / Low / Info
- confidence: reproduced（実証済み） / hypothesis（仮説）
- 新規性: 新規 / known-confirmed（既知の確認） / known-broken（既知の「閉じた」主張が破れている）
- 主張: 何が問題か（1-3文）
- 証拠: 該当箇所 file:line ＋【実行コマンドと、その生出力の該当行を逐語で貼る（要約不可）】
- North Star への影響: なぜこれが北極星基準で問題か（配布/保守/非エンジニア運用の観点）
- 修正方向: 具体的に（既存機構内の配線変更で足りるか、新機構が要るか、effort 見積り S/M/L）
```

**証拠の生出力必須**: `reproduced` を名乗る所見は、**実行したコマンドと生出力の該当行を逐語で貼れ**（要約は不可）。moat/locale 系は「この stdin JSON を流した → この stdout（`{}` 等）が返った／観測した grep 実装は BSD か GNU か」を必ず生で示すこと。生出力が無い所見は自動的に `hypothesis` 扱いとなる。

**North Star（複雑性）次元の証拠形式**: 「過剰/未使用/暗記強要」の主張にも操作的な証拠を課す — 未使用＝`grep -r` で参照0を示す／暗記強要＝正しい操作列が N ステップあり1つ誤ると block/ERROR になる再現／肥大＝実測した語数・token 数。操作的証拠を出せない複雑性所見は `hypothesis` 固定とし、severity は Medium 以下に留めよ。

最後に必ず:
- **エグゼクティブサマリ**（総合評価＋最重要3〜5件）
- **次元別サマリ表**（次元 × 新規件数 × 最高 severity）
- **あなたが「触ってはいけない/追わない方がよい」と判断した提案**（North Star 不整合で意図的に除外したもの。ノイズ抑制の透明化）

---

## 6. 成果物

レビュー結果を **`docs/fable-review-<YYYY-MM-DD>.md`** に1本で書き出すこと（このファイルの新規作成のみが許可された書き込み）。冒頭に §0 の対象コミット/version、使用したモデル・設定、レビュー所要の実行ログ要約を記す。

全力で、遠慮なく。あなたが見つけられなかった穴は、突合相手も見つけられないかもしれない。
