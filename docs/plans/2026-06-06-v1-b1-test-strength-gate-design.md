# 設計仕様: B1 テスト強度ゲート（mutation drill）

> **状態: 確定（spec・grill-plan＋計画時の偽造耐性修正 反映済み）。** superpowers:brainstorming で①〜④を順次承認 → grill-plan の致命1〜5＋章立て新設を反映 → **writing-plans 着手時に案B（指紋束縛）が Goal A を満たさない（ローカルハッシュは偽造可）と判明し、案A（承認時実走）へ切替**。指紋・改竄ハッシュ機構は撤去。次工程＝writing-plans。
> 起点: 監査 `docs/audit-report-2026-06-06.md` 優先度4 B1（哲学的所見 P2＝「"崩れない" の測定が欠落」／ライフサイクル能力⑥「機械的に正しい＋仕様遵守」⑫「保守」）。

## 1. 目的とスコープ

非エンジニアのユーザーが書かせたテストが「緑だが意味がない（バグを通す）」状態のまま納品される事故を、**決定論的に**防ぐ。qa フェーズで「テストが**各変更ハンクに仕込んだ mutant を実際に捕まえる**」ことを機械的に証明できない限り、qa ゲートの承認を拒否する。さらに結果を非エンジニアが判断できる平易な日本語に翻訳する。

> **証明できる範囲を正直に**: ゲートが保証するのは「**仕込んだ mutant が捕まる**」ことであり、「テスト全体が強い」ことではない。mutant の質・全網羅・非決定スイートは保証外（`§12`）。誇大に「テストが意味あるバグを全部捕まえる」とは主張しない。

**スコープ（v1）**: タスク単位・そのタスクで変更したコードのみ・mutant 1〜数個・ゼロ設定。
**非スコープ（v1）**: 本物の mutation ツール（Stryker/mutmut）、全スイート mutation、複数言語の網羅。これらは将来 opt-in。

## 2. ゴール

- **A（決定論的ブロッキングゲート）**: 証明できない限り qa 完了を拒否。判定はハーネスが決め、LLM の自己申告に依存しない。証明対象＝各変更ハンクの mutant 捕獲（テスト全体の強度保証ではない＝`§12`）。
- **C（非エンジニア向け翻訳）**: 合否と「次にやること」を平易な日本語で提示。

## 3. 用語

- **mutant**: コードに意図的に仕込む小さなバグ（比較反転 `>=`→`>`、境界±1、条件否定、早期 return 等）。v1 は**単一行の文字列置換のみ**（複数行変更・コード削除・設定変更には mutant を作らない＝`§6.1`・`§12`）。
- **捕獲（killed）**: mutant を入れたらテストが赤くなる＝テストがその振る舞いを守れている。
- **生存（survived）**: mutant を入れてもテストが緑のまま＝テストに穴。
- **ドリル**: 1 mutant について「仕込む→テスト実行→戻す→判定」する1サイクル。
- **baseline**: 無改変の現コードでのテスト実行結果。
- **code_fingerprint**: タスクの変更ファイル群の git diff から計算したハッシュ。verdict を「そのコード状態」に束縛する。

## 4. 採用方針

- **技法 = ゼロセットアップの仕込みバグ方式 → 採用案 = 案1（ハーネス再実行型・git-safe・fail-closed）**。
  - 非エンジニア＋手堅さを軸に案2（LLM 自己証明）を不採用。決め手は失敗の鳴り方: 案2 は**静か**（弱いテストのまま納品＝P2 そのもの）、案1 は**大きい**（止まって明示メッセージ→助けを求められる）。詰まる（回復可）＞静かに出荷（回復不能）。
  - 案1 の負荷は軽い: **ハーネス部分は小さく言語非依存**（テキスト書換＋シェル実行＋exit code 判定）。言語依存の判断（mutant 選定・テストコマンド）は LLM が担当＝aegis の「手順=LLM／アウトカム強制=harness」と一致。
