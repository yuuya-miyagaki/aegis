# Aegis 二重網羅レビュー 2026-07-19 — Codex×Fable 突合・裁定・ロードマップ

> 対象: aegis v1.31.1（HEAD `77566eda7d15cb70d6ca68377fdbd764834d6fe5`）
> 方法: 外部 Codex（隔離）と盲検2次 Fable（隔離 clone）を層1共通6次元＋層2特化で並行盲検レビュー → 親（本セッション）が突合し、乖離・片方のみの高リスク所見を**自身の実走で裁定**。
> 生レビュー正本（証跡）: `docs/codex-review-2026-07-19.md`・`docs/fable-review-2026-07-19.md`。方法論: `docs/specs/2026-07-19-iter74-dual-review-design.md`。
> 前回正本: `docs/full-review-2026-07-06-six-dimensions-evolution.md`（R1〜R10）。

---

## 1. エグゼクティブサマリ

**総合判定: 決定論的 moat の骨格は健在。ただし「最終の2入力＝生シェル文字列（moat）と生テスト出力（evidence）」に、実走再現できる欠陥が2件ある。次の進化は機能追加でなく、この2つを構造化 argv と実行イベントへ一本化すること。** 両レビュアーが独立にこの同一結論へ収束した。

裁定を通った**確定 P0（親が実走再現済み）**:

1. **MOAT-BYPASS（Critical・reproduced）**: `check-destructive.sh`／`check-secrets.sh` が空クォート トークン分割で回避可能。`g""it a""dd .e""nv` は bash では正規の `git add .env`（secret 漏洩）だが **secret DENY が ALLOW に落ちる**。`r""m -rf` も ASK を回避。**SF-001 で control-plane 側には実装済みの token 化防御が、この2フックに伝播していない**非対称。
2. **EVIDENCE-FORGE（High〜Critical・reproduced）**: `pytest; true` / `pytest || echo` / `pytest | tee` / 偽 runner 出力で、**失敗テスト・未実行が green 認定**される。marker は「本体実行」しか証明せず、judge は `status=ok`（exit code 由来）だけで green にし、出力の `N failed` を再照合しない。SF-012/SF-014 の原理天井が現行 HEAD で生存。

裁定を通った**確定 High/Medium**:

3. **LOCALE-1（Medium・reproduced・iter73 の主張を反証）**: `check-runtime-state.sh` が不正 UTF-8 バイトで `tr: Illegal byte sequence` crash＝**fail-open**。iter73 設計正本の「runtime-state は crash せず＝同型不成立」は実測で誤り。`LC_ALL=C` 一行で解消。
4. **TEST-002（High・source＋partial）**: B1 drill が import/crash mutant を「テストに殺された」と数える（意味変化の証明なし）。
5. **MODEL-1（Medium・reproduced・known-broken）**: 品質役（security/planner/reviewer/qa）が `opus`=Opus 4.8 に契約固定。Fable 5 セッション（現行）では**最重要役ほど弱いモデル**で走る。`fable` は `ALLOWED_MODELS` に無い。前回 R5 の反転が生存。
6. **HARNESS 群（Medium・reproduced 構造ギャップ）**: deny/block は Claude Code が厳密 JSON 形を honor する前提のみに依存。整合の自動検証が無く、drift 検知は subset-only、時間 backstop は休眠（~2026-12）。Claude Code の schema 変更で**全 moat が最長半年 無言に fail-open**しうる。
7. **L0 肥大／budget 未強制（Medium・reproduced）**: STATUS.md ~6.5k tok（76% が session_history）・CLAUDE.md は 650語上限で余白0。**budget は常時ロードの2ファイルを計測していない**うえ単位が CJK を ~6x 過小計数。thin L0 が未強制。

**進化の一言（両者収束）**: 「危険操作は argv で判断し、テスト事実は実行イベントで判断する。文字列は説明に使い、真実の決定には使わない。」

---

## 2. 二重レビューの健全性チェック（突合前提）

