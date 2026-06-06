# 設計仕様: B2 非エンジニア向け judge 可視化

> **状態: 確定（spec・grill-plan 反映済み）。** superpowers:brainstorming で①〜⑥承認 → grill-plan の致命1〜5を反映（claims 欠落=🟡 移行安全／テスト再実行を指紋キャッシュ化／ティア1無条件実行／ティア2を self-attested 正直化＋アドバイザリ限定／claims 形式固定・ref null=🟡）。次工程＝writing-plans。
> 起点: 監査 `docs/audit-report-2026-06-06.md` 優先度4 B2（哲学的所見 **P1**＝「非エンジニアが最終ジャッジャーだが、LLM レビュー結果を評価する手段がなく "LLM が OK と言えば信じるしかない" 単一障害点」）。Fowler 評「精緻な構造は統制の幻想／レビュアーは markdown を読みたくない」。

## 1. 目的とスコープ

非エンジニアが「LLM が OK と言ったから」だけでゲートを承認してしまい、LLM レビューが誤ったとき誰も気づけない単一障害点（P1）を壊す。ゲート承認の**意思決定の瞬間**に、LLM の判定とは**独立したシグナル**を並べ、非エンジニアが「内容を技術評価する」のでなく「**機械が出した🔴/🟡/🟢と次の一手に従う**」だけで go/no-go を踏める形にする。

**スコープ（v1）**: Dev の4ゲート（review/qa/security/deploy）に judge カード（ティア1機械事実）。第2意見（独立 LLM レビュー）は review＋security のみ。
**非スコープ（v1）**: qa/deploy の第2意見、`/judge` の全ゲートロールアップ、Client 側ゲート。将来 opt-in。

## 1.5 採用と移行（既存非破壊）

B2 を入れても**既存の進行中プロジェクト・テスト・example を即座に壊さない**ことを最優先する。

- **claims 欠落＝🔴 でなく🟡**: claims ブロックが無い/読めないゲートは「未検証・要確認」（🟡 アドバイザリ・ack で承認可）に**格下げ**する。ハードブロック（🔴）は「claims が**有り**かつ機械実測と**矛盾**した」決定論的ケースだけ。これで claims 未対応の既存フローは「🟡＋ack」で生き残り、エージェント更新後に本検査が効く。
- **ブロック権限はティア1機械事実のみ**: ティア2（第2意見）は v1 で**絶対にブロックしない**（🟡 止まり）。
- **段階導入**: 既存テストで pre_approve_gate を通すものは、claims を与えるか🟡許容（ack）に寄せる（writing-plans で棚卸し）。

## 2. ゴール

- **独立クロスチェック（Q1=B）**: 非エンジニアは「独立シグナル vs LLM 判定」の一致/不一致を見て判断する。純翻訳では「統制の幻想」が残り単一障害点を壊せない。
- **信頼度ティア（Q2=C）**: 機械事実（ティア1・最強）＞相互意見（ティア2）＞単一意見（ティア3・裏取り無し）。各シグナルにティアを明示し、非エンジニアが「機械保証／2意見一致／裏取り無し」を区別できる。
- **価値の重心＝ティア1（検証可能な独立性）**: ブロック判定（🔴）は**ハーネスが実測で裏取りできる機械事実だけ**が持つ。ティア2（第2意見）は P1 核心（構造健全性）への手当てとして残すが、**ハーネスは「2次が実走したか・盲検か」を検証できない**＝**self-attested（自己申告・低保証）と明示**し、アドバイザリ（🟡）に限定する。"検証できないものを検証済みのように見せない"＝統制の幻想を自分で犯さない。

## 3. 用語

- **judge カード**: ゲートごとにハーネスが機械生成する artifact。ティア別シグナル＋総合判定＋赤旗＋平易アクション。
- **総合判定**: 🔴 ブロック／🟡 要確認／🟢 承認可。ハーネスが下位シグナルから決定論的に算出。
- **構造化クレーム（claims）**: 各ゲートエージェントが機械照合可能な主張を構造化フィールドで記録したもの。
- **決定論的矛盾**: クレーム（主張）≠ ハーネスの実測。→ 🔴。
- **第2意見の相違**: 1次レビューと盲検2次レビューの verdict/論点が割れること。→ 🟡。
- **ack**: 🟡 を人間が明示承認する操作（理由付き・記録される）。