- **ゲート結合 = 案A（承認時実走）**。当初は案B（成果物 verdict 信頼＋指紋束縛）を採ったが、writing-plans 着手時に**ローカルハッシュ/指紋は秘密鍵なしで偽造可能**（ドリル未実走でも `verdict: PASS`＋正しい指紋を手で書ける）と判明。これは Goal A「LLM の自己申告に依存しない」と正面衝突するため案A に切替。
  - **仕組み**: qa ゲート**承認の瞬間にハーネス（`pre_approve_gate`）がドリルを実走**し verdict を計算。PASS でなければ承認を拒否（return 1）。「ハーネスが今まさに実行」＝**偽造不能・staleness 不能**。
  - **「重い」懸念の解消**: mutant は少（1/ハンク）＋テストは関連テストにスコープ（`§6.5`）＝**数秒**。当初「案A=重い」は『全スイート×毎回』の過大見積りで、スコープ前提だと軽い。
  - **副産物＝単純化**: `code_fingerprint`（旧 §6.3）と改竄ハッシュ保管機構（旧 §7.2）が**丸ごと不要**に。staleness 窓も消える。最も脆い部品を撤去でき、手堅さが上がる。

## 5. アーキテクチャ概要

```
qa フェーズ（プレビュー＝人間の判断材料）
  └─ qa agent (LLM): 変更 diff を読む → 各変更ハンクに最低1 mutant を選定(file:line:原→改)
        → テストコマンド(関連テストにスコープ)/timeout を指定
        → ドリル入力仕様ファイルに記録(docs/qa-reports/test-strength-<task-id>.drill)
        └─ ドリルランナーを実走してプレビュー → ✅/⚠️ + 平易な説明 + (不合格なら)次にやること を提示
  └─ ユーザーが内容を見て qa ゲート承認を申請

qa ゲート承認（authority＝偽造不能なゲート判定）
  └─ update-gate.sh qa approve
        └─ pre_approve_gate("qa") が **ドリルを実走**(入力仕様ファイルを読む):
              各 mutant について ↓
                ドリルランナー (harness shell, 言語非依存):
                  baseline 2回(両緑＝安定必須) → 対象行==原 を検証 → 現バイト保存(temp)
                    → mutant 書込 → テスト実行(timeout付)
                    → 復元前: 現バイト==書込 mutant を検証(他プロセス改変なら温存・中断)
                    → temp で復元(trap で必ず) → 復元検証 → 捕獲/生存を機械判定
              網羅フロア＋追加行(+)を検証 → 集計
        └─ 全 mutant 捕獲＋フロア充足なら verdict=PASS → レポート(機械ブロック)を書き return 0(承認可)
        └─ 1つでも生存/未配置/失敗なら verdict=FAIL → return 1(承認拒否・blocked)
  └─ current_refs.qa = docs/qa-reports/test-strength-<task-id>.md（ハーネスが承認時に生成）
```
**偽造不能の根拠**: verdict は事前に書かれた値を読むのでなく、**承認の瞬間にハーネスが実走して計算**する。LLM は mutant と test コマンド（入力）を出すが、PASS を得るには「mutant を入れると実際に赤くなるコマンド」＝本物のテストを出すほかない。指紋もハッシュも不要。

**権限の分離（信頼の穴を作らない肝）**: 合否を決めるのは**ハーネス**（機械ブロック＋ゲート検査）だけ。LLM は mutant 選定と翻訳を担うが、**合否は1ミリも動かせない**。

## 6. コンポーネント

### 6.1 ドリルランナー（harness shell・新規）
- **入力**: 対象ファイル、mutant 仕様（`file:line:原→改`、単一行のみ）、テストコマンド、timeout 秒。
- **責務**: baseline 実行 → **対象行の現内容 == `原` を検証**（不一致なら行ズレとみなし中断・別行を破壊しない）→ 現バイト保存 → mutant 書込 → テスト実行 → 復元（`§7.4` の安全手順）→ 復元検証 → 1 mutant の捕獲/生存を exit code で返す。
- **性質**: 言語非依存（テキスト書換＋シェル実行のみ）。一度に1 mutant のみ active。単一行 mutant のみ扱う。
- **配置案**: `scripts/run-test-strength-drill.sh`（mirror 対象＝example へ複製・A5 の identity チェックに登録）。