| 項目 | Codex | Fable | 突合影響 |
|---|---|---|---|
| 対象 SHA | 77566ed ✅ | 77566ed ✅ | 一致 |
| 実行場所 | **メイン repo に直書き**（clone せず） | 隔離 clone `/tmp/aegis-fable` | Codex は dirty tree（iter74 の STATUS/specs）が見えたが「user-owned」と認識し不変・レビュー対象外に。**フック等の対象コードは 77566ed で同一**＝突合有効 |
| grep 実装記録 | 記録なし（locale は C.UTF-8） | **BSD grep 2.6.0-FreeBSD を明示＋対話 grep が ugrep に化ける汚染を警告** | Fable の方法論優位。**作者の iter72/73「実測」の一部は対話 ugrep 由来で汚染の可能性**（別途留意） |
| 網羅 | COMPLETE / 実行 PARTIAL | 層1+層2 完走 | 双方十分 |
| 生出力 | 主要所見に添付 | 全 severity 所見に親実走生出力 | 双方 reproduced 検証可能 |

**メタ所見**: Codex がクローンでなくメインで走ったのは手順逸脱だが、対象コードは同一コミットで無影響。次回は clone 起動を徹底。Fable の「対話 grep=ugrep」観測は、**作者自身の過去の locale/byte 実測結論を検証し直す価値がある**（フック実走で取り直すべき）。

---

## 3. 突合マトリクス（層1＝共通・乖離が最重要シグナル）

| 次元 | Codex | Fable | 分類 | 親裁定 |
|---|---|---|---|---|
| moat（quote-split） | **MOAT-001 Critical** | 「健在」＋偽陽性を自己棄却 | **乖離** | **Codex 正**。Fable は token 内空クォート形を未攻撃（平文 decoy のみ試行）。親再現で確定 → §4.1 |
| test-strength（green 偽造） | TEST-001/SF-012 **Critical** | TEST-1 **Medium** | 一致（機構）／乖離（severity） | 機構確定。severity は §4.2 で較正 |
| locale-byte（掃討完全性） | LOCALE-001 「closed」 | **LOCALE-1 Medium known-broken** | **乖離** | **Fable 正**。Codex は runtime-state を未攻撃。親再現で確定 → §4.3 |
| test-strength（B1 mutant質） | **TEST-002 High** | （test-strength テーマで整合） | 片方（Codex 深掘り） | 確定（source＋partial）→ §4.4 |
| regression（model pin） | 「回帰なし／範囲外」 | **MODEL-1 Medium known-broken** | **乖離**（insider/outsider） | **Fable 正**。Codex は model-tier 比較を範囲外に。config 事実 → §4.5 |
| north-star（L0 肥大） | NORTH-001 Medium | CTX-1/2/5・NORTH-2 | **一致** | 確定・高確度 → §4.6 |
| SF 再裁定 | SF-011/013/015/016 OPEN 妥当・F-CRIT-1 closed | 同左 | **一致** | 確定（現状維持・Low） |
| harness（層2 Fable） | — | HARNESS-1〜4 | 片方（Fable 固有） | §4.7 |
| distribution（層2 Codex） | DIST-001/002/003 | — | 片方（Codex 固有） | §4.8 |
| context/model（層2 Fable） | — | CTX 群・MODEL-2 | 片方（Fable 固有） | §4.6/4.5 に統合 |

**設計検証**: 2層ハイブリッドは機能した。(a) 収束＝green 偽造・L0 肥大で高確度、(b) **層1の乖離が2つの実バグを摘発**（MOAT-001＝Codex のみ／LOCALE-1＝Fable のみ・互いに相手の盲点）、(c) 層2特化で非重複カバー（配布=Codex／harness・model=Fable）。iter72 の「乖離＝バグの在処」が再現された。

---

## 4. 確定所見（親の実走裁定つき）

### 4.1 MOAT-BYPASS（Critical・reproduced・SF-001 の未伝播）

