# iter64 セキュリティレビュー（PRIMARY security role）

- 日付: 2026-07-09
- レビュア: security 1次（in-session・read-only 準拠。subagent の Plan Mode 制約と iter63 前例〔検証委譲のインフラ不安定〕を踏まえ、実挙動の敵対検証を coordinator が網羅）
- 手法: aegis-security-gate Step 0（公式 `security-review` 観点）→ moat 完全性を軸に脆弱性同定 → 実 git/敵対入力で実証 → 盲検2次を独立ディスパッチ
- 対象: iter64 diff = コミット 992ff4f（`hooks/lib/fingerprint.sh`＝E1 moat 単一所有者・`bin/setup.sh`＝self-heal 身元判定・テスト2）
- 仕様: `docs/specs/2026-07-08-iter64-fingerprint-tree-hash-design.md`
- 先行参照: `docs/qa-reports/iter64-review.md`（1次 in-session＋テスト強度＋盲検2次 approve_with_notes）／iter63-security.md 残余 (c)＝本 iter が解消する LOW-1

## 1. moat 完全性 — silent-green の非復活（最重要）

- fp = sha256(`tree:<committed>` ＋ framed 作業ツリー差分)。`committed` = 非 docs/.claude の committed tree-hash。
- **code コミットで fp が動く**: `git ls-tree -r HEAD` の対象 blob sha が変われば committed 行が変わる（実証: test_new_commit_changes_fp 維持・定数 tree mutant で RED）。**作業ツリー変更で fp が動く**（既存経路不変）。
- **意図せぬ除外なし**: 除外は `${tab}docs/`（素文字列）・`${tab}[.]claude/`（char-class リテラルドット）。bare-dot だと `aclaude/` を誤除外＝silent-green 穴になるため char-class で封鎖（実証: bare-dot mutant→resembling RED・slash-drop mutant→root-docs RED）。root 直下の `docs` ファイルは末尾スラッシュ要件で非除外。
- **degenerate token が変更を隠さない**: `committed=""`（docs-only 履歴/no-HEAD）は has-code fp と非 alias（実証: docs-only 145795… ≠ code b3d006…）。`oversize`/`nogit`/`error` は 64-hex でないため consumer が unverified 化（silent-green にならない）。`ls-tree` 失敗→`error`（実証・fail-closed）。
- verdict: **PASS**（silent-green の新規経路なし。旧 head:sha より narrow〔コード状態に反応〕かつ罠 r を解消）。

## 2. インジェクション（git ls-tree 出力・敵対的コミット済ファイル名）

- committed 部は `listing=$(git ls-tree ...)` → `printf '%s\n' "$listing" | grep -v …` → `printf '%s' "$filtered" | _fp_sha256`。`$listing` は printf の `%s` 引数（フォーマット文字列でない）＋grep の入力（パターンでない）。`eval` なし・変数値のコマンド置換再評価なし。
- **committed 部はファイル内容を cat しない**（ls-tree メタデータのみハッシュ）＝敵対的ファイルの**内容**が実行/注入される経路が原理的にない（旧 working-tree 部の cat より安全）。
- 実証: `a;rm -rf zzz.py` 等シェルメタ文字名のファイルをコミット→fp は clean 64-hex・注入マーカー（PWNED）非生成。
- 変名（git が quote する制御文字名）: committed 部は quote されても blob sha を含む行をハッシュするため内容変化は必ず検出（silent-green なし）。作業ツリー部は既存の quoted→error を維持。
- verdict: **PASS**（command/path injection なし）。

## 3. 移行の fail-closed（token 契約・consumer 透過）

- fp 定義変更で既存 record（旧 head:sha 算法）の fp は新 current fp と不一致。`read_test_result` は 64-hex ∧ fp==current を要求するため→**unverified（🟡 ack 可）**＝green にはならない（fail-closed）。marker_verified(v1.6.1) 導入時と同型の安全な移行。
- token 契約（64-hex|oversize|nogit|error・rc0）不変。consumer（build-judge-card.py `current_fingerprint`・evidence.sh）は 64-hex を不透明比較のみ＝内部表現（head:/tree:）非依存（実 grep: `head:` は fingerprint.sh のみ）。
- verdict: **PASS**（silent-green にならない fail-closed 移行）。

## 4. OR marker 厳格化が bypass を作らないか（＋iter63 LOW-1 の解消）

- 変更: `selfheal_unlock_target` 身元ガードを `.aegis-install-version` **OR** `hooks/lib/cp-lock.sh` から **stamp 単独**へ。これは self-heal（`chmod a-w` 解除）の発火面を**減らす**方向のみ（cp-lock.sh を持つが stamp を持たない非正規 target は今後 return〔黙〕→fail-closed 帰属エラー）。
- 正規 self-heal は不喪失: stamp(K-11・66e59e8・2026-06-13) は cp-lock(1e46e4d・2026-06-21) より先行導入＝OS-lockable install は必ず stamp を持つ（既存 T1 self-heal テスト維持）。stamp は locked CP 集合外で lock 下でも読める。
- 第2防御（`aegis_cp_verify` 実 lock 検出）・opt-out `AEGIS_SETUP_SELFHEAL=off` の fail-closed は不変。
- **iter63 security 残余 (c) LOW-1 を本変更が解消**（OR→AND stamp 単独で身元判定を authoritative 1本に締結）。
- verdict: **PASS**（bypass レバー新設なし・攻撃面縮小・LOW-1 クローズ）。

## 5. secrets / deps / ログ衛生

- secrets: 実 grep で diff にシークレット/クレデンシャル該当なし（誤検知1＝コメント `token==token`）。env の値を echo する箇所なし。
- deps: 純 bash＋既存 coreutils/git（awk/cat/grep/printf/sha256sum/shasum/sort/tr/wc）＝新規外部依存ゼロ。
- verdict: **PASS**。

## Findings

**HIGH: 0 / MEDIUM: 0 / LOW: 0**

OWASP Top 10 該当確認（非該当は理由付きスキップ）:
- Injection: §2 でトレース＋敵対入力実証＝なし（**該当・PASS**）。
- Sensitive Data Exposure: §5 実 grep で secrets 混入なし（**該当・PASS**）。
- Security Misconfiguration: §4 self-heal ライフサイクル＝攻撃面縮小・fail-closed（**該当・PASS**）。
- Broken Authentication: 認証フロー変更なし（**非該当**）。
- Vulnerable Dependencies: 新規依存ゼロ（**非該当**。既存 deps🟡 は iter61/62 からの pre-existing ack）。

## 残余リスク受容判断

- fp 移行の一過性 unverified（既存 record が初回 unverified）: 受容。fail-closed（silent-green にならない）・該当タスクのテスト再実行で解消。ship note で周知（severity: Info・設計明記）。
- 新規 deploy blocker: **なし**（M＝deploy skip）。

## claims

```claims
verdict: approve
second_opinion:
  verdict: approve
  divergence_points:
    - "committed tree-hash 成分に oversize 上限なし（working 成分は MAX_FILES/BYTES ガード）＝メタデータのみ・+25ms・brick リスクなし・residual 受容（🟢）。1次 §1 の性能考慮と収束。"
    - "deps 監査は requirements.txt 無しで unverified advisory＝契約どおり・🔴 でない（🟢）。"
  findings: "HIGH/MEDIUM/LOW 0。盲検2次は Plan Mode 下でも Bash 動的実証（injection 6種・clean→clean pin・移行 fail-closed・OR marker 発火面縮小・date-ordering git log 裏取り）で 1次と完全収束。"
  evidence_ref: docs/qa-reports/iter64-security-2nd.md
```