### 6.2 レポート生成（ハーネスが承認時に書く）
- ドリル集計後に `docs/qa-reports/test-strength-<task-id>.md` の**機械ブロック**を書く。LLM 散文でなくハーネス出力。承認時（authority 実走）の verdict で上書き（プレビュー時にも書くが、ゲートを決めるのは承認時の再生成）。
- **`<task-id>` の出所**: STATUS.md の現タスク識別子（`iteration` 等の安定値）を源泉。task-id を解決できなければ fail-closed。
- 構造化ヘッダ（指紋は撤去済み・verdict は承認時の実走結果）:
  ```
  verdict: PASS            # PASS / FAIL（ハーネスが承認時に実走して決定）
  mutants_total: 3
  mutants_caught: 3
  baseline: green
  survived: []             # 不合格時は [path:line, ...]
  ```

### 6.3 ドリル入力仕様ファイル（LLM が書く・ハーネスが承認時に読む）
- qa agent が mutant 仕様と test コマンドを `docs/qa-reports/test-strength-<task-id>.drill` に記録。これが**承認時実走の入力**。
- 内容: 各 mutant の `file:line:原→改`、関連テストにスコープした test コマンド、timeout。
- **入力（LLM）と出力（ハーネス verdict）の分離**: LLM は入力を出すが、verdict は承認時にハーネスが実走して計算＝LLM は PASS を直接書けない。偽造を構造で排除（指紋・ハッシュ不要の核心）。

### 6.4 ゲート結合（既存 `pre_approve_gate` への結線）
- `scripts/check_status.py` の `pre_approve_gate(gate_name, root)` に **`qa` ブランチ**を追加（既存の `client_ready_for_dev` が `mapping.md` 不在で return 1 する**ハード block 前例と同型**）。
- qa 承認時の手順: 入力仕様ファイル（§6.3）を読む → ドリルランナーを実走（§7.4 の安全手順）→ 網羅フロア＋追加行検証 → 全捕獲なら verdict=PASS でレポート（§6.2）を書き **return 0**、さもなくば **return 1（承認拒否）**。
- `update-gate.sh qa approve` は既に `pre_approve_gate` を呼び rc≠0 で停止する（Explore 確認済み・line 104 付近）ので、**新ゲート・新フックは不要**。qa の ref キーは既存の `qa`（`GATE_REF_MAPPING["qa"]="qa"`）を再利用し、`current_refs.qa` にレポートを記録。
- 完了時の ref 存在は既存 `evidence_integrity_violations` がそのまま担保（qa=approved なら `current_refs.qa` 必須・ファイル実在）。

### 6.5 LLM 側責務（qa agent / qa-verification skill）
- 変更ハンク内から mutant を選定（`file:line`＋書換）。**各変更ハンクに最低1 mutant**（網羅フロア・致命的な選定漏れを防ぐ＝`§7.1`）。ハンク総数が多い場合の上限は `§11` の要否ルールに従う。
- **テストコマンドは関連テストにスコープ**する（フルスイートでなく変更箇所をカバーする最小集合）。総ドリル時間が上限を超える見込みなら `§11` に従い drill 縮約 or qa=n/a を申告（`§4` の「速さ死守」を運用で守る）。
- timeout を指定。
- レポートの**説明ブロック**を機械 verdict から枠決め打ちで生成（PASS のときだけ「合格✅」）。
- 不合格時、生存 mutant の file:line から「どのテストを足すべきか」を翻訳。
- **ハーネスが網羅フロアを検証**: 変更ハンクのうち mutant 未配置のものがあれば fail-closed（LLM の選定漏れを機械で捕まえる）。

## 7. 設計詳細（確定）

### 7.1 ①ドリルの実行単位・スコープ（承認済み）
- 置き場所＝qa フェーズ。既存 qa ゲートの承認条件に組み込む。
- 1ドリル＝変更コードに mutant を配置。各 mutant は「テストが守ると主張する振る舞い」を壊す。**各変更ハンクに最低1 mutant**（網羅フロア＝`§6.5`）。
- 合否＝**全 mutant 捕獲＋網羅フロア充足で合格**、1つでも生存 or 未配置ハンクありで不合格。
- **反ガミング（決定論・2段）**: ハーネスが検証 — (a) mutant の line が**そのタスクの diff の追加行（`+`）**であること（ハンク範囲内の文脈行＝無変更行に隠す経路を封じる。「範囲内」では不十分）。(b) 全変更ハンクが mutant でカバーされていること（薄い選定でロジックを未テストのまま通す経路を封じる）。base＝未コミット変更。