**親再現（HEAD 77566ed・生出力）**:
```
check-destructive  r""m -rf /tmp/x         -> rc=0 {}                     [ALLOW]   （平文 rm -rf は ASK）
check-secrets      g""it a""dd .e""nv      -> rc=0 {}                     [ALLOW]   （平文 git add .env は DENY）
変種              r\m -rf /tmp/x           -> ALLOW
変種              "rm" -rf /tmp/x          -> ALLOW
```
`r""m`/`r\m`/`"rm"` は bash では全て `rm`、`.e""nv` は `.env`。**secret の DENY を突破**するため、フレームワーク自身の脅威モデル（SF-001 が同クラスを「非 framework エージェントが任意書込み＝Critical」と認定）に照らし **Critical**。

**根本**: SF-001（iteration 32-35）は shlex トークン化＋パス解決で quote-split を control-plane 書込み検出に対し網羅閉鎖した。**しかし `check-destructive.sh` の破壊語検出と `check-secrets.sh` の `.env` 検出は生正規表現のままで、この防御が伝播していない**（親確認）。＝moat の quote-split 耐性がフック間で非対称。

**修正**: SF-001 の token 化 primitive を destructive/secrets の語判定へ一般化（Codex の「conservative lexer / shlex token view」と同方向・**primitive は既にコードにある**）。`git commit -m "fix STATUS.md"` 等のクォート内メッセージ救済（OBS-006）を壊さないこと。effort **S/M**。

### 4.2 EVIDENCE-FORGE（washed-green／fake-output・High〜Critical・reproduced）

**親再現（生出力）**:
```
marker verdict（exit arg=0・"1 failed" サマリ）:
  "python3 -m pytest -q; true" -> true
  "pytest || echo done"        -> true
  "pytest | tee log.txt"       -> true
fake runner:
  "pytest-not-installed || printf forged" + 偽 pytest 出力 -> marker true
```
judge（`build-judge-card.py:312`）は `status=="ok"` のみで green 判定＝exit code 由来 status を洗浄すれば失敗が green。**severity 較正**: 指示書 rubric「reproduced＋到達可能な forged green＝Critical」に厳密に従えば Critical（Codex）。一方これは**外部からの moat 突破でなく evidence 自己偽造**（SF-012/SF-014 の既知天井）＝Fable は Medium。**親裁定: P0・"High〜Critical（evidence-integrity）"**。`|| echo`/`; true` は pipefail 非依存で無条件 exit0＝**事故的到達が現実的**（非エンジニア/AI が書く典型）ゆえ Low 据置は不適。中核約束「evidence-based completion」が North Star 条件下で破れる。

### 4.3 LOCALE-1（Medium・reproduced・iter73 の完全性主張を反証）

**親再現（生出力）**:
```
check-runtime-state  echo x > docs/STATUS.md          -> rc=0 {}                       [allow]
check-runtime-state  echo <0xFF> x > docs/STATUS.md   -> rc=1 ''  stderr:"tr: Illegal byte sequence"  [FAIL-OPEN crash]
同バイト -> check-destructive（iter73修正済）          -> rc=0 {}  （crash せず）
同バイト + LC_ALL=C -> check-runtime-state             -> rc=0 {}  （一行修正で解消）
```
iter73 は destructive/secrets の同一 crash を直しつつ「runtime-state は python3 抽出でバイト→空 CMD＝同型不成立」と記録したが、**python3 は surrogateescape でバイトを温存し空にならない**（Fable 実証・親再現）。到達性は valid-UTF-8 制約下ゼロ（モデルは 0xFF を emit しない）＝**Medium**（iter73 自身の較正と整合）。ただし本フックは非 framework モードで Bash 経由 runtime-state 改竄を止める唯一の PreToolUse ガードで、fail-open の落ち先が重い。**修正**: `INPUT=$(cat)` 直後に `export LC_ALL=C LC_CTYPE=C LANG=C`＋設計正本の訂正＋`test_hook_locale_byte.py` に crash-regression pin。effort **S**。

### 4.4 TEST-002（High・source＋partial・Codex 深掘り）
`run-test-strength-drill.py:645-649` は mutation run の outcome が `failed` なら理由を問わず `caught`。import/collection/runtime crash mutant も「assertion が検出」に化ける。`_parses` は構文可否のみ。**修正**: pytest adapter で collection/internal/setup error を `inconclusive`、test-phase failure かつ実行1件以上のみ caught。mutant は即死系でなく condition/operator/return の意味変化を優先。effort **M**（4.9 の attestation に統合）。

