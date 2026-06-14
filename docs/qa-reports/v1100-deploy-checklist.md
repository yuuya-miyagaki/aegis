# v1.10.0 deploy チェックリスト（2026-06-14）

## 配布影響

- 層1（core）: `scripts/skill_behavior_manifest.py`（root 専用・非ミラー・setup profile 非配布＝framework-dev のみ）＋`check_reference_drift.py` への追加。installed project には drift も manifest も配布されない（profile は `check_status.py` のみ）＝**install 経路への影響ゼロ**。
- 層2（extension）: `extensions/skill-pressure-drill/`＝CONVENTIONS 準拠の手動 opt-in addon。`setup.sh --profile` 非搭載・contract 非登録＝コア契約面 churn ゼロ。
- mirror: 変更はすべて非ミラー面（scripts/・extensions/・tests/・docs/）。`.claude/skills` 等のミラー対象は不変＝`make example` 差分ゼロ。

## 後方互換・ロールバック

- 既存挙動の変更なし（純追加）。drift に check が 1 つ増えるのみ（既存 skill は全トークン保持＝即 GREEN）。
- ロールバック容易: 関連コミット（`6575d75`/`caf4e0e`/`848ae55`/`bb40ed2` ＋本 close-out）の revert で完全復元。データ移行・状態変更なし。

## 版

1.9.0 → 1.10.0（feature・MINOR）。contract 定数・template STATUS・example STATUS・live STATUS を 1.10.0 に統一。

## 機械検査

contract 全 profile / drift（15 チェック）/ Tier0 779pass・1skip / Tier2 smoke / Tier3 scenario / make example 差分ゼロ＝全 PASS。

## 判定

PASS（配布リスク低・ロールバック容易）。