### 7.2 ②証拠とゲート結合（案A＝承認時実走）
- 採用＝案A。6.2〜6.4 のとおり。**verdict はハーネスが承認の瞬間に実走して計算**するため、偽造・staleness が原理的に不能。指紋・改竄ハッシュは撤去。
- **authority の所在**: ゲートを決めるのは `pre_approve_gate("qa")` の実走結果のみ。プレビュー（qa フェーズ）で書いたレポートを手編集しても、承認時にハーネスが再生成して上書きするので無意味。
- **PASS を得る唯一の道**: LLM が出した test コマンドが「mutant を入れると実際に赤くなる」本物のテストであること。空コマンド（常に緑）→mutant 生存→FAIL、常に赤→baseline 赤→fail-closed。よって PASS は実テストでしか出ない。
- **承認後の改竄耐性**: 承認は実走結果で確定済み。後からレポートを書き換えても gate 判定は変わらない。完了時の ref 実在は `evidence_integrity_violations` が担保。

### 7.3 ③非エンジニア向け翻訳（承認済み）
- 権限の分離（6.5）。判断アンカーは機械が出した ✅/⚠️ 記号。
- 矛盾しない翻訳＝機械 verdict から枠決め打ち生成。
- ゲート提示時は生の mutation ログでなく「✅/⚠️ ＋ 平易な説明 ＋（不合格なら）次にやること」。
- 例（合格✅）:「『割引計算』のコードにわざとバグ（`>=`→`>`）を仕込んだら、テスト〇〇が気づいて赤くなりました。→ このテストは意味があります。」
- 例（不合格⚠️）:「『割引計算』にバグを仕込んでもテストは緑のまま＝この部分は取りこぼします。→ **やること: 100 円ちょうどのケースのテストを追加してください。**」

### 7.4 ④fail-closed / 安全（承認済み）
- **revert は git checkout/stash/restore 不可**（タスクの未コミット作業を消す）。
- **バイト単位 save/restore（git 不使用・真実源は temp ファイル1つ）**: mutant 書込前に対象ファイルの現バイト列を temp ファイルへ保存（バックアップの真実源は temp に一本化。書込んだ mutant バイト列は復元前検証用に別途保持）。→書込→テスト→**復元**（`trap` EXIT/INT/TERM で必ず。クラッシュ・Ctrl-C・timeout でも実行）。
- **並行編集から作業を守る復元手順（致命的安全）**: 復元の直前に「**ファイルの現バイト列 == 自分が書いた mutant バイト列**」を検証する。
  - 一致 → temp の保存バイト列で上書き復元 → 再読込して temp と一致検証。
  - **不一致**（＝drill 中にエディタ保存・ウォッチャ・別セッションが書き換えた）→ **上書きしない**。第三者の編集を温存し、大声でエラー（ファイル名・temp バックアップ位置・「他プロセスが触ったため自動復元を中止。temp に元バイト列あり」）。git checkout 不可と同じ理由＝ユーザーの未コミット作業を消さない。
  - これにより「自分の安全 promise を自分の復元で破る」自己矛盾を排除。drill 実行中は対象ファイルを開く別プロセス（watch テスト等）を止めるよう `§11`/skill で案内。
