# Aegis 進化レビュー（2026-06-10）

対象: Aegis v1.3.2（リリースコミット `0bcb3ed`）
目的: 哲学の読み取り・類似フレームワークとの比較・欠陥検出の3軸から、今後の進化方向を提示する
方法: 本体ドキュメント精読（メインコンテキスト）＋ Web 調査エージェント＋読み取り専用欠陥監査エージェント（/tmp フィクスチャで hook 実発火検証、リポジトリ無変更）の並列実施
位置づけ: **監査と再設計の分離**を維持する。欠陥（第4章）は fix-forward 対象、進化テーマ（第5章）は brainstorm → grill-plan 行きであり、本書は実装を確約しない。

---

## 1. エグゼクティブサマリ

- **哲学は一貫しており、市場で唯一性がある。** 「非エンジニアが上流〜保守まで非スラップを作れる」という北極星と、保証（hooks）/手順（skills）/揮発値（隔離）の3層トリアージは、2026 年の主要フレームワーク群と比較しても他に同型が存在しない。特に Client モード（上流工程）と judge card（非エンジニア可視化）の組み合わせは独自資産。
- **しかし F6 と同族の「install 経路の死角」が今回さらに 2 件（P1）見つかった。** いずれも「framework repo 内では絶対に観測されず、インストール先でのみ発症する」型。v1.3.2 の scaffold smoke 拡張でも捕捉できなかった理由は、smoke の検査入力が実運用の hook 入力スキーマと乖離しているため。**「検査入力の現実度」自体を契約化する**ことが構造的対策になる。
- **進化の本丸は機能追加ではなく「実プロジェクトでの証明」と「検証の実行ベース化」。** B-series 完了でロードマップは消化済み。次の価値は (1) 実案件投入によるフィードバックループ、(2) 「エージェントの主張」ではなく「ツール実行の痕跡」で完了を判定する activity verification、(3) ネイティブ機能に食われる下層ガードレールの計画的な引き算、の3つにある。

**推奨（理由付き）**: まず P1×2 + P2-1 を fix-forward で締める（インストール先の実害・moat 不在は北極星の信頼性を直撃するため）。その後、進化テーマ E1「検証の実行ベース化」を brainstorm に乗せる（2026 年のモデル特性変化＝検証主張の信頼性低下に対する harness 側の正攻法であり、Aegis の「エビデンスなき完了なし」哲学の自然な延長のため）。

---

## 2. 哲学の読み取り

### 2.1 核となる思想（ドキュメントから抽出）

| 思想 | 出典 | 要約 |
|------|------|------|
| 北極星 | north-star（メモリ）/ README | 非エンジニアが上流〜保守の 12 能力を非スラップで回せる。harness=構造・段階開示・ゲート・可視化、LLM=判断レビュー |
| 3層トリアージ | 再アーキ方針 / emit.sh 設計 | 保証=決定論 hooks（PaC）、手順=モデル委任（skills）、揮発値=隔離。層を混ぜない |
| トレッドミルから降りる | v1.0.0 再アーキ | 公開契約=運用契約のみ（SemVer）。Claude Code の内部仕様追従をやめ、emit.sh 単一出力源に集約 |
| エビデンスなき完了なし | CLAUDE.md Completion Rule | ゼロツールコール完了は無効。成果物・チェック実行・STATUS 参照整合を hook で強制 |
| 監査と再設計の分離 | audit-charter-2026-06-06 | 欠陥の検出と将来の設計判断を別フェーズに分け、混入を防ぐ |
| 段階開示 | Context Budget Policy | L0 常駐は CLAUDE.md+STATUS.md のみ。pull-based でフェーズ必要分だけ読む |

### 2.2 哲学の現在地 — 前回監査の P1〜P3 はどこまで解けたか

2026-06-06 監査が立てた哲学的課題 3 件に対する到達度:

