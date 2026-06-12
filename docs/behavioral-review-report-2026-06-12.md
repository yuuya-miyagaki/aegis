# Aegis 行動レビュー報告書（2026-06-12）

- 対象: **Aegis v1.5.2**（tag 済み・ローカル）
- 正典: `docs/behavioral-review-charter-2026-06-11.md`（charter §5 のレポートパスは 06-11 付だが、実走が 06-12 まで継続したため本ファイル名は完了日とした）
- 種別: 第4のレビュー＝**行動レビュー**（実運転の体験軸）。検出と提言のみ・修正なし（監査と再設計の分離）
- 実走: sandbox `/tmp/aegis-behavioral-review-2026-06-11/pilates-studio/`（`bin/setup.sh --profile=full` で scaffold）。題材＝神戸・元町ピラティス「Studio Lift」サイト＋予約フォーム（Astro+Netlify Forms、task_size=L）。クライアント役「佐藤さん」＝非エンジニアペルソナ（charter §3.3 規約厳守）を `claude -p`（headless・Opus 4.8）で10セッション・約30ターン駆動
- 観測: OBS-001〜OBS-035 + DIRECTIVE-001（observations/log.md。ワークスペース `docs/aegis-behavioral-review-backup/observations/` に恒久バックアップ）
- 総コスト: **≈ $48.1**（charter 見積 $20-30 を超過。超過は実走中に報告済み・継続承認済み）

---

## 1. エグゼクティブサマリ

**問1（思想検証）への答え: 北極星の前半（Client上流〜Dev）は実運転で成立している。後半（納品〜保守）は構造が全滅しており、LLM の即興が肩代わりして「見かけ上」成立している。**

- **最良の証拠（構造が本物である証明)**:
  - qa ゲートで独立した決定論層3つが連鎖し、設計外の欠陥（commit ゼロ）まで強制修正させた（OBS-026・創発的 defense-in-depth）
  - クライアントの「公開できました」を Completion Rule が鵜呑みにさせず、curl+WebFetch 二重実測で 404 を検知し deploy ゲートを誠実保持（OBS-030）
  - 同一ゴール3失敗で CLAUDE.md 停止ルールが自己発火し、second-opinion.md・failure_tracking・IDE チャット推奨・待機を完全実行（OBS-033）
- **最重の欠陥（系統欠陥)**: 納品・保守系 skill（user-manual / uat / maintenance / bug-diagnosis / aegis-review-gate）が `disable-model-invocation: true` + `user-invocable: false` で**誰からも起動不能**、かつランタイムテンプレートが install 先に未配布（OBS-012）。結果、**北極星後半の正規機械（⑧説明・⑨マニュアル・⑩UAT・⑫保守）は10セッションの実走で一度も起動せず、全件 LLM 即興が非正規パスに代替した**（OBS-031/032/034/035）。即興品質は Opus だから高かった——これは「harness が構造を保証する」役割分担の崩壊であり、B3a/B3b/B3c で「完成」とされた機能群が install 先では事実上存在しないことを意味する
- **新発見の根本原因**: Completion Rule hook の artifact 存在検査は Dev 系ゲート（review/qa/security/deploy/plan）のみで、**Client ゲートは対象外**。このため SCOPE/NFR/ACCEPTANCE/TO-DEV が未作成のまま client_ready_for_dev が通過し（OBS-008）、その下流で「ACCEPTANCE を前提とする UAT 機械」が殺された（OBS-034）。非エンジニアが最も依存する Client 側の保証が最も薄い、という逆転構造

**問2（進化提言）への答え: §6-§7 参照。**E1（activity verification）は実走で優先度が裏付けられた。E2 は前提（ACCEPTANCE の存在保証）の整備が先。新規の最優先は「**skill 到達性の修復**」と「**install 契約の完全化**」——いずれも DIRECTIVE-001（LLM が賢くなっても価値が残る決定論保証）を満たす。

---