- **baseline 緑＋安定が前提（flaky ガード）**: mutant 前に無改変コードでテストを**2回**実行。両方緑でなければ結論不能→fail-closed（赤＝「元から赤、先に直して」／1回緑1回赤＝「テストが不安定（flaky）、drill は信頼できない」）。これで「決定論的」の看板を実体で裏付ける。
- **一度に1 mutant・変更ファイル内限定**: クラッシュしても復元対象は既知の1ファイル。
- **timeout = 結論不能 = fail-closed**: 無限ループ等で timeout したら「捕獲」と数えず fail-closed（「テストがハングした。別 mutant か timeout 調整を」）。mutation 業界慣習（timeout=killed）は採らない（アサート無しでも捕獲扱いになる偽合格リスクを避ける）。テストコマンドは関連テストにスコープし（`§6.5`）、総ドリル時間が上限超過見込みなら `§11` で縮約 or qa=n/a。
- **既定は BLOCKED**: PASS は唯一のハッピーパス（baseline 2回緑＋全捕獲＋網羅フロア充足＋全復元検証 OK）でのみ。書込前 `原` 不一致・書込失敗・コマンド不在・復元前 mutant 不一致（他プロセス）・復元後不一致・baseline 赤/flaky・mutant 位置が追加行外・未配置ハンク・timeout・入力仕様ファイル不在/不正 → 非ゼロ終了＋（可能なら）復元＋ゲート blocked 維持。
- **承認時実走の安全**: この安全手順は**承認時（`pre_approve_gate`）の実走にも全て適用**。承認実走中も同じ byte save/restore・並行編集ガードでユーザー作業を守る。

## 8. エラー処理（fail-closed 一覧）

| 事象 | 挙動 |
|------|------|
| baseline 赤 | 結論不能→PASS 不可・ゲート blocked・「元から赤、先に直して」 |
| baseline が flaky（2回で緑/赤割れ） | 結論不能→blocked・「テストが不安定、drill 信頼不可」 |
| 書込前に対象行 ≠ `原` | 行ズレとみなし中断（別行を破壊しない）・blocked |
| mutant 位置が diff 追加行（`+`）外 | 拒否（反ガミング）・blocked |
| 変更ハンクに mutant 未配置あり | 網羅フロア違反→blocked・該当ハンク提示 |
| テストコマンド不在/起動失敗 | 非ゼロ終了→復元→blocked |
| テスト timeout | 結論不能→復元→blocked・「別 mutant か timeout 調整を」 |
| mutant 生存（1つでも） | verdict=FAIL→blocked＋生存 file:line を翻訳 |
| 復元前に現バイト ≠ 書込 mutant（他プロセスが触った） | 上書きせず温存・大声エラー（temp 位置提示）・blocked |
| 復元後バイト ≠ temp | 大声エラー（ファイル＋temp 位置）・blocked |
| 入力仕様ファイル（`.drill`）不在/不正 | 承認時に実走不能→fail-closed・blocked |

## 9. テスト戦略（B1 自身の検証・TDD red→green）

ドリルランナー単体（subprocess）:
- baseline 赤 → fail-closed（PASS が出ない）
- baseline flaky（緑/赤割れを注入）→ fail-closed
- 書込前に対象行 ≠ `原` → 中断（別行を破壊しない）
- mutant 捕獲 → そのドリルは pass
- mutant 生存 → FAIL＋生存位置を報告
- `trap` でクラッシュ/中断後もバイト復元される（復元検証）
- **並行編集**: drill 中に対象ファイルを別書込→復元前検証で不一致検知→上書きせず温存＋エラー（第三者の編集が残ることを検証）
- mutant 位置が追加行（`+`）外 → 拒否
- 変更ハンクに mutant 未配置 → 網羅フロア違反で fail-closed
- timeout → fail-closed
- 入力仕様ファイル不在/不正 → 承認時 fail-closed

ゲート結合（`tests/test_check_status.py`）— `pre_approve_gate("qa")`:
- 入力仕様の mutant が全捕獲 → 承認可（return 0）＋レポート生成
- mutant 生存あり → 承認拒否（return 1）
- 入力仕様ファイル不在 → 承認拒否（fail-closed）
- qa=n/a（理由付き）→ ドリル免除で従来どおり通る（既存 n/a フロー温存）
- 完了時: qa=approved で `current_refs.qa` 不在/実在しない → `evidence_integrity_violations`

mirror identity（`tests/test_mirror_identity.py`）: 新スクリプトが example へ複製され byte 一致。

全体: 既存 208/213 tests＋本 B1 分／eval tier 0-3／contract full+standard／drift／status strict／実 scaffold smoke を全 green に。

