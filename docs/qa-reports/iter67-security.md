# iter67 security レポート — judge test-fact 判定堅牢化（trust-scan）

- **対象**: `d2c4dd6..HEAD`（scripts/build-judge-card.py::read_test_result trust-scan 化＋系列テスト＋docs 同期）
- **task_type/size**: framework / M（control-plane＝gate 判定ロジック接触につき security 必須）
- **設計正本**: docs/specs/2026-07-12-iter67-judge-test-fact-robustness-design.md
- **脅威モデル正典**: docs/security-followups.md 冒頭 canonical 節（self-bypass・silent-green 禁止）
- **判定**: **PASS**（1次 opus approve＋盲検2次 fable approve_with_notes・新規脆弱性0・findings 2件はいずれも differential 実走で pre-existing 確定＝SF-012 起票済み）

## OWASP 簡略チェックリスト（該当判定）

| 項目 | 該当 | 結果 |
|------|------|------|
| Injection | 該当 | PASS（shell メタ7種で sentinel 非生成・regex-DoS 9種 195-275ms 線形・cmd は string 処理のみ） |
| Sensitive Data Exposure | 該当 | PASS（追加276行 secrets 0 hit・合成 hex 値は SECRET_PATTERN 非該当） |
| Vulnerable Dependencies | 該当 | PASS（新規 import は stdlib `importlib.util` 1件・manifest 不変更） |
| Broken Authentication | 非該当 | diff は auth/session/login/token に不接触（承認は update-gate.sh＋snapshot の別機構） |
| Security Misconfiguration | 非該当 | config/CORS/header/chmod/権限に不接触（変更は read_test_result 内1分岐のみ） |

## 1次レビュー（security agent=opus max・differential harness）

baseline(d2c4dd6) と HEAD の read_test_result を両ロードする differential harness（リポジトリ外 scratch・実 patterns.sh/fingerprint.sh を read-only symlink）で全項目を実走。

### gate-bypass 4攻撃面（本丸・全実走）
- **(a) rotation × 透明化**: 4系列（同一ログ/.1 跨ぎ/50件埋没/green←red←noise）全て **BASE=unverified／HEAD=red**＝decidable red が noise で 🟡 洗浄されなくなった＝**red 可視性の厳格化**（後退なし）。
- **(b) クォート span マスク非対称**: quoted-runner 名の red は BASE=HEAD 同一（マスクは trust-scan 分岐の手前で発火＝diff 影響外・pre-existing）。悪用拡大なし。
- **(c) marker_verified 型混乱**: `"true"`/`1`/`1.0`/`[]`/`None` 等 8種の lone observed-ok は全て **unverified**（`is not True` identity 比較が堅牢）。系列では red 保持。green 捏造・red 抑圧いずれも不可。
- **(d) fp 細工**: 空/非hex/foreign(`A`×64)/stale-green←fresh-noise は全て unverified＝**fp backstop 無緩和**。fresh-green←stale-noise のみ green（設計どおり・fresh green は正当）。

### findings（1次）
- **F-1（Low・pre-existing）**: unknown/missing src → decidable-by-default。差分実測 BASE=HEAD=green＝回帰でない。実 writer は observed/manual のみ発行・任意 log 書込みは脅威モデル外。→ SF-012(b)。
- **F-2（Info・pre-existing・fail-closed）**: 非 string cmd で AttributeError → build() が rc=2（🟡）で捕捉。該当行 blame=5a8184f0（diff 前）。

1次 verdict: **approve**（検出2件は差分実測で pre-existing 確定・SF-012/既知として可視化済み・本 diff の新規リスクなし）。

## 盲検 第2意見（self-attested・fable・fresh context・1次結論非開示）

独立に14検査を消化（攻撃面を自力選定）。コア安全不変条件を確認: 透明 skip は `observed かつ marker_verified≠true かつ status=ok` に厳密限定＝**decidable（manual/marker=true）も fail-status も決して skip されない**＝green は必ず fp 一致 decidable green の実在に裏打ち。red 洗浄経路の閉鎖（強化）も独立確認。
- **F1（Low・pre-existing・High conf）**: washed-green（`pytest; true` の exit 洗浄＋pass-marker が `1 failed, 2 passed` にマッチ→marker_verified=true→decidable green）。writer probe で marker_verified=true を実測・reader で BASE=HEAD=green。iter67 は stacking で表面化するのみ＝**green 新規製造なし**・発火に明示的 exit 洗浄（自己欺瞞）必要。→ SF-012(a)。
- **F2（Info・pre-existing）**: unknown-src decidable（1次 F-1 と独立収束）。→ SF-012(b)。
- **F3（Info・設計既知境界）**: 非決定/環境依存テストの残余は fingerprint が捕捉しない既存盲点＝新クラスの脆弱性でない。

盲検 verdict: **approve_with_notes**（新規脆弱性なし・F1/F2 は differential で pre-existing 実証・iter68 hardening 候補）。

## divergence 論点と裁定
「washed-green の到達性拡大（W2: washed-green 上の noise が旧 🟡→新 green で表面化）を reject 理由にするか」— 1次/2次とも **green の新規製造はない**（透明化は decidable green の実在が前提・fp backstop 健在）＋**発火に明示的 exit 洗浄が必要**（通常失敗は exit≠0→status=fail→red/🟡）で許容判断に収束。結論レベルの割れなし。根因は writer 側 marker/status 整合欠如で SF-012(a) に分離。

## 起票（SF-012・OPEN・Low）
docs/security-followups.md に SF-012 起票済み: (a) washed-green（marker/status 整合 hardening・writer 側 zero-run gate 同型軸 or reader 側矛盾検出）＋(b) unknown-src allowlist（reader 側 `src in {"manual","observed"}` 以外を undecidable-fail 化）。両件 pre-existing・contained・iter68 hardening 候補。

## Evidence Checklist
- [x] Grep で secrets/credentials パターン検索（追加276行・0 hit）
- [x] 外部入力（evidence-log フィールド）のサニタイゼーション確認（string 処理・dict 比較のみ・shell/eval 非到達）
- [x] dependency audit（新規依存ゼロ・manifest 不変更）
- [x] 全 finding に severity と remediation 付与
- [x] gate-bypass 4攻撃面を differential 実走・pre-existing は baseline 差分で確定

## テスト実測
- 1次: judge/evidence/patterns スイート 132 passed・contract PASS
- 2次: 同 132 passed・contract PASS（独立実行）
- full suite: record-test-result（trusted runner）で green 記録＝承認直前の最新 decidable

## deploy blocker
なし（M サイズにつき deploy 自体 skip）。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: []
  evidence: "盲検14検査・differential harness（BASE d2c4dd6 vs HEAD）実走。透明skipは observed/marker≠true/ok に厳密限定＝decidable と fail は skip されず silent-green 不変条件保持・red 洗浄経路は閉鎖（強化）。新規脆弱性0。F1 washed-green/F2 unknown-src は差分実走で pre-existing 実証（BASE=HEAD）＝iter67 回帰でない・SF-012 起票済み Low hardening。132 passed・contract PASS・scratch は repo 外・repo 無変更。"
```

## 結論
**security PASS**。trust-scan は silent-green 禁止を保持し red 側を厳格化。gate-bypass 4攻撃面で新規経路ゼロ（differential 実走）。検出2件（washed-green・unknown-src）は 1次/2次が独立に differential で pre-existing 確定し SF-012（Low・iter68 hardening）へ分離。ship フェーズへ。
