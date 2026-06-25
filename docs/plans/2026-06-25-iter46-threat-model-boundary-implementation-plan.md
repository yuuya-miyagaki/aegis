# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- full-review backlog の **C4**（gate 値パーサ乖離）と **G4**（secret ゲート scope）を、検証済みの verdict として `docs/security-followups.md` に明文化してクローズする。あわせて Aegis 脅威モデルを canonical 節に集約する。**docs-only・production code 変更なし。**

## スコープ境界（grill-plan 反映）

- **C1 は本 iteration 対象外**: C1（full-review:65）は「MultiEdit バイパスは現行 platform で**不成立**」という訂正 finding＝platform 解決済み。残る構造的留意点（`extract-input.sh:20` first-path-only／matcher のツール名ホワイトリスト）は別系統の robustness 課題で、本 docs タスクの対象外。backlog 行更新時に C1 の現状（訂正済み・残留留意点は別 iteration）を正しく表示する。
- **README §95 は触らない**（grill YAGNI）: §95 は control-plane path/Bash moat の posture で secret ゲートに言及せず、かつ既に `docs/security-followups.md` を参照している。secret ゲート行の追加は新規スコープ拡張＝不要。canonical 節（security-followups.md）が secret 境界の single source。
- canonical 節の参照関係: README §95 は既に security-followups.md を指している。`docs/architecture-overview.md` に脅威モデルの競合記述があれば 1 行ポインタで canonical 節へ寄せる（実装時に確認・無ければ何もしない）。

## 入力

- 参照要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（backlog C4・G4）
- 参照設計: `docs/specs/2026-06-25-iter46-threat-model-boundary-design.md`
- ブレインストーミング記録: `docs/specs/2026-06-25-iter46-threat-model-boundary-brainstorm-record.md`

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: **n/a**（docs-only。デプロイ対象の成果物なし。framework・M は deploy ゲート size-exempt）
- Database: **n/a**
- CI/CD: **n/a**

### 互換性確認

- next.config `output` 設定: **n/a**（Next.js プロジェクトではない）
- 上記がデプロイ先と互換であることを確認: **Yes**（デプロイ無し＝非該当）

### 認証方式

- 認証プロバイダ: **None**（フレームワーク内部ドキュメント変更）
- DEMO_MODE 予定: **n/a**

## Git 戦略

- main 直コミット（既存 iteration の運用＝feature branch ではなく main で iteration を回す）。push はユーザー確認のうえ `gh auth switch --user yuuya-miyagaki` 後に実施。

## ファイル構造（変更マップ）

- 変更: `docs/security-followups.md` — (a) 冒頭（イントロ直後・SF-001 の前）に `## 脅威モデル（canonical）` 節を新設 (b) **新規 `## 調査済み・非該当（NOT-A-VULN / by-design）` 節**を追加し、SF-007（C4・NOT-A-VULN）と SF-008（G4・by-design）をそこへ記録。**CLOSED 節（＝実在した課題を修正したもの）とは区別する**（grill-plan 致命1）。
- 変更: `docs/full-review-2026-06-24-hooks-gates-distribution.md:81` 付近 — backlog 行の C4・G4 を closed 化し SF-007/008 へポインタ。C1 の現状も正しく反映（grill-plan 致命2）。
- README.md: **触らない**（上記スコープ境界・YAGNI）。
- テスト: **なし**（docs-only。テスト可能な production code を追加しない）。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | security-followups.md の canonical 脅威モデル節＋SF-007＋SF-008 | C4 probe 証拠・G4 境界分析（設計ノート） |
| Task 2 | full-review backlog の closed 行＋SF ポインタ | Task 1 の SF 番号 |
| Task 3（条件付き） | README posture 整合 | Task 1 の脅威モデル文言 |

循環依存なし。

## タスク分解