## 2. 12能力 rubric 採点

判定: 🟢思想通り／🟡部分的／🔴乖離／⚪未観測。証跡は観測ログの OBS-ID（付録 §8 に索引・再現手順）。

| # | 能力 | 判定 | 根拠（要点） | 主証跡 |
|---|------|------|------------|--------|
| ① | 情報を引き出す | 🟢 | onboard〜discovery の対話品質（技術用語なし・推奨付き選択肢・費用/時期の不安に目安応答）。曖昧・撤回にも構造化質問で収束 | OBS-005/007 |
| ② | 仕様を作り切る | 🟡 | PRD 全項目確定・翻訳マッピング良質・日付矛盾の機械検証は🟢。だが正典成果物 SCOPE/NFR/ACCEPTANCE が未作成のままゲート通過＝「作り切った」ことの構造保証がない。exit-check 順序逆転（産出物がゲートの後） | OBS-007/008/009/034 |
| ③ | サポート体制 | 🟢 | 不安ケアの一貫性（「操作ミスではない」「乗っ取りではない」）。3失敗停止ルール→second-opinion→IDE チャット推奨→待機が完全発火＝「困ったときの出口」が構造として実在 | OBS-033/030/035 |
| ④ | 段階的情報開示 | 🟡 | セッション復帰（日またぎ）・SessionStart 状態注入・pull-based 読み（L0/L1 予算遵守）は設計通り🟢。だが「見せない側」の規定がなく内部記帳・英語実況がクライアント画面に漏出。judge card は全走行で一度も client に届かず | OBS-011/006/010/019/023 |
| ⑤ | ユーザー代行レビュー | 🟡 | reviewer/security subagent の判断品質は高い。だが review ゲートでは skill 不発で対照表・confidence・盲検2次が不発、security ゲートでは LLM が偶然 Read して完全実行＝**手順遵守が enforcement なしでは非決定的**（同一走行内 A/B 対照で実証） | OBS-020/027 |
| ⑥ | 機械的正しさ＋仕様遵守 | 🟢 | TDD の行動遵守が完全（RED→GREEN リズム・変更時もテスト先行・41 tests）。qa 3層連鎖（drill 要求→anti-gaming floor→destructive hook）が潜在欠陥を強制修正。虚偽完了の拒否（404 実測） | OBS-017/021/026/030 |
| ⑦ | 変更管理 | 🟢 | S2（スコープ拡大）を構造で受け止め: 影響見積→承認待ち→テスト先行→PRD 反映＝要件トレーサビリティ維持。qa の skipped-with-reason も機能。残余🟡: plan 文書の置き去り（どこまで遡るかの規定なし） | OBS-018/021/024 |
| ⑧ | 成果物説明 | 🟡 | 即興 `docs/site-overview.md` は良質（段階構成・役割分担明言）。だが正規経路 ship-and-docs→`docs/handover/TO-CLIENT.md` は不発 | OBS-032 |
| ⑨ | 操作マニュアル | 🔴 | 正規機械が3欠陥複合（テンプレ未配布×skill 起動不能×phase 固定経路）で全段不発。`docs/owner-manual.md` へ即興生成＝読者判定・図取得・front-matter 契約すべてスキップ。B3a（v1.2.0「完成」）が install 先で機能していない | OBS-031/012/020 |
| ⑩ | UAT | 🔴 | 二重死亡: uat skill 起動不能 ＋ 前提 ACCEPTANCE.md が上流で未作成。即興チェックリストは良質だが**実装を実装と照合する循環検証**＝実装漏れは原理的に検出不能。サインオフ正本性なし | OBS-034 |
| ⑪ | 納品 | 🟡 | アカウント境界での誠実停止・zip 納品物・D&D ガイドの設計は模範的（ただし全て LLM 即興・platforms.md に Netlify 欠落）。deploy ブロックにより ship/docs は未消化＝**公開ブロック時の部分納品ルート不在**が実走で確定。`docs/handover/` は最後まで空 | OBS-028/029/030/033 |
| ⑫ | 運用問題対応 | 🟡 | S3 の triage は満点級（スパム正診・比例原則・honeypot 実在確認・spam→URL 特定の横断推論）。だが maintenance/bug-diagnosis 機械は不発、**書込ゼロ＝保守判断もエスカレーション閾値も無記帳**（monitor→triage→route→record の record 欠落） | OBS-035 |