## 4. 採用方針

- **構築 = 案1（ハーネス組立・B1 踏襲）**: ハーネスが機械シグナルを集約し**赤旗を決定論的に計算**、`pre_approve_gate` で決定論的矛盾をハードブロック、LLM は平易説明のみ（赤旗を握り潰せない）。B1 の型（機械生成 artifact＋ハードゲート＋LLM 説明＋live 生成）をそのまま流用。LLM 組立（案2＝不一致を散文で薄める余地）・決定論だけ先（案3＝P1 核心を残す）は不採用。
- **クレーム捕捉 = 構造化（A）**: 目視比較（B）は弱い人間チェックに戻るため不採用。
- **不一致時 = 混合（Q4=C）**: 決定論的矛盾→ハードブロック／第2意見相違→アドバイザリ＋明示 ack。

## 5. アーキテクチャ概要

**重要なアーキ前提**: スクリプトは LLM サブエージェントを起動できない（Agent/Task は会話中の LLM のみ）。したがって役割を厳密に分ける:

```
[review/qa/security/deploy フェーズ中（LLM 主導）]
  └─ 各ゲートエージェントがレポートに claims: を構造化記録
  └─ review/security では LLM が「盲検の独立2次レビュー」を別ディスパッチし
        second_opinion: を記録（1次の verdict/コメントを見せない fresh context）

[ゲート承認時（ハーネス＝純スクリプト）]
  update-gate.sh <gate> approve
    └─ pre_approve_gate(<gate>) が build-judge-card.py を live 実行:
         1. レポートの ```claims``` を読む（ref null/不在→🟡・§6.2）
         2. ティア1機械検査を**無条件**実行（§6.3）: スタブ/secret は live grep、
            テストは指紋キャッシュ読み（再実行しない）、B1 verdict 読込 — LLM 不要
         3. 記録済み 1次/2次 verdict を比較 → 🟡 算出（2次はアドバイザリのみ）
         4. 総合算出（🔴優先＞🟡＞🟢）→ judge カード artifact を書く
    └─ 総合=🔴 → return 1（ブロック）
       総合=🟡 → ack 無し approve を拒否（`approve --ack "理由"` でのみ可）
       総合=🟢 → 通常承認
    └─ LLM がカードの「あなたが取るアクション」を平易日本語で記述（判定は不変）

[/judge コマンド（読み取り・状態変更なし）]
  └─ 同じ build-judge-card.py を実行して今いるゲートのカードをプレビュー
```

**整合性**: ティア1は嘘を実測で露見（🔴）。ティア2は「2次 artifact の存在＋比較」をハーネスが強制（1次が握り潰せない）。カードは承認時 live 生成＝偽造/staleness 不能（B1 同型）。"2次が真に盲検か"は LLM 行為のため決定論保証は不可（→ §11 限界）。

## 6. コンポーネント

### 6.1 judge カードビルダー（harness・新規）
- `scripts/build-judge-card.py --gate <gate> --root <root> [--report-out <path>]`。
- 責務: claims 読込 → ティア1再チェック → 1次/2次 verdict 比較 → 総合算出 → カード書込 → **tri-state 終了コード**。
- **終了コード（唯一の真実・三状態）**: `0`=🟢 承認可／`1`=🔴 ブロック／`2`=🟡 要確認（ack 必要）。総合判定はカード冒頭にも機械記述。
- **カード出力先**: `docs/qa-reports/judge-<gate>.md`（ゲートごと・上書き）。
- 純スクリプト（テスト scan・git diff・ファイル比較のみ。高コストなテストは記録読み＝§6.3。LLM 起動なし）。mirror 対象（example へ byte 同一複製・`MIRROR_FILES` 登録）。