### タスク 1: security-followups.md 拡張（canonical 脅威モデル + SF-007 + SF-008）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** 対象 `docs/security-followups.md` / テスト なし
**意図:** 脅威モデルを 1 箇所に正典化し、C4=NOT-A-VULN・G4=by-design を既存 SF 様式でクローズ記録。
**TDD:** n/a（docs。挙動変更なし）
**受入条件:**
- canonical 節は **(i) 何を確実に守るか**（gate 偽造不能・control-plane path 保護・事故的 secret commit 阻止）を**先に**述べ、**(ii) 守らない境界**（非 sandbox／非 exfil 耐性／非 content スキャナ／chmod 権持つ敵対者は対象外）を述べる。語彙は README §95 の確立表現「threshold-raising layer / not a sandbox」に揃える（grill 要検討2＝under-claim で新規ユーザーを過剰に不安にさせない）。
- SF-007 が C4 の verdict（bypass-direction 0 行・strict 化は tamper backstop 弱体化）に加え、**最小再構築キット**（grill-plan 致命3）を残す＝(a) 両パーサ所在 `frontmatter.sh:gate_value` / `check_status.py:extract_approval_map` (b) bypass 定義「bash が exact `approved`/`n-a` を返すのは clean トークンのみ＝両パーサが一致しないと allow にならない」(c) 試行 12 形の代表（trailing-space／doubled-quote／glued-token／quoted／comment-ish 等）(d)「strict 化は post-status-audit:129-130 の OLD/NEW 比較を `approved`↔`approved ` で同一視させ tamper を取りこぼす」。種別=`not-a-vulnerability（実証）`・コード変更なしと明記。
- SF-008 が G4 を by-design（D2 scope・commit chokepoint・exfil モデル外/futile）として記録。種別=`by-design boundary（accepted）`。exfil を「防げる」とは書かない。
**Deliverable:** [ ] canonical 節＋SF-007＋SF-008 が存在 [ ] 既存 SF 様式に整合 [ ] 過大主張なし [ ] SF-007 の再構築キットで第三者が verdict を再現可能

### タスク 2: full-review backlog 行の closed 化

**blockedBy:** Task 1 | **モデル:** `inherit`
**ファイル:** 対象 `docs/full-review-2026-06-24-hooks-gates-distribution.md`
**意図:** backlog の C4・G4 を closed にし SF-007/008 へポインタ。
**受入条件:** backlog 行が C4/G4 の closed 状態と SF 参照を示す。
**Deliverable:** [ ] backlog 行更新

### タスク 3: （削除 — grill-plan YAGNI）

README §95 は secret ゲートに言及せず既に security-followups.md を参照済みのため、触らない。canonical 節が single source。実装時に `docs/architecture-overview.md` に脅威モデルの競合記述があった場合のみ 1 行ポインタを追加（無ければ何もしない）。

## 事前準備

- [x] 対象ファイルは既存（security-followups.md・full-review doc・README）
- [x] ベースブランチ最新（main = origin/main = 8a8fbbe）
- [x] 外部サービス・API キー不要

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| full-review C4（gate 値パーサ乖離の再評価） | verdict=NOT-A-VULN を実証付きで記録・close | Task 1（SF-007）＋Task 2 | なし（docs） |
| full-review G4（secret ゲート scope の再評価） | verdict=by-design を threat-model 準拠で記録・close | Task 1（SF-008）＋Task 2 | なし（docs） |

全 backlog 項目（C4/G4）がタスクでカバーされている。

## 自己レビュー

- 仕様カバレッジ: C4・G4 とも SF エントリ＋backlog close でカバー。
- 曖昧さ: 「close」の意味を「NOT-A-VULN（C4）／by-design accepted（G4）」と明示し「修正した」と誤読されない文言にする。
- 境界整合: Task 2/3 は Task 1 の SF 番号を Consume＝Produces に一致。

## リスク

- リスク R1: verdict の過大主張（C4 を「修正」と誤記載／exfil を「防げる」と誤記載）。
  - 対策: SF-007=「NOT-A-VULN・コード変更なし」、SF-008=「exfil はモデル外で futile・防御主張しない」と明記。security ゲートで盲検検証。
- リスク R2: C4 の「strict 化は逆効果」主張が将来読者に伝わらず再び strict 化提案が出る。
  - 対策: SF-007 に「strict 化＝tamper backstop 弱体化」を理由付きで残す（LEARNINGS[tech] と二重化）。
- リスク R3: ドキュメント肥大。
  - 対策: 各 SF は簡潔に。ただし SF-007 の**最小再構築キット**（パーサ所在・bypass 定義・代表 12 形・strict 化の逆効果）は省略しない＝verdict 検証可能性を優先（grill-plan 致命3 と整合。フル probe スクリプトは残さないが、キットから 5 分で再構築できる粒度を担保）。

## 完了条件

- [ ] Task 1/2 完了（Task 3 は条件付き）
- [ ] status_doctor PASS / framework contract PASS（ref 整合）
- [ ] review ゲート（doc 明瞭性・正確性）approved
- [ ] qa ゲート approved（B1 drill は docs-only で auditable skip）
- [ ] security ゲート approved。盲検 security の合格基準＝(a) C4=NOT-A-VULN の主張が脅威モデル内で正しい (b) exfil をモデル外とする線引きが妥当 (c) 過大/過小主張がない (d) canonical 節の「守る/守らない」境界が正確。
- [ ] 過大な security 主張がないこと（grill-code で確認）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->