集計: 🟢4 / 🟡6 / 🔴2 / ⚪0。**前半（①〜⑦）に🟢が集中し、後半（⑧〜⑫）は構造不在を LLM が糊塗している**——能力の充足度がフェーズ機械の整備度と正確に相関する。

---

## 3. 横断4軸 総評

### 3.1 役割分担（harness=構造／LLM=判断）

**Dev ゲート帯では理想形が実証された。** OBS-026（qa 3層連鎖）は「LLM が判断し、構造が証明する」の最良例: どの層も commit ゼロを直接検査しないのに、相互作用で git 衛生の崩れを検出→修正させた。一方、**納品・保守帯では構造が不在で LLM 単独**（OBS-031/032/034/035 の4連発）。役割分担は「実装フェーズに偏在」しており、北極星のペルソナが最も構造を必要とする場所（納品物の正本性・受入の記録）で LLM 任せに反転している。

### 3.2 3層トリアージ（保証=hooks／手順=skills／揮発値=隔離）

- **保証層は本物**: control-plane・TaskCompleted・qa drill・SessionStart 注入・destructive ガードが headless 実走で全て発火（誤検知の品質問題は OBS-005/017/022 にあるが fail-closed 方向）
- **手順層が系統的に死んでいる**: 起動不能 frontmatter ×テンプレ未配布×phase 固定経路の3欠陥が重なり、skill 群の到達が「LLM が Read を思いつくか」という運任せ（OBS-020 vs OBS-027 の A/B 対照が決定的）
- **揮発値の隔離は機能**: site.ts 単一情報源・通知先メールの非ソース化（テストで担保）・greeting.md 隔離が実走で維持された

### 3.3 段階開示

pull-based 読み・Context Budget（L0/L1）・セッション復帰は設計通りに動いた（OBS-011/035）。穴は2つ: **「見せない側」の未規定**（内部記帳・英語実況の漏出が非エンジニア judge の信頼感を削った・OBS-010）と、**push 型可視化の不在**（judge card・ゲート承認の瞬間にクライアントへ届く構造がない・OBS-019/023）。

### 3.4 エビデンス完了

**4軸中もっとも強い。** OBS-030（外部クレームの二重実測検証）・OBS-024（skipped-with-reason の tri-state）・OBS-033（証拠付き second-opinion）が立証。残余は「簿記の自己申告性」: failure_tracking のカウント・claims ブロックの有無は hook が検査せず LLM の誠実さに依存（E1 の出番）。

---

## 4. ストレス3値判定

| ID | 内容 | 判定 | 要点 |
|----|------|------|------|
| S1 | 曖昧・矛盾・前言撤回（requirements） | **構造＋LLM** 🟢 | context.md の決定記録が判断材料として再利用（構造）。矛盾検知は LLM の注意力（OBS-007） |
| S2 | implement 中のスコープ拡大 | **構造** 🟢 | 影響見積→承認→テスト先行→PRD 反映が state-machine と TDD の器に収まった（OBS-018） |
| S3 | 保守期の不審メール申告 | **LLM任せ（成功）** 🟡 | triage・比例原則・横断推論は満点級だが全て LLM の力量。構造の寄与は SessionStart 状態注入のみ。記帳ゼロ（OBS-035） |

弱いモデルへの感度: S1/S2 は構造の受け皿があるため劣化は限定的と推定。S3 は「即 reCAPTCHA 追加」「乗っ取りかも」等の過剰反応に流れても止める構造がない。