### 4.5 MODEL-1（Medium・reproduced・known-broken）＋MODEL-2
`security/planner=opus/max`・`reviewer=opus/xhigh`・`qa=opus/high` に契約固定。Fable 5（現行セッション・Mythos-class＝Opus 4.8 上位）では frontmatter が session model を outrank し、**品質役ほど弱い Opus 4.8、implementer/ui（inherit）が強い Fable 5**。`ALLOWED_MODELS={opus,sonnet,inherit}` に `fable` 不在＝品質役を上げる経路なし（`CLAUDE_CODE_SUBAGENT_MODEL` は一括降格のみ）。`OPUS_ONLY_EFFORTS` は文字列 "opus" に溶接＝tier でなく名前依存。作者は iter54 plan で「Fable 5 再ティア」を deferred 済み。品質 impact は hypothesis だが config 反転は事実。**修正**: `fable` を lineage alias 追加＋**非対称 pin（下方は opus 床・上方は session model 追随）**＋`MODEL_EFFORT_POLICY` を「≥opus」意味論へ。effort **M**。

### 4.6 L0 肥大・budget 未強制（Medium・reproduced・両者一致）
実測（親確認可）: STATUS.md ~6.5k tok（**76% が session_history**・1件 3-5k字の commit-essay）、CLAUDE.md 650語（**上限・余白0**）、rules ~0.95k tok。**`context_budget.py` は skills+rules のみ計測＝常時ロードの CLAUDE.md/STATUS.md を見ていない**うえ単位 `len(text.split())` が CJK を ~6x 過小。＝「budget green」が信用できず thin L0 が未強制。**修正**: budget を CJK-aware 化し CLAUDE.md/STATUS.md を計測対象に＋session_history の1件語数 cap＋全文は evidence-archive へ。effort **M**。（複雑性 NORTH-2: 最高結合 checker〔check_status×check_framework_contract〕統合・learnings_search 降格は effort L・別途）

### 4.7 HARNESS 群（Fable 層2・Medium・構造ギャップ）
- **HARNESS-1**: 全 deny/block が Claude Code の厳密 JSON honor 前提。整合の自動検証なし・drift 検知 subset-only（rename/削除を取りこぼす）・時間 backstop 休眠（~2026-12）＝schema 変更で全 moat が最長半年 無言 fail-open。**配布ユーザに最も刺さる**。
- **HARNESS-2/3/4**: TaskCompleted は exit-2 依存で fail-closed fallback なし／deploy-MCP matcher rename で無言停止（かつ WARN 止まり）／frontmatter 契約は自己参照検証のみ。
- **修正**: install/session-start に `verify-harness` smoke（既知 deny 入力→実 hook が実 block したか）＋control-plane/deploy matcher の drift を WARN→FAIL 昇格＋verified 日付一本化＋staleness 180→60日。effort **M**。

### 4.8 DISTRIBUTION（Codex 層2・Medium/Low・fresh-eyes 実測）
- **DIST-001**: onboarding が setup 直後に重複 `git commit` を必須化するが、setup は既に baseline commit を作る＝`nothing to commit` rc1 で初体験が壊れる。
- **DIST-002**: onboarding/cheatsheet が `deploy na` を案内するが checker は deploy n/a を必ず拒否（前回 R9 継続）＝**official golden path を機械が拒否**。
- **DIST-003**: `--dry-run` 無し・stamp は version のみ（profile provenance 欠落）。
- **修正**: docs を checker 契約に一致＋golden-path E2E test＋`--dry-run`/`--no-baseline-commit`＋stamp を version/profile JSON 化。effort **S/M**。
- **付随（iter74 自身が露呈）**: フレームワークに **research/analysis iteration type が無く**、分析タスクが review/qa/security/deploy ゲートに馴染まない＝North Star 次元の設計課題。

---

## 5. 改善ロードマップ（impact×effort・iter75+ テーマ分割）

