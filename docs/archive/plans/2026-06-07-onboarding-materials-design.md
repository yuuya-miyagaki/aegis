# 設計: aegis オンボーディング教材（2026-06-07）

## 目的

1. **習得**: 宮垣さん自身が aegis を「使いこなせる」ようになる（操作の習熟）。
2. **説明**: 将来 aegis を使う人（**非エンジニア中心**）に宮垣さんが説明できるようになる。

ブレスト合意: 北極星（非エンジニアが上流〜保守まで非スラップを作れる）と整合させ、非エンジニアを主読者に置く。

## 既存資料とのギャップ

- ある: README（reference・install・版履歴）／`architecture-overview.md`（構造の深掘り）／`/tutorial`（terse な Dev flow 5手順）。
- 無い: **使い方を習得する導線**と**他者に説明する材料**。本教材はこの空白を埋める（reference は重複しない）。

## 成果物（3点・日本語・`docs/onboarding/`）

framework repo のメタ文書。ミラー/契約対象外。README から1リンク（Quick Start 付近）。索引 `README.md` を置く。

### ① `01-hands-on-reservation.md` — フルサイクル・ハンズオン
題材は**中規模の予約管理システム**（会議室・備品予約／カレンダー連携／フロアマップ／サービス依頼〔呈茶・アテンド〕）。
方針: **Client で全体を設計 → タスクサイズ振り分けで1スライス（会議室予約の重複チェック）を Dev で TDD→UAT→保守 まで通す → 残り領域は次イテレーション**（反復モデルも体得）。各段で「打つコマンド／Claude への頼み方／何が起きるか／どの hook・ゲートが効くか／なぜ止まるか」を明記。

構成:
0. 準備: `bin/setup.sh --profile=full --target=<tmp>` で scaffold → Claude Code を開く → `/status`。
1. Client: onboard→discovery→requirements(PRD=システム全体)→scope(SCOPE/NFR・初回は会議室予約に絞る)→acceptance(ACCEPTANCE)→handover(TO-DEV)→`client_ready_for_dev` 承認（モード遷移体験）。
2. Dev: brainstorm→plan(会議室予約の重複チェック)→implement(**TDD**・`check-gate`/`check-tdd` で止まるのを体験)→review→qa(**B1 テスト強度ドリル**)→security→ship。
3. UAT: `uat` で ACCEPTANCE 照合→`docs/handover/UAT-RESULTS.md`→`dev_ready_for_client`（**UAT 存在チェック**体験）。
4. handover: TO-CLIENT＋MANUAL(`user-manual`)＋RUNBOOK(`maintenance` Part A)。
5. 保守: 本番バグ（例「日跨ぎ予約で重複検知が漏れる」）→ `maintenance` Part B→`bug-diagnosis`→bugfix→RUNBOOK 履歴記録。
6. 次の反復: 備品/カレンダー連携/フロアマップ/サービス依頼は次イテレーションへ。

### ② `02-explainer.md` — 非エンジニアへの説明ペラ
- **ひと言ピッチ**（1文）。
- **たとえ**: 工事現場の「監督＋検査官」＝工程を勝手に飛ばさせない仕組み（要承認なら別案も検討可）。
- **なぜ価値があるか 3点**: 上流から固める／品質ゲートで非スラップ／保守まで一貫。
- **ただの AI 任せとの違い**: 決定論 hook（PaC）が「人の確認なしに飛ばす」を物理的に止める。
- **30秒トーク台本＋3分版**の話し方、**刺さる相手**。

### ③ `03-cheatsheet.md` — 手元早見表
- スラッシュコマンド8種（/status /gate /judge /next /recover /retro /tutorial /validate）。
- ゲート8種の意味（client_ready_for_dev, brainstorm, plan, review, qa, security, deploy, dev_ready_for_client）。
- モード・フェーズ図（Client / Dev）。
- 主要 hook と「なぜ止まるか」。
- 承認・na・reset・ack 操作（`update-gate.sh`）。
- タスクサイズ早見（S/M/L とゲート省略）。

## 正確性の担保

- 数値・コマンド・hook 名・ゲート名・skill 名は**現行 v1.3.2 の実体**に一致させる（`architecture-overview.md` 刷新で確立した正本＋実ファイルで照合）。
- ハンズオンの手順は**実際に scaffold して通せる**ことを前提に書く（少なくとも各コマンドの存在と挙動は確認済みのものだけ載せる）。

## 非対象（YAGNI）

- 実際の予約システムを完全実装すること（題材・スライスのみ）。
- reference の重複（README/architecture-overview にあることは要約＋リンクで済ます）。
- 動画・スライド生成（テキスト教材に限定）。

## 完了条件

- 3ファイル＋索引が `docs/onboarding/` に揃い、内容が v1.3.2 実体と一致。
- README から導線リンク。
- ハンズオンのコマンド/挙動が実体と齟齬しない（要所をスポット確認）。
