# iter73 Review Report — locale/byte 掃討（deny 側フック byte-wise 決定化）

- **日付**: 2026-07-19
- **対象 diff**: `b0eb8a1..HEAD`（実装 677b71a〜8be219d）
- **設計**: `docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md`
- **計画**: `docs/plans/2026-07-18-iter73-locale-byte-sweep-implementation-plan.md`
- **task_type/size**: framework / M（deploy skip・review+qa+security 必須）
- **レビュー体制**: 1次（reviewer・opus・多角＋security-narrowing）＋specialist（reviewer-testing）＋盲検2次（reviewer・fable・blind）＋親verify（fable・in-session 実測）

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 実装状態 |
|---|------------|------------|---------|
| 1 | RED 回帰 pin（locale/byte） | `tests/test_hook_locale_byte.py`（677b71a・強化 2c5c575/8be219d） | 実装済（10 pass：crash 回帰4＋i18n2＋ASCII2＋受容residual2） |
| 2 | check-destructive.sh に byte-wise locale | `hooks/check-destructive.sh:44`（61b276f→95e08ae 抽出前へ→8be219d コメント訂正） | 実装済 |
| 3 | check-secrets.sh に byte-wise locale | `hooks/check-secrets.sh:55`（7bfb8f7→8be219d） | 実装済 |
| — | 設計/計画の配置修正 doc-sync | e1d1585 | 実装済 |

scope 逸脱なし（2 フック＋テスト＝計画どおり）。判定ロジック無改修（additive）。runtime-state/deploy-gate 非該当は設計に恒久記録。

## Evidence Checklist

- [x] diff を実読（chat summary でなく実ファイル・patterns.sh/secrets-patterns.sh の文字クラスも監査）
- [x] plan/spec の受入条件と突合（配置=抽出前・byte-wise・判定無改修）
- [x] 未カバーエッジケース列挙（Unicode 空白区切り＝SF-016）
- [x] 全 finding に severity＋confidence 付与

## Findings

### 1次（opus・多角）: **approve・findings なし**
- security-narrowing の load-bearing 質問＝「C locale が moat パターンを狭めて miss を作るか」に対し、17 敵対プローブ＋C vs UTF-8 differential で「positive class は ASCII 分離子のみ・negated class は C で widen(safe)・K-4 `.env` 境界は同一」を実証。NBSP `git\xa0add` の非マッチは「bash 単一トークン化＝非コマンド」で非 exploitable と判定。PEP 540 劣化は fail-safe（deny/ask 側）。

### specialist（reviewer-testing）: **Major×1（対処済）**
- **F-T1（Major・conf8・CLOSED-in-review）**: check-destructive の crash 回帰 pin が `decision=="ask"` のみを見るため、`export` を抽出後へ戻す mutation B（抽出ドロップ→fallback も "ask"）を区別できない（secrets 主 pin は deny→ask 格下げで catch＝非対称）。**fix-forward 2c5c575**: `run()` が `permissionDecisionReason` を返すよう拡張し、byte-carrying `rm -rf` が main-path「再帰削除」メッセージを出す（＝byte-wise 抽出成功）ことをアサート。mutation B で fallback「解析に失敗」に落ちて RED になることを親verify 実測＝secrets pin と対称化。

### 盲検2次（fable・blind・1次非開示）: **approve_with_notes・Major×1（対処済）＋Minor×1（対処済）**
- **F-B1（Major・conf9 挙動/conf6 exploitability・→SF-016 として accept）**: C locale が `[[:space:]]`/`\s` を ASCII のみに狭め、Unicode 空白区切り（NBSP/U+3000）が pre-change(UTF-8)=warn/deny → post-change(C)=allow に narrowing。コメントの「ASCII + literal だから byte-wise が正」は事実誤り。**divergence**: 1次は「非 exploitable」で不問、盲検2次は「coverage 縮小＋誤コメント」を Major。**親verify 実測で決着**: narrowing は実在（NBSP/U+3000 は C で non-match）だが、bash は NBSP/U+3000 で word-split せず `rm<NBSP>-rf`/`git<NBSP>add` は単一非存在トークン→`command not found`＝**非 exploitable**（削除/ステージング不成立）。**fix-forward 8be219d**: (a) 両フック誤コメント訂正（runnable は ASCII IFS 区切り必須ゆえ取りこぼさない）(b) 受容 residual を pin（re-widen 時 flip で revisit 強制）(c) SF-016 起票。re-widen は非コマンドへの spurious マッチ＋C-locale 決定性矛盾で不採。
- **F-B2（Minor・conf9・CLOSED-in-review）**: テストが narrowing 方向を pin していない → F-B1(b) の residual pin で解消。
- 他角度（python3 抽出 PEP 540・downstream git/find/tr・negated class・fallback 格下げ）は no-finding。

## 親verify（in-session 実測サマリ）
- byte-wise narrowing 実測: `[[:space:]]` は UTF-8 で NBSP/U+3000 match・C で non-match／ASCII space・TAB は両方 match。
- 非機能性実測: `set -- rm<NBSP>-rf` → argc=1／`type 'rm<NBSP>-rf'` → command not found。
- moat 非退行実測: multibyte 隣接（`rm -rf café`・`DROP TABLE 日本語;`・force-push＋多バイト・`café/.env`）すべて正しく ask/deny。
- mutation 実測: export 削除→両フック RED（crash 検知）／export 抽出後移動→destructive pin（強化後）RED・secrets pin RED。
- full suite: **1302 passed, 2 skipped**・`check_framework_contract.py` PASS。

## Severity 集計
- Critical: 0
- Major: 2（F-T1 テスト強度／F-B1 narrowing）— いずれも **CLOSED-in-review**（F-B1 は非 exploitable と実証し accepted residual=SF-016 として記録）
- Minor: 1（F-B2）— CLOSED-in-review

## 判定: **PASS（approve）**

- 主目的（invalid-byte crash→fail-open の封鎖）を達成し、full suite green・contract PASS。
- 1次/盲検2次の divergence（F-B1）は親verify 実測で「narrowing は実在するが非 exploitable（非コマンド）」と決着し、誤コメント訂正＋residual pin＋SF-016 で対処。
- 位置づけ＝defensive robustness hardening（脅威モデル内到達性ゼロ）は維持。security ゲートで F-B1 の非 exploitability と PEP 540 fail-safe を独立再確認する。

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "F-B1: 1次=NBSP narrowing は非 exploitable で不問／盲検2次=coverage 縮小＋誤コメントで Major。親verify 実測で『narrowing 実在だが bash 非 word-split ゆえ非コマンド＝非 exploitable』と決着 → 誤コメント訂正＋residual pin＋SF-016 で CLOSED-in-review"
```