- **P1（非エンジニア judge の単一障害点）**: B2 の judge card と tri-state ゲート（🟢/🔴/🟡 + `--ack`）で「judge が判断材料を持たない」問題は前進した。ただし tier-2 エビデンスは**自己申告（エージェントが自分の出力を根拠として提示）**のままで、独立検証は未達。→ 進化テーマ E1 に接続。
- **P2（非スラップが無計測）**: B1 のテスト強度ドリル（ミューテーション）で「テストが弱い」は計測可能になった。一方、**意味的整合（ACCEPTANCE ↔ テストが本当に対応しているか）は依然無計測**。→ 進化テーマ E2 に接続。
- **P3（決定論保証が宣言より弱い）**: v1.3.2 の F6 修正＋scaffold smoke 実発火化で大きく前進したが、今回の P1-1/P2-1 が示す通り**「宣言と実態の乖離」はまだ install 経路に残る**。→ 第4章 fix-forward に接続。

### 2.3 読み取れる発達段階

Aegis は「機能を作る段階」を終え、**「実プロジェクトで証明される段階」への転換点**にいる。B-series 全消化・12 能力の骨格完成に対し、実案件は Hair Salon Bloom の 1 件のみ。哲学（非エンジニアの非スラップ）は実ユーザーの失敗データなしには反証も改良もできない。今後の進化は「足す」より「回して測る」が主軸になるべき、というのがドキュメント群からの最大の読み取りである。

---

## 3. 競合ランドスケープと Aegis の位置づけ（Web 調査）

### 3.1 2026 年の主要フレームワーク・ハーネス

| 系統 | 代表 | 中核アイデア | Aegis との関係 |
|------|------|--------------|----------------|
| Spec 駆動 | GitHub Spec Kit / AWS Kiro / OpenSpec / Augment Cosmos | 仕様を一級成果物に。Kiro は EARS 記法＋形式検証志向、OpenSpec は差分仕様、Cosmos は「生きた仕様」 | Aegis の requirements/ACCEPTANCE と同方向だが、仕様↔コードの drift 検出は Aegis 未実装 |
| エージェント手法集 | obra/superpowers / everything-claude-code | スキル・ワークフローの大規模カタログ。コミュニティ規模が大きい | Aegis は「薄い契約＋pull-based」で逆張り。カタログ化はしない方針が明確 |
| マルチエージェント編成 | claude-flow→Ruflo / CCPM / Conductor | 並列 worktree・PM 的タスク分解・エージェント群編成 | Aegis は「subagent は安全・縮小に資する時のみ」の抑制方針。並列化は未開拓領域 |
| プロセス OS | BMAD-METHOD / Agent OS | 役割と工程の全体定義（アナリスト→PM→アーキ→開発） | 工程の幅は近いが、対象が「エンジニアチーム」。非エンジニア単独運転は想定外 |
| 標準化 | AGENTS.md | エージェント設定のクロスツール標準 | Aegis は CLAUDE.md 専用。互換レイヤは検討余地（E6） |

### 3.2 業界ドクトリンとの整合

- **「hooks=決定論 / skills=確率論」**という分担論が 2026 年に広く定着した。Aegis の3層トリアージはこれを先取りしており、しかも「揮発値の隔離」という第3層を持つ点でより精緻。
- **モデル特性の変化**: Fable 5 世代の system card は「検証したと主張するが実際は検証していない」型の失敗モードを明記している。「エージェントの自己申告を信じない」設計（＝Aegis の Completion Rule）の価値は上がっているが、現状の hook は**「ツールを呼んだか」までしか見ておらず、「何を実行してどんな出力を得たか」は見ていない**。

### 3.3 Aegis の差別化要素（調査結論）

1. **非エンジニアの全ライフサイクル運転** — Client モード（onboard→handover）を持つフレームワークは他に存在しない。最大の戦略資産。
2. **judge card** — 非エンジニアが承認判断できる可視化。tri-state ゲートと一体。
3. **決定論ゲートの一貫性** — ゲート遷移・完了条件・参照整合を hook で強制する密度は最高水準。
4. **eval 内蔵** — contract/drift/smoke の自己検査をフレームワーク自体が持つ。
5. **運用契約のみ公開（SemVer）** — 追従コスト最小化の設計判断が明文化されている。

