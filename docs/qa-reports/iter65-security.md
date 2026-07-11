# iter65 security レポート — S サイズ修復（R2🔴）

- 対象: `git diff 26de7f6..HEAD`（gate 強制ロジック＝control-plane 変更）
- 脅威モデル正本: `docs/security-followups.md` §脅威モデル（LLM 自己バイパス）
- 手法: 1次＝親 in-session（review でのゲート迂回深掘りを踏まえ moat posture を確定）／盲検2次＝fable フレッシュ委譲（下記 claims）。
- 環境: 依存ファイル変更なし＝dependency audit N/A。UI/network/DB/認証フローの変更なし。

## OWASP 該当チェック（非該当は理由付きスキップ）

- **Injection**: ✅ 確認。check-gate の新規 `$()` は `read_frontmatter`/`gate_value`（ファイル内容の grep/sed）で、untrusted 入力の eval/command 実行なし。`printf '...%s...' "$GATE"` は値を**引数**として渡す（format 文字列ではない）＝review F1 で `%s%d%n` 逐語出力・`%n` 非発火を実証。埋め込む値は gate 値（approved/pending 等）で、`"`/`\` は emit.sh の JSON エスケープ済。task_size 値は reason に埋め込まれず等価比較のみ。→ **findings なし**。
- **Broken Authentication（＝gate 認可機構・本 diff の本丸）**: gate 判定を size-aware 化。**SF-010** の migration-grace 経路を除き、moat 保証（brainstorm ハードゲート・pure-bash fail-closed）は保存（下記「moat posture」）。
- **Sensitive Data Exposure**: ✅ 確認。diff に secrets/credentials パターン 0（grep 実行）。ログ/レスポンスへの機密露出なし（gate ロジックのみ）。
- **Security Misconfiguration**: ✅ 確認。size-aware gate は fail-closed（未設定/不正 task_size→plan gate＝保守側・gate を緩めない）。キー欠落/空値も deny。
- **Vulnerable Dependencies**: N/A（依存変更なし）。

## moat posture（gate 迂回・自己バイパス）

review 1次（gate 迂回 finder）で検出した gate-bypass の security 確定:

| 経路 | 状態 | severity | 判断 |
|------|------|----------|------|
| (a) 本文 spoof（`frontmatter_value` whole-file grep が本文 `task_size: S` を拾う） | **封鎖済み**（b9c95f7・frontmatter スコープ読み） | Major→解消 | qa 一次変異 M2 で歯を確認・test_i でピン |
| (b) frontmatter 直接 raw-Edit × `post-status-audit:210` migration-grace（empty-baseline で tamper skip）＝**SF-010** | **OPEN（accepted residual）** | **Medium**（盲検2次較正） | 下記 ack |
| F-1 `extract_scalar_value` 引用形優先の python/bash 割れ（audit-evading） | OPEN（SF-010 同梱） | Minor | 次反復 |
| F-2 `gate_value` 本文フォールバック（gate_approvals 節欠落時） | OPEN（SF-010 同梱） | Minor | 次反復 |

### SF-010 の residual ack（security 判断）

- **性質**: 文書化済み tamper-evidence 保証（脅威モデル §「task_size も .gate-snapshot 比較で検知・block」）への **empty-baseline 例外**。この diff が task_size を gate 判定に昇格させたことで、既存の migration-grace 穴（iter43 由来）が初めて gate-skip に転化。
- **発火前提**: task_size 未設定の empty-baseline 窓（fresh scaffold / rollover 直後〜Step D 前）＋意図的 frontmatter raw-Edit。task_size 設定済みなら `[ -n "$OLD_TF" ]` 非空で block＝到達不能。
- **脅威モデル内の位置**: 単一ユーザ dogfood の**自傷経路**（外部攻撃者面ではない）。bypass 後も brainstorm はユーザー承認必須ハードゲートで、飛ぶのは plan 儀式のみ（無承認コーディングは依然不能）。低頻度・高意図性。
- **判断**: **accepted residual（ack）**。ユーザー承認のもと次反復（iter66）で専用 brainstorm/plan を通して migration-grace を「真の旧フォーマット snapshot 限定」に絞る＋F-1/F-2 パーサ drift 統一で対応。SF-010 に OPEN 記録済み。accessible surface（経路 a）は本 iter で封鎖済み＝ship 可。

## Evidence Checklist

- [x] Grep で secrets/credentials 検索（diff・該当 0）
- [x] 外部入力サニタイゼーション確認（task_size は equality 比較のみ・gate 値は literal 比較・emit.sh JSON エスケープ）
- [x] dependency audit（N/A＝依存変更なし・明記）
- [x] 全 finding に severity・remediation 付与（SF-010/F-1/F-2＝次反復 remediation 明記）

## deploy blocker

- なし（M＝deploy skip・そもそもデプロイ物なし）。SF-010 は ship blocker ではない（accessible surface 封鎖済み・accepted residual）。

## 判定

**approve_with_notes**。diff 起因の新規 injection/secrets/data-exposure なし。moat posture: 経路(a) 封鎖済み、SF-010（経路 b）は accepted residual として ack（ユーザー承認・次反復分離）。fail-closed 保存。

```claims
scan_done: true
secrets_found: false
dep_audit: "N/A (no dependency changes)"
verdict: approve_with_notes
residual_ack: "SF-010 (task_size empty-baseline raw-Edit × migration-grace・Medium)・F-1/F-2 parser drift — 次反復 iter66 分離・ユーザー承認済み"
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "結論収束（両者 approve_with_notes・defer+ack 必須で一致）"
    - "SF-010 severity のみ割れ: 2次=Medium / 1次=Major。2次論拠=end-state は authorized RISK-3(update-task.sh --size S) で既到達・受容済みで capability 増分は監査ログ行の有無のみ＝新 capability 非解錠。→ Medium を採用"
    - "2次が SF-010・RISK-3・body-spoof・F-1/F-2 を独立実測し、未起票の新規 bypass ゼロを確認"
```

## 盲検2次（self-attested）

- **ディスパッチ**: security（model=fable）・1次 verdict 非開示（fresh context）・diff/spec/脅威モデル/SF-010 起票文のみ・6拘束（read-only・fixture は mktemp）。
- **結果**: **approve_with_notes（収束）**。5観点すべて実フック起動で実測 PASS。injection/format-string/JSON 破壊なし（敵対的 task_size/gate 値で cmdsub 非発火・JSON parse OK）・secrets 0・fail-closed 6ケース全 deny・本文 spoof 封鎖確認。
- **独立再現**: SF-010 を CONFIRMED（empty-baseline が唯一の発火条件＝M baseline では audit が `[task-tamper] task_size changed M→S` を BLOCK と対照実測）。RISK-3 の authorized 経路も実測（同 end-state 到達・受容済み）。未起票の新規 bypass **ゼロ**。
- **severity 較正**: SF-010 を **Medium**（1次 Major から下方修正）。論拠採用済み（SF-010・security レポート反映）。
- **residual ack**: 2次が security-gate residual ack を明示付与・defer に concur。deploy security blocker なし。