> 原則（両者収束）: **regex/denylist を足し続けない**。2つの弱い代理（生シェル文字列・生テスト出力）を構造化 argv と実行イベントへ一本化する。各修正は「旧実装で赤・新実装で緑」の回帰テスト化を ship 条件にする（"1306 green" だけでは不足）。

| iter | テーマ | 含む所見 | effort | 完了条件 |
|---|---|---|---|---|
| **75（P0）** | **moat quote-split 一般化** | 4.1 MOAT-BYPASS | S/M | `r""m`/`g""it a""dd .e""nv` が ask/deny・`git commit -m "…STATUS.md…"` 等の正常形は誤拒否なし・回帰 pin |
| **76（P0）** | **evidence 整合＋locale 掃討完了** | 4.2 washed-green／src allowlist・4.3 LOCALE-1 | S/M | `pytest; true`/fake-output が green 不可・runtime-state の byte crash 消滅・設計正本訂正 |
| **77（P0/P1）** | **pytest execution attestation** | 4.2 の恒久策・SF-014 天井 | M（1-2 iter） | argv spawn＋structured event（executed/passed/failed/skipped/collection_error/exit）・`src=attested` のみ decisive green・fake 出力は event 不能 |
| **78（P1）** | **B1 を attestation に統合** | 4.4 TEST-002 | M | crash/collection mutant が caught 不可・意味変化 mutant は PASS |
| **79（P1）** | **model policy 非対称 pin** | 4.5 MODEL-1/2 | M | `fable` alias 追加・下方床/上方追随・contract が session tier を見る |
| **80（P1）** | **harness verification** | 4.7 HARNESS-1〜4 | M | `verify-harness` smoke・control-plane/deploy matcher drift=FAIL・staleness 60日 |
| **81（P1/P2）** | **配布・onboarding 整合** | 4.8 DIST・research-iteration-type | S/M | golden-path E2E 成功・dry-run・profile provenance・分析 iteration の gate モデル決定 |
| **82（P2）** | **L0 縮小・budget 実効化** | 4.6 CTX/NORTH | M | budget が CJK-aware で CLAUDE.md/STATUS.md 計測・STATUS ≤ ~700語・session_history 1件語数 cap |
| **（後続）** | 複雑性収支 | NORTH-2 | L | 最高結合 checker 統合・未使用抽象降格 |

**戦略ライン**: P0 の 75/76 は既存 primitive の再利用・reader 1点・一行修正が中心で低コスト高 impact。77（attestation）が「テスト出力＝真実」の原理天井を塞ぐ本命。79/80 は配布に向けたモデル/ハーネス staleness の対処で、**target user（非エンジニア）に最も刺さる失敗モード**を消す。

---

## 6. 意図的に追わないもの（ノイズ抑制の透明化・両者一致）
- Bash 全文法 parser の自作（conservative lexer に留める）。
- 全 test ecosystem の同時 adapter（Aegis 自身の pytest から）。
- 同一ユーザー権限内の署名/秘密鍵による擬似 attestation（trust boundary 増えず）。
- 常設外部 CI／vector memory／swarm／多人数承認（North Star 外）。
- SF-004/005（interpreter・extglob 名前分割）の格上げ（静的解析の原理限界・OS-lock 補完・脅威モデル外）。
- SF-016 Unicode 空白 matcher 再拡張（非 exploitable）。
- Low hardening（SF-011/013）を P0 の2 Critical より先に処理。
- test 数を増やすこと自体の目標化（各 test は claim/finding ID に紐付け）。

---

## 7. 次のアクション
1. 本正本をレビュー成果として確定（iter74 の deliverable）。
2. iter75 以降を上表の順で個別 iteration 化（各々 brainstorm→…→ship）。P0 の 75/76 を先行。
3. 生レビュー2本（codex/fable-review-2026-07-19.md）は証跡として保全。
4. 新規 SF 起票候補: MOAT-BYPASS（SF-001 未伝播・Critical）／LOCALE-1（iter73 反証・runtime-state crash）。既存 SF-012/014 は 76/77 で消化。
5. 作者の過去 locale/byte「実測」を、対話 ugrep 汚染を排して（実フック/`/usr/bin/grep` で）取り直す価値あり（Fable 方法論所見）。