---

## 4. 新規欠陥 findings（fix-forward 対象）

読み取り専用監査エージェントが /tmp フィクスチャで hook を実発火させて検証した。既出 F1〜F7・2026-06-06 監査との重複は除外済み。**全件新規**。詳細な根拠・行番号・修正方針案は監査エージェント報告に基づく。

### P1 — インストール先で実害（repo 内では絶対に観測されない）

| ID | 内容 | 根拠 | 修正方針案 |
|----|------|------|-----------|
| P1-1 | **check-control-plane.sh が install 先でほぼ全 Bash コマンドを deny**。`hooks/check-control-plane.sh:42` が RAW hook 入力全体を CONTROL_PLANE 正規表現（`:38`、`\.claude/` 含む）で検査するが、hook 入力には常に `transcript_path`（`~/.claude/projects/...`）が含まれるため early-allow が**決して発火しない**。`git status`/`npm test`/`python3 -m pytest` が deny（/tmp で実証済み） | full プロファイル + task_type≠framework で再現。`scripts/eval_scaffold_smoke.py:96-123` の検証 stdin は transcript_path を含まない合成入力＝F6 と同型の死角 | 抽出済み `command` 文字列のみを検査対象にする。smoke の stdin を実運用スキーマ（session_id/transcript_path/cwd 込み）に揃える |
| P1-2 | **check-gate.sh の `*/hooks/*`・`*/scripts/*` glob が一般プロジェクトのディレクトリと衝突**。React の `src/hooks/useAuth.ts` や `scripts/build.js` の Edit/Write が deny される（`hooks/check-gate.sh:56-67`） | standard/full の両 install で再現。回避策の task_type=framework 化は他の防御を全部外すため悪手 | ルート直下に限定（先頭一致＋`$CLAUDE_PROJECT_DIR` 正規化）、または setup.sh 配布ファイルの実マニフェスト照合へ移行 |

### P2 — silent degradation

| ID | 内容 | 根拠 |
|----|------|------|
| P2-1 | **standard プロファイルで破壊コマンドガードが一切不発火**。check-destructive 等はファイル配布されるが settings 未登録。CLAUDE.md:16 の「Enforce via hooks (PaC)」と実態が矛盾し、Bash PreToolUse hook がゼロ | `templates/profiles/standard.json`（hooks_include に不在）+ `bin/setup.sh:239-252` |
| P2-2 | **`vercel --prod` が deploy gate を素通し**。パターンが bare `vercel` と `vercel deploy` のみで最頻出形を逃す。`wrangler deploy` も未カバー | `hooks/check-deploy-gate.sh:44` |
| P2-3 | **task_size=S/M で deploy gate が無条件 fail-open**。size の許可 phase に deploy が無いと return 0（許可）。「phase スキップ＝無検査で許可」という前提逆転 | `scripts/check_status.py:1051-1054` |
| P2-4 | **check-secrets.sh が id_ed25519/id_ecdsa を未検出**（`id_rsa` のみ。現代の ssh-keygen 既定は ed25519） | `hooks/check-secrets.sh:29,60-64,99` |
| P2-5 | **contract manifest が emit.sh/patterns.sh を未追跡**。repo 側から emit.sh が消えても contract は green（F6 の中心ファイルが番人不在） | `scripts/check_framework_contract.py:121-142` |
| P2-6 | **example STATUS.md の framework_version が "0.12.2" のまま**（正準 1.3.2）。全 drift 検出器の対象外で、非エンジニアがコピーする example が3メジャー版古い | `examples/minimal-project/docs/STATUS.md:3` |

### P3 — 軽微