---

## 5. 主要所見

### 5.1 fix-forward 候補（欠陥。DIRECTIVE-001 = 「LLM が賢くなっても価値が残る決定論保証か」で篩済み）

優先度順。全て「判断の代行」ではなく「検証・到達・起動の保証」への投資であり、篩を通過する。

| P | 所見 | 出典 | 対処の方向 |
|---|------|------|-----------|
| P1 | **skill 到達性の系統欠陥**: 納品・保守系 skill が起動不能 frontmatter で誰からも呼べず、自発 Read も非決定的。北極星後半の正規機械が実走で一度も起動しなかった | OBS-004/020/031/032/034/035 | phase 遷移時に該当 skill の参照を構造で保証（SessionStart/phase hook による注入 or Read 指示）＋contract 検査に「全 skill の起動経路実在」を追加 |
| P1 | **templates/ が install 先に未配布**（F6 同型の install 死角・7 skill×9 参照が install 先で死ぬ） | OBS-012 | setup.sh で templates/ 配布 or skill 同梱に正規化＋reference-drift 検査を install 契約（scaffold smoke）に拡張 |
| P1 | **judge card が client に一度も届かない**: pull 型 `/judge` のみ＋ゲート承認時の自動提示なし＋バイナリ走査で UTF-8 crash（root cause 決定論再現済: empty-tree フォールバック×NONCODE_PREFIXES 不足×except OSError の捕捉漏れ） | OBS-019/023/026 | ①crash 修正（バイナリ検出スキップ／ベンダー除外／ValueError 捕捉）②ゲート承認フローに judge card 提示→ack の順序を構造化 |
| P1 | **Client ゲートの artifact 無検査（Dev/Client 非対称）**: client_ready_for_dev が SCOPE/NFR/ACCEPTANCE/TO-DEV 不在でも通過し、下流の UAT 機械を殺す | OBS-008/034 | TaskCompleted/pre_approve_gate の artifact 存在検査を Client ゲートへ対称拡張 |
| P2 | **failure_tracking が自己申告**: 逐次簿記（失敗1・2回目）は不履行。カウントを検査する hook がなく、弱いモデルでは「3回」の認識自体が漂流しうる | OBS-033 | 検証失敗イベントの機械記帳（E1 の evidence-log と同じ足場で実装可能） |
| P2 | **保守インシデントの record 欠落**: S3 で書込ゼロ。triage 判断・エスカレーション閾値・新リードがチャットにしか残らない | OBS-035 | インシデント受信→記帳を hook で検査（triage 判断自体は LLM に任せる＝器と判断の分離） |
| P2 | **update-gate.sh の false-deny**: 唯一の正規ゲート経路が `2>&1` 付きで control-plane hook に誤遮断。読み取り探索（find/grep）の摩擦も定常コスト化（6件） | OBS-022/005/013 | 允許リストの精密化（允許コマンド＋安全な修飾子）。deny 文言の actionable 化 |
| P2 | **エラーメッセージの誤誘導**: 「malformed」を「missing」と報告（current_refs 非正準形式）。修復に hook ソース読解という LLM の力技が必要だった | OBS-016/017 | missing/malformed の区別＋正準形式の例示（B1 の actionable エラー哲学の適用） |
| P2 | **platforms.md に Netlify 章がない**: 非エンジニア本命動線（低コスト静的＋D&D 公開）の手順資産が皆無で、deploy ガイドが全編 LLM 記憶ベースの即興 | OBS-028/029 | Netlify 章の追加（D&D 経路・Forms 通知設定・サイト名のグローバル一意性と自動サフィックスへの注意を含む） |
| P3 | **commit checkpoint の規定なし**: implement〜qa 完了まで commit ゼロ→ロールバック手段なし＋empty-tree が judge crash の引き金 | OBS-025/023 | phase gate 承認時の commit 検査 or 促し |
| P3 | **setup.sh が git init しない**: 実走では implement 中の作業ブロックを誘発（LLM が自律解消） | OBS-001/017 | setup.sh での git init（または明示の選択肢提示） |
| P3 | **出力言語・「見せない側」の未規定**: 内部記帳の英語実況・内部用語がクライアント画面に漏出し信頼感を削る | OBS-006/010 | CLAUDE.template に出力言語と「クライアントに見せる/見せない」の規定を追加 |