### 6.2 構造化クレーム schema（形式固定）
ビルダーは claims を**そのゲートの既存 evidence ref**（`current_refs.<gate-ref>`）が指すレポートから読む（新パスを発明しない）。
- **形式は1つに固定**: レポート内の ` ```claims ` フェンス YAML ブロック（曖昧な「frontmatter かどこか」を排除・パース規則を一意化）。
- **ref が null / レポート不在 / claims ブロック不在 → 🟡「証拠未提出・要確認」**（クラッシュ・🔴 にしない＝§1.5 移行安全）。
```claims
tests_pass: true|false          # 全ゲート共通
no_stubs: true|false            # 変更コードに TODO/FIXME/stub/空実装が無い
no_secrets: true|false          # security
deps_clean: true|false          # security（依存脆弱性監査）
verdict: approve|reject|approve_with_notes
second_opinion:                 # review/security のみ（self-attested）
  verdict: approve|reject|approve_with_notes
  divergence_points: ["..."]
```

### 6.3 ティア1チェッカ（無条件実行・テストは指紋キャッシュ）
**機械検査はクレームの有無に関係なく無条件で実行**（claim を省略して検査を回避できないようにする＝ガミング穴封鎖）。claim が有り矛盾→🔴／claim 省略でも機械が問題検出→🔴／機械クリーン→🟢。
- **安価な scan は live 実行**（速い）:
  - `no_stubs` → **変更行**（B1 の `added_lines_by_file` 流用）にスタブパターン（`TODO|FIXME|XXX|NotImplementedError|pass\s*#\s*stub|placeholder`）を grep。
  - `no_secrets` → `hooks/check-secrets.sh` のパターン流用。
- **高コスト検査はテストを再実行せず記録結果を読む**（致命2・「数秒」死守）:
  - `tests_pass` → **指紋キャッシュ**: テスト結果を `{status, code_fingerprint}` で記録（`docs/qa-reports/test-result.json`）。ビルダーは現コードの指紋（B1 の指紋概念流用）と照合し、一致なら**再実行せず記録を使う**。不一致（コード変更後）なら1回だけ実走して更新。→ review→qa→security→deploy がコード未変更なら**スイートは1回だけ**。記録が無く実走も不能なら 🟡 未検証。
  - qa は B1 の verdict（`docs/qa-reports/test-strength.md`）を流用（二重実行しない）。
  - `deps_clean` → `npm audit`/`pip-audit` 等があれば実行（timeout 付き）。ツール不在/オフライン → 🟡 未検証（ブロックしない）。
- **ティア2（第2意見）の歯**: ハーネスは2次の実走/盲検を検証できないので、**`second_opinion:` ブロックの存在のみ強制**（review/security で欠落→🟡「第2意見なし」）。verdict 相違→🟡。**ティア2は決してブロックしない**（§2）。

### 6.4 ゲート結合（`pre_approve_gate` → `update-gate.sh` の三状態連携）
- `scripts/check_status.py` の `pre_approve_gate` に **judge ブランチ**（review/qa/security/deploy 承認時に 6.1 を実行）。B1 の qa ブランチと同型だが**三状態**を返す: ビルダー rc をそのまま伝播（`0`=🟢/`1`=🔴/`2`=🟡）。既存の prerequisite チェックで失敗した場合は従来どおり `1`。
- `update-gate.sh <gate> approve` は `pre_approve_gate` の rc を解釈:
  - `0` → 通常承認。
  - `1` → ブロック（🔴 または前提未達）。ack でも越えられない。
  - `2`（🟡）→ `--ack "<理由>"` があれば理由を記録して承認、無ければ停止し「`approve --ack \"理由\"` で承認可」を促す。
- 既存の `if [ $GATE_CHECK_RC -ne 0 ]` は三状態を見るよう改修。
- **既存呼出元の rc 解釈を棚卸し**（`test_extractors` 等が `rc!=0`=ブロックと解釈する箇所が🟡=2 を誤解しないよう writing-plans で対応）。
- **サイズルーティングと整合**: スキップされたゲート（例 deploy は M で省略）では judge ブランチを発火させない（state-machine の免除を尊重）。