P3-1 check-task-completed の python3 不在時 fail-open（check-task-created と非対称）／P3-2 `ULTRA_PRECOMPACT_INTERVAL` の旧命名残り／P3-3 update-gate.sh の flock 無し（並行セッションで lost update）／P3-4 WRITE_INDICATORS の裸 substring（`grep -r "remove"` が偽陽性）／P3-5 `grep -A20` 依存の脆い YAML 読み／P3-6 hooks.template.json が `$CLAUDE_PROJECT_DIR` 非使用（cwd 相対で全 hook 不発の余地）。

### メインコンテキストでの独自発見（ナレッジ層の欠陥）

| ID | 内容 | 含意 |
|----|------|------|
| K-1 | **docs/LEARNINGS.md:33 に stale エントリ（confidence:9）**。「update-gate.sh が current_refs を approved で上書きする」と主張するが、`scripts/update-gate.sh:189-200` で修正済みであることを検証確認。毎セッション注入され続ける | **構造問題**: LEARNINGS に「解決済みマーク」の仕組みがない。drift 検査は mirror（ファイル同一性）は見るが知識（記述の真偽）は見ない。高 confidence の偽情報は決定論ガードより害が大きい可能性 |
| K-2 | functional-integrity-audit-report-2026-06-07.md 末尾に「Layer 3（未着手）」節が重複 | cosmetic。報告書整形時の消し忘れ |

### 構造的観察（個別修正を超える教訓）

1. **「検査が実運用経路を見ていない」F6 同型が 2 つ残存**（smoke の stdin 非現実・manifest の lib 部分追跡）。→ 「検査入力の現実度」を契約化する必要。
2. **パス文字列パターンによる制御プレーン防御は原理的に衝突する**（P1-1/P1-2 は同根）。配布実ファイルのマニフェスト照合への移行が本筋。
3. **fail-open/closed の方針が hook ごとにアドホック**（deploy=closed、task-completed=open、control-plane=過剰 closed）。1 枚のポリシー表で宣言しテストで固定すべき。
4. **task_size 緩和が「phase の省略」と「コマンドの許可」を混同**（P2-3）。skip のセマンティクス（検査不要なのか実行禁止なのか）の明文化が必要。

---

## 5. 進化方向（brainstorm 行き — 本書では決定しない）

Web 調査の「次の形」仮説 5 件と evolution 候補 7 件を、Aegis の哲学と欠陥所見に照らして 6 テーマに統合した。**優先度順**。

### E1: 検証の実行ベース化（activity verification）— 最優先推奨

- **何か**: 「テストを実行した」というエージェントの主張ではなく、**hook が観測したツール実行の痕跡**（PostToolUse で記録した実コマンド・exit code・出力ハッシュ）と完了主張を突合する。tier-2 エビデンスの自己申告問題（§2.2 P1 残課題）の正面解。
- **なぜ最優先か**: (1) Fable 5 世代の「検証したと偽る」失敗モードへの harness 側の正攻法。(2) Aegis の「エビデンスなき完了なし」哲学の自然な延長で、思想の改変なしに実装できる。(3) 既存の post-bash.sh・TaskCompleted hook という足場が既にある。
- **形の例**: post-bash が `docs/evidence-log.jsonl` に追記 → TaskCompleted hook が「完了主張に対応する実行記録があるか」を決定論照合。

### E2: 仕様↔コード drift 検出（living specs）

- **何か**: ACCEPTANCE 項目とテストの対応を計測する（OpenSpec の差分仕様・Cosmos の living specs と同方向）。§2.2 P2 残課題（意味的整合の無計測）の解。
- **トレードオフ**: 意味的対応の判定は LLM 判断が必要＝3層トリアージでは「手順」層。決定論にできる部分（ACCEPTANCE ID をテスト名/コメントに記載させ存在照合）から始め、意味判定は reviewer の責務に載せる二段構えが哲学整合的。

### E3: 計画的な引き算（native 委譲の継続）