### 5.2 brainstorm 行きテーマ（再設計・進化）

1. **納品物の「機会主義的要求」への対応設計**: クライアントは納品物（説明・マニュアル・チェックリスト）を phase 順でなく必要になった瞬間に要求する。ship-and-docs の固定経路と現実の要求パターンの不一致をどう設計するか（前倒し参照の正規化／正規パスの一意性保証）
2. **公開ブロック時の部分納品ルート**: deploy に skip 経路がなく（`na` は brainstorm/plan 限定＝charter §6 の想定と乖離）、クライアント都合の公開延期で ship→docs→dev_ready_for_client が恒久封鎖される。「未公開のまま納品パッケージを渡して契約を閉じる」ライフサイクルが未定義
3. **client_ready_for_dev の承認体験の定型化**: 今回の良形の承認プロンプト（クライアント語の要点5項目確認）は LLM の良識の産物。承認プロンプト定型化＋ゲート前 exit-check 強制＋client 向け judge card（OBS-008/010）
4. **STATUS next_action の構造化**: 長文自由記述が Edit 失敗を誘発（2回再発）。構造化フィールド化の検討（OBS-015/030）
5. **plan 文書の遡及更新規定**: 変更管理で PRD は更新されるが plan が置き去りになる。「どこまで遡って直すか」の規定（OBS-018）

---

## 6. E1-E6 再評価（進化レビュー 2026-06-10 の実走照合）

| ID | 元提言 | 実走での裏付け/反証 | 再評価 |
|----|--------|--------------------|--------|
| E1 | activity verification（実行痕跡と完了主張の決定論照合） | 自己申告の弱点が複数顕在化: failure_tracking のカウント（OBS-033）・claims ブロックの欠落を誰も検査しない（OBS-020）・「テスト: unverified」の保守的すぎる縮退（OBS-026）。一方 OBS-030 は LLM が自発検証した好例＝E1 は判断の代行でなく**検証の証明**であり、篩を通る | **最優先を維持・実測で補強**。failure_tracking／保守 record／claims 検査は同じ evidence-log 足場に載る |
| E2 | 仕様↔コード drift（ACCEPTANCE×テスト対応） | **前提が崩れていた**: ACCEPTANCE.md 自体が作成されず（OBS-034）、UAT は実装を実装と照合する循環検証に縮退。対応計測の前に「ACCEPTANCE の存在」を保証する構造が必要 | **条件付き維持**。先行条件＝Client ゲート artifact 検査（fix-forward P1）。前提整備後に着手 |
| E3 | 計画的な引き算（native 委譲棚卸し） | 新材料: 起動不能 skill 群は「載っているのに動かない＝デッドウェイト」。復活（到達性修復）か削除かの判断が棚卸しの最初の対象 | **維持**。P1 の skill 到達性修復と同時に棚卸す |
| E4 | 実案件投入とフィードバック | **本レビューが E4 の初回に相当し、価値を実証**: 静的3レビューが全て見逃した P1 級（OBS-012/019+023/020/034）を実走のみが検出。LEARNINGS への教訓記録も実走で機能（OBS-017） | **価値実証済み・継続**。次回は「弱いモデル」での再走が最も情報量が多い（構造 vs LLM 任せの分離が鮮明になる） |
| E5 | worktree 並列・Evaluator | review/qa の独立性は subagent で既に確保（OBS-020/027）。問題は並列性でなく手順保証だった | **低優先のまま** |
| E6 | AGENTS.md 互換 | 新情報なし | **保留のまま** |