## 10. 既存機構との結合点（実装時に触る箇所の見取り図）

- 新規: `scripts/run-test-strength-drill.sh`（＋ example へ byte 同一複製）
- 改修: `scripts/check_status.py` の `pre_approve_gate` に **`qa` ブランチ**（承認時にドリル実走→PASS でなければ return 1）。`GATE_REF_MAPPING["qa"]` は既存再利用・`evidence_integrity_violations` は無改修で ref 実在を担保。
- 改修: `.claude/skills/qa-verification/SKILL.md`（qa agent にドリル手順＝mutant 選定・入力仕様記録・プレビュー・翻訳を記述）
- 改修: `scripts/check_reference_drift.py` の `MIRROR_FILES` に新スクリプト登録＋`templates/profiles/*.json`
- ドキュメント: `docs/qa-reports/` に成果物が出ることを architecture-overview に反映

## 11. ドリル要否（いつ drill する／しない）

既存の qa=n/a 経路を壊さないため、drill の要否を明示する。

**drill 必須**: qa ゲートを `approved` にするタスクで、テスト対象の**コード変更がある**場合。
**drill 免除（qa=n/a・理由付き）**:
- 非コード変更のみ（ドキュメント・設定・文言）。
- テストを伴わない/伴えないタスク（state-machine の task size 免除と整合）。
- 単一行 mutant を作れない変更のみ（削除・複数行のみ＝`§3`・`§12`。この場合は qa=n/a に理由「mutant 化不能」を記録）。

**ゲート結合の壊さない結線**: GATE_REF_MAPPING の「qa→test-strength レポート必須」は **qa=`approved` のときだけ**適用。qa=`n/a`（理由付き）は従来どおりレポート不要。これで既存 n/a フローを温存。

**運用ガード**: drill 中は対象ファイルを開く別プロセス（watch テスト・自動保存エディタ）を止めるよう skill が案内（`§7.4` の並行編集ガードの補完）。総ドリル時間が現実的でない場合はテストコマンドを関連テストに絞る（`§6.5`）か、正当な理由で qa=n/a を申告。

## 12. 保証の限界（保証しないこと・正直さ）

3年後の自分と引き継ぎ者のために、このゲートが**保証しない**ことを明記する。過大主張は信頼を損なう。

- **mutant の質は保証しない**: 仕込んだ mutant が「意味あるバグ」かは LLM 選定に依存。ハーネスは「追加行であること」「全ハンク網羅」までは強制するが、mutant が真に危険なロジックを突いているかは保証外。
- **テスト全体の強度は保証しない**: 証明範囲は「仕込んだ mutant が捕まる」ことのみ。未 mutant 化の振る舞い・到達しないパスは対象外。
- **非決定スイートでは保証が弱まる**: flaky テストは baseline 2回ガードで弾くが（`§7.4`）、根本的に決定論的スイートを前提とする。
- **単一行 mutant のみ**: 複数行変更・コード削除・設定変更は v1 で mutant 化しない（`§3`・`§11` で qa=n/a 経路）。
- **承認のたびに実走するコスト**: 案A は qa 承認時に毎回ドリルを実走する（mutant 少＋テストスコープ済みで数秒）。偽造不能・staleness 不能を得る対価。フルスイートで重い場合はテストスコープ（`§6.5`）か qa=n/a（`§11`）で回避。
- **git 前提**: 反ガミングは git diff に依存するため、対象は git リポジトリであること。未初期化なら明示エラーで `git init`＋commit を促す（初回コミット前は empty-tree 差分で全コードを added 扱いにフォールバック）。git の無いプロジェクトでは drill 不可。
- **非コードタスクの n/a は不可**: qa は `update-gate.sh` で n/a にできない（na は brainstorm/plan 限定）。テスト対象コードが無い場合は `.drill` の明示スキップ（`{"skip": true, "reason": "..."}`）で対応する（`§11`）。

これらは将来の opt-in（本物 mutation ツール・全スイート）で段階的に埋める前提（`§1` 非スコープ）。

## 13. 次アクション
writing-plans で実装計画へ（本書を入力に `docs/plans/` へ実装計画を作成）。