- **何か**: B4 で文書化した委譲マップを「定期棚卸しの運用」に昇格する。Claude Code ネイティブ（plan mode、checkpoint、task system 等）が下層ガードレールを食い続けるのは確定トレンドで、**残るのはプロセスゲート（人間の承認・evidence 契約）**という Web 調査の結論と一致。
- **なぜ重要か**: 「トレッドミルから降りる」哲学の維持コストを下げる。足すより消す方が moat の純度が上がる。

### E4: 実プロジェクト投入とフィードバックループ

- **何か**: Hair Salon Bloom に続く実案件 2〜3 件で 12 能力を一周させ、LEARNINGS に「非エンジニア運転の実失敗データ」を蓄積する。K-1 で見つけた LEARNINGS の解決済みマーク機構（status: open/resolved + 解決時の参照コミット）をこのとき併せて導入する。
- **なぜ重要か**: §2.3 の通り、哲学の反証データが 1 件しかない。フレームワークの進化判断が仮説ベースから実測ベースに変わる。

### E5: worktree 並列・Evaluator agent（条件付き）

- claude-flow/Conductor 系の並列編成は Aegis の「subagent 抑制」方針と緊張関係にある。**review/qa の独立性向上**（実装者と別コンテキストで検証する Evaluator）に限定して採るのが哲学整合的。全面的な並列編成は非エンジニア運転の複雑性を上げるため非推奨。

### E6: AGENTS.md 互換レイヤ（低優先）

- クロスツール標準への片方向 export（CLAUDE.md → AGENTS.md 生成）なら追従コスト最小。ただし現ユーザー基盤では効果が薄く、要望が出るまで保留が妥当。

### 採らない方が良いもの（明示的非推奨）

- **スキルカタログの大規模化**（superpowers/ECC 路線）: pull-based・薄い契約の哲学と正面衝突。
- **EARS 等の形式記法の全面導入**（Kiro 路線): 非エンジニアの認知負荷を上げ、北極星と逆行。要件テンプレの「条件→振る舞い」構造のヒントとして部分借用に留める。

---

## 6. 推奨ロードマップ

| 順 | 項目 | 種別 | 理由 |
|----|------|------|------|
| 1 | P1-1 + P1-2 修正（control-plane の入力抽出修正・gate glob のルート限定）＋ smoke stdin の実運用スキーマ化 | fix-forward（bugfix フロー） | インストール先で全 Bash/正当編集が死ぬ＝北極星の信頼性を直撃。smoke 現実化は F6 族の再発封鎖で、修正自体の検証器にもなる |
| 2 | P2-1（standard の破壊ガード登録）＋ P2-6（example 版数） | fix-forward | 「recommended」プロファイルの moat 不在は宣言と実態の乖離。example は非エンジニアの入口 |
| 3 | P2-2〜P2-5、P3 群、K-2 | fix-forward（まとめて S/M） | 個別は小さいが、fail-open/closed ポリシー表（構造的観察3）をこの時に1枚作ると再発系統が締まる |
| 4 | K-1: LEARNINGS の stale エントリ解消＋解決済みマーク機構 | 小改修 | 偽情報の毎セッション注入を止める。E4 の前提整備 |
| 5 | E1: activity verification | brainstorm → grill-plan | 進化の本丸。§5 参照 |
| 6 | E4: 実案件投入（E2/E3 は実測データを得てから判断） | 運用 | 仮説ベースの機能追加を止め、実測ベースに転換する |

---

## 付記: 検証来歴

- 欠陥監査: 読み取り専用エージェントが /tmp フィクスチャで hook を実 stdin 発火させ検証（リポジトリ無変更）。P1-1 はメインコンテキストでも `hooks/check-control-plane.sh:30-116` を直読して根拠（CONTROL_PLANE 正規表現・RAW 入力検査・READ_ONLY_STARTS の欠落・既定 deny）を独立確認済み。
- K-1: `scripts/update-gate.sh:189-200` を直読し、LEARNINGS 記載のバグが修正済みであることを確認済み。
- Web 調査: 2026-06-10 時点の調査エージェント報告に基づく。スター数等の揮発値は本書に記載しない（揮発値の隔離）。