### 6.5 ack 機構（`update-gate.sh` 改修）
- `update-gate.sh <gate> approve [--ack "<理由>"]`。🟡（rc=2）時のみ `--ack` が意味を持ち、理由を STATUS の session_history／judge カードに記録（監査可能）。素の approve は🟡で通らない。🔴 は ack でも越えられない。

### 6.6 `/judge` コマンド（新規）
- `.claude/commands/judge.md`。ビルダーを読み取り実行し、対象ゲートのカードをプレビュー（承認しない）。
- **対象ゲートの解決（phase→gate 写像）**: phase が judge 対象ゲート（review/qa/security/deploy）ならそのゲート。フェーズ間（implement 等）なら**次に控える judge ゲート**を対象（例 implement→review）。引数 `/judge <gate>` で明示指定も可。

### 6.7 LLM 側責務（agent/skill 規約）
- reviewer/qa/security エージェント定義に `claims:` 記録規約を追記。
- review skill（aegis-review-gate）と security skill に「**盲検2次レビューを別ディスパッチして `second_opinion:` を記録**」を追記。
- 各ゲートで LLM がカードの「あなたが取るアクション」を平易日本語で記述。

## 7. 設計詳細（確定・①〜⑥）

### 7.1 ①カード構造とティア
ゲート1枚・ハーネス機械生成。ティア1=機械事実（✅検証済・高信頼）／ティア2=**🔍 第2意見（self-attested・自己申告・低信頼）**／ティア3=単一意見（裏取り無し）。総合判定と🔴/🟡振り分けをハーネスが算出。LLM は「あなたが取るアクション」のみ。**ティア2はカード上で必ず「self-attested（自己申告・裏取り無し）」と明示**し、非エンジニアが機械保証と区別できるようにする（致命4 の正直化）。

### 7.2 ②ゲート別シグナル＋クレーム捕捉
6.2/6.3 のとおり。review=テスト緑/lint/スタブ scan/evidence-integrity、qa=B1/テスト緑、security=secret/依存/危険パターン、deploy=deploy-ready/build。クレームは構造化（A）でハーネスが実測再チェック。

### 7.3 ③整合性とゲート結合
承認時 live 生成。claims≠実測=🔴（ブロック）。第2意見相違=🟡（ack 要求）。`pre_approve_gate` で施行。クレームはハーネスが裏取り、第2意見は独立 artifact 比較。

### 7.4 ④第2意見の独立性（self-attested・アドバイザリ限定）
構造健全性のみ対象。**LLM が review/security フェーズ中に盲検（1次非開示・fresh context）＋視点替え（`reviewer-maintainability` 等の既存別観点）で2次をディスパッチし `second_opinion:` を記録**。ハーネスは artifact の**存在を強制**し verdict を比較して 🟡 算出（欠落も🟡）。**ハーネスは2次の実走/盲検を検証できない**ため、カード上で**self-attested と明示**し、**決してブロックしない**（ブロックはティア1機械事実のみ）。偽の「2次一致」が混じっても害は「🟡 取り逃し」に限定され、本当の問題はティア1が止める。v1 は review＋security のみ。

### 7.5 ⑤入口とアクション
ビルダーを2経路（承認時自動＋`/judge` プレビュー）。非エンジニアは機械の🔴🟡🟢＋LLM 翻訳の次手に従う。🔴=戻して直す／🟡=確認し納得なら `approve --ack "理由"`／🟢=承認可。

### 7.6 ⑥アーキ補正・fail-closed
§5 のアーキ補正（ハーネスは LLM を呼ばない・2次は LLM が記録）。fail-closed は §8。

## 8. エラー処理（fail-closed 一覧）

