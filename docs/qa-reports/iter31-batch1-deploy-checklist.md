# Deploy チェックリスト — iteration 31 / Batch1（2026-06-18）

> Aegis は server アプリでなくフレームワーク＝deploy は**リリース準備**（staging/uat/production は N/A）。

## ゲート前提（全 approved）

- [x] review approved（`docs/qa-reports/iter31-batch1-review.md`）
- [x] qa approved（`docs/qa-reports/iter31-batch1-qa.md`）
- [x] security approved（`docs/qa-reports/iter31-batch1-security.md`・approve_with_notes）
- [x] git config user.email 確認済（既存リポ・変更なし）

## 配布影響（install 経路に影響あり）

Batch1 は**配布物**を変更（install へ配られる）:

- `hooks/check-control-plane.sh`（moat 精度向上）＝installed hook が改善版に。`bin/setup.sh`（**新規 baseline commit 挙動**：fresh install で 0-commit なら scoped add＋commit、既存リポは no-op）。`scripts/build-judge-card.py`（stub 走査の CP 除外・secret 走査は不変）。
- mirror（`examples/minimal-project/`）同期済＝`test_mirror_identity` 緑。
- **配布整合**: `tests/test_setup_distribution.py`(11) 緑＝install が参照する scripts が配布集合に含まれる。
- net 効果: install の moat が厳密化＋新規 install に baseline commit。新規 install の初回 review ゲートが framework 由来 stub 🔴 を出さない（OBS-017 の主目的）。

## 後方互換・ロールバック

- hook 変更は**厳密化＋精度向上**方向。意図的緩和は write-safe な OBS-003（read-only パイプ）/OBS-006（commit メッセージ内 CP 言及）/OBS-017（git add staging→ask）のみ＝既存の安全な操作の摩擦低減。control-plane への内容書込みは従来どおり deny（新規 WRITE バイパス ゼロ・security ゲート実証）。
- setup baseline commit は**加算的**（0-commit fresh install のみ・既存リポ no-op・best-effort で git 失敗は skip）。
- ロールバック容易: Batch1 コミット（52dff43〜6d1b938＋76112bc/8f85a5b）の revert で完全復元。状態移行・データ変更なし。

## Mandatory Security Blockers

- [ ] 認証無効 / [ ] デフォルト管理者PW / [ ] HTTPS 未設定 / [ ] secret ハードコード — **全て非該当**（フレームワーク・server/auth/secret なし）。
- **残存リスク（deploy blocker 非該当）**: SF-001（control-plane の literal `hooks/` 一致回避＝quote分割/backslash/bare-dir。pre-existing・Critical）。security skill の blocker 列挙に非該当のため deploy をブロックしない。`docs/security-followups.md` SF-001 に durable 記録・最優先 follow-up（繰延合意）。

## 版（ship で適用予定）

1.10.0 → **1.11.0**（feature・MINOR：control-plane 精度＋setup baseline）。contract 定数・template/example/live STATUS を ship で統一。

## 機械検査（現 HEAD）

full suite **830 passed/1 skip** ・ REDTEAM PoC **18/18＋5/5** ・ contract 全 profile（minimal/standard/full）・ drift ・ mirror identity(7) ・ scaffold smoke(3 profile) ・ distribution(11) ＝**全 PASS**。

## 判定

**PASS** — 配布整合・後方互換確認、新規 WRITE バイパス ゼロ、deploy blocker なし、ロールバック容易。残存リスク SF-001 は繰延合意済。push は明示承認まで保留。

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve
  divergence_points: ["security ゲートの approve_with_notes を継承（SF-001 残存・OBS-003/006/017 の意図的緩和）。deploy 固有の新規所見なし"]
```