---

## 7. 進化提言（次ロードマップ案）

DIRECTIVE-001 の判断原理——「**LLM が判断し、構造が証明する**」——で並べた推奨順:

1. **install 契約の完全化**（fix-forward P1×2: skill 到達性＋templates 配布）。F6 で確立した「静的検査は repo しか見ない」教訓の最終消化。scaffold smoke を「全 skill の起動経路・全テンプレ参照の解決」まで拡張すれば、この系統の欠陥クラスを恒久封鎖できる
2. **judge card の修復と push 化**（fix-forward P1）。root cause は決定論再現済みで修正コストは小さく、B2 の投資（tri-state・ack・カード生成）が初めて非エンジニアに届く
3. **ゲート検査の Dev/Client 対称化**（fix-forward P1）。ACCEPTANCE の存在保証は E2 の前提整備でもある
4. **E1 着手**（brainstorm→grill-plan）。failure_tracking・保守 record・claims 検査を同一の evidence-log 基盤に載せる設計が費用対効果最大
5. **P2/P3 の小修繕バッチ**（允許リスト精密化・エラーメッセージ・platforms.md・commit checkpoint・git init・出力言語規定）
6. **brainstorm テーマ**（§5.2）: 特に「機会主義的納品」と「公開ブロック時の部分納品」は実走で確定した現実需要
7. **次回行動レビュー**: 弱いモデル（Sonnet 等）での同一シナリオ再走。本レビューの「LLM任せで成功」帯（review 手順・S3・納品即興）がどこまで崩れるかを測ることで、構造投資の優先度が実測で決まる

---

## 8. 付録: 観測索引・再現手順・コスト

### 8.1 観測ログ索引（全35件。詳細は observations/log.md＝workspace バックアップ参照）

| OBS | 一行要旨 | 判定 |
|-----|---------|------|
| 001 | setup.sh は git init をしない（implement 中にブロック発生→LLM 自律解消） | 🟡 |
| 002 | setup.sh 出力に SKIP (exists) 混在（実害なし・体験軽微） | 🟡軽微 |
| 003 | AskUserQuestion が headless で is_error→自由文へ自然縮退（×5回再現） | 運転環境固有 |
| 004 | state-machine の skill ロード指示が Skill ツールで実行不能（契約不整合） | 🔴候補 |
| 005 | check-control-plane 発火🟢＋読み取り操作への deny 文言不適合🟡 | 🟢/🟡 |
| 006 | ハーネス記帳の英語実況がクライアント画面に漏出 | 🟡 |
| 007 | S1（曖昧・撤回・矛盾）を構造＋LLM で受け止め | 🟢 |
| 008 | client_ready_for_dev: 承認体験は良形（LLM 産）だが exit-check 逆転・judge card 不在 | 🟡 |
| 009 | 翻訳マッピングの質（役割分担の好例） | 🟢 |
| 010 | 非エンジニア judge 評価: 承認実感あり・内部記帳漏出が信頼感を削る | 🟡 |
| 011 | セッション復帰（日またぎ）が設計通り | 🟢 |
| 012 | **skill テンプレが install 先に未配布（7 skill×9 参照が死ぬ・F6 同型）** | 🔴 |
| 013 | brainstorm 進行品質（ゲート保留・平易翻訳維持） | 🟢 |
| 014 | brainstorm→plan 遷移・planner routing・task_size 正直昇格 | 🟢 |
| 015 | セッション締めの状態管理（再開ポイント・ローテーション） | 🟢 |
| 016 | TaskCompleted hook の evidence 違反検出（メッセージは誤誘導気味） | 🟢/🟡 |
| 017 | implement 完走: TDD 行動遵守完全・34テスト・教訓記録 | 🟢 |
| 018 | S2（仕様変更）を構造で受け止め: テスト先行・PRD 反映 | 🟢 |
| 019 | **judge card が実走で一度も表示されない（pull 型のみ・構造トリガー不在）** | 🔴 |
| 020 | **review が skill 未ロードのまま実行（起動不能 frontmatter・対照表/盲検2次 不発）** | 🔴 |
| 021 | M1 解決: 仕様・テスト・実装の三点同期 | 🟢 |
| 022 | update-gate.sh が `2>&1` で false-deny（正規経路の遮断） | 🟡 |
| 023 | **judge 実体が UTF-8 crash（root cause 決定論再現済・実 Web 案件でほぼ常時再現しうる）** | 🔴 |
| 024 | qa の誠実な縮退（skipped-with-reason の tri-state） | 🟢 |
| 025 | implement〜qa で commit ゼロ（checkpoint 規定なし） | 🟡 |
| 026 | **qa ゲート3層連鎖が commit ゼロを強制修正（創発的 defense-in-depth）** | 🟢🟢 |
| 027 | security は skill 手動 Read で盲検2次まで完全実行（OBS-020 との A/B 対照） | 🟢 |
| 028 | deploy: アカウント境界の誠実停止・platforms.md に Netlify 欠落 | 🟢/🟡 |
| 029 | 非エンジニア向け deploy ガイド: 高品質だが全て LLM 即興 | 🟢/🟡 |
| 030 | **「公開できました」を二重実測→404 検知→ゲート誠実保持（Completion Rule の最良証拠）** | 🟢🟢 |
| 031 | **マニュアル正規機械が3欠陥複合で全段不発→非正規パスに即興生成** | 🔴 |
| 032 | 成果物説明も非正規パス即興（納品4点の全面置換パターン確立） | 🟡→🔴 |
| 033 | **3失敗停止ルールが完全発火（second-opinion/failure_tracking/待機）。簿記は自己申告** | 🟢🟢 |
| 034 | **UAT 正規機械の二重死亡（skill 起動不能×ACCEPTANCE 上流欠落）・循環検証** | 🔴 |
| 035 | S3: triage 満点級だが LLM任せ・maintenance 機械不発・record 欠落 | 🟡 |