| 事象 | 挙動 |
|------|------|
| claims ブロック欠落/不正・ref null/レポート不在 | **🟡「証拠未提出・要確認」**（移行安全＝§1.5・🔴 やクラッシュにしない） |
| ティア1機械検査が検証不能（テスト記録無し＆実走不能等） | 沈黙🟢にしない → 🟡「未検証・要手動確認」 |
| クレーム≠実測（例 tests_pass:true だが赤）／claim 省略でも機械が問題検出 | 🔴 決定論的矛盾→ブロック（無条件検査＝§6.3） |
| 2次 `second_opinion:` 欠落（review/security） | 🟡「第2意見なし・要確認」（ブロックしない） |
| 1次/2次 verdict 相違 | 🟡 要確認＋ack 要求（ブロックしない） |
| ビルダーがクラッシュ/例外 | `pre_approve_gate` return 1（既定 BLOCKED） |
| 依存監査ツール不在/オフライン | 該当クレームを🟡 未検証（ブロックしない） |
| 🟡 で素の approve | 拒否（`--ack "理由"` を要求） |

## 9. テスト戦略（TDD red→green）

ビルダー単体（subprocess）:
- クレーム≠実測（tests_pass:true だが記録は赤）→ 🔴／exit 1
- claim 省略でも機械が問題検出（スタブ有り）→ 🔴（無条件検査）
- 全クレーム一致＋2次一致 → 🟢
- 1次/2次 verdict 相違 → 🟡（exit 2・ブロックしない）
- 2次 `second_opinion:` 欠落（review/security）→ 🟡
- **claims 欠落/不正・ref null → 🟡（exit 2・ブロックや例外でない＝移行安全）**
- スタブ scan が変更行の TODO を検出 → 🔴
- **テスト指紋キャッシュ**: 指紋一致なら記録結果を使い再実行しない／不一致なら1回実走
- ティア1検証不能（記録無し＆実走不能）→ 🟡（沈黙🟢でない）
- 例外 → fail-closed（exit 1）

ゲート結合（`tests/test_check_status.py`）— `pre_approve_gate`:
- 🔴 でブロック／🟡 で ack 無し拒否・ack 有り許可／🟢 で許可。
- judge ブランチが review/qa/security/deploy で発火。

その他: `/judge` 出力、mirror identity（ビルダー登録）、`update-gate.sh --ack` の理由記録。

## 10. 既存機構との結合点

- 新規: `scripts/build-judge-card.py`（＋example mirror・`MIRROR_FILES` 登録）／`.claude/commands/judge.md`。
- 改修: `scripts/check_status.py`（`pre_approve_gate` に judge ブランチ）／`scripts/update-gate.sh`（`--ack`）。
- 流用: B1 の `added_lines_by_file`・テスト実行ラッパ・`docs/qa-reports/test-strength.md`／`hooks/check-secrets.sh` のパターン。
- 規約追記: reviewer/qa/security agent（`claims:`）／aegis-review-gate・aegis-security-gate skill（盲検2次記録）。
- ドキュメント: architecture-overview に judge カードを反映。

## 11. 保証の限界（正直さ）

- **2次は self-attested（実走したか・盲検かを保証できない）**: 2次レビューのディスパッチは LLM 行為で、ハーネスは「`second_opinion:` の存在と相違」しか強制できない。**「そもそも2次を実走したか」「1次を見ずに回したか」は検証外**＝LLM が回さずに「一致」と書くことも可能。よって**カードで self-attested と明示し、ブロック権限を持たせない**（ブロックはティア1機械事実のみ）。これで「検証できないものを検証済みに見せる」統制の幻想を自分で犯さない。完全な独立性保証は将来課題（ハーネス側で2次入力を制限する仕組み等）。
- **ティア2は判断もの**: 第2意見はアドバイザリ。2意見が一致しても「両方間違う」可能性は残る（ティア表示で正直に提示）。
- **クレームは LLM 記述**: ただし機械照合可能なものは実測で裏取り（嘘=🔴）。照合不能なクレームは🟡 止まり。
- **v1 ゲート/第2意見スコープ**: qa/deploy の第2意見、Client 側は将来 opt-in。
- **スタブ scan の取りこぼし**: パターンベースなので巧妙な未完成は見逃しうる（B1 と相補・§12 的に明示）。

## 12. 次アクション
spec 自己レビュー → ユーザーレビュー → grill-plan → writing-plans。