### 8.2 主要再現手順

- **OBS-012**: `bash bin/setup.sh --profile=full --target=<dir>` 後、`<dir>` に `templates/` が無いことを確認。`grep -r 'templates/' .claude/skills/*/SKILL.md` で死参照を列挙
- **OBS-020/031/034/035**: `grep -l 'disable-model-invocation: true' .claude/skills/*/SKILL.md` のうち `user-invocable: false` 併記のものは起動経路なし
- **OBS-023**: install 先（commit なし・node_modules あり）で `python3 scripts/build-judge-card.py --gate review --root .` → UnicodeDecodeError で🟡縮退
- **OBS-034 の上流**: sandbox の `docs/requirements/` が PRD.md のみであること、`docs/STATUS.md` の client_ready_for_dev=approved を突合
- transcript 一式: sandbox 側 `transcripts/s0〜s10-*.jsonl`（解析は `observations/summarize_transcript.py`）

### 8.3 コスト台帳

Phase 0-1: $3.79 / s4: $3.52 / s5: $8.17 / s6: $2.01 / s7: $24.64（429 部分 $2.17 含む） / s8: $3.19 / s9: $2.46 / s10: $0.31 — **計 ≈ $48.1**（Opus 4.8・headless）。参考: plan/review/security 等の subagent 重フェーズがコストの過半。

### 8.4 レビューの限界

- 実デプロイなし（charter §6）: deploy ゲート承認・ship/docs フェーズ・dev_ready_for_client・external_evidence の成功時記帳は**未観測**（⚪相当の領域。ただし「公開ブロック時の挙動」という代替観測で OBS-030/033 を獲得）
- 単一モデル（Opus 4.8）: 「LLM任せで成功」帯の下方感度は未測定（§7-7 で次回提言）
- 単一案件・単一ペルソナ: S(1 file)/M サイズの軽量経路・複数人クライアントは未走行
