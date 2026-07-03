# iteration 55 — Deploy Report（ドッグフード一周目フィードバック反映）

- date: 2026-07-03
- task: framework / L / v1.16.0

## Deploy Target

- Hosting / Database / CI/CD: n/a（フレームワーク内部変更。デプロイ実体＝main への commit/push）
- 配布経路: `bin/setup.sh` の `copy_hooks`。本イテレーションで **`hooks/lib/*.tsv` を glob に追加**し
  新規 `hooks/lib/scripts-manifest.tsv` を全 profile に force-copy（F6 級 install 死角の封鎖）。
  変更した判定ロジック（is_allowlisted の manifest 化・stderr 正規化・is_root_prose_md の symlink 除外）は
  既存 REQUIRED hook（check-control-plane.sh・check-gate.sh）内＝新規 contract 登録は manifest のみ。

## デプロイ前ゲート確認

- [x] review approved（docs/qa-reports/iter55-review.md・盲検2次2体 approve_with_notes・全 notes 解消）
- [x] qa approved（docs/qa-reports/iter55-qa.md・B1 SKIP＋手動 mutation 相当5点実証）
- [x] security approved（docs/qa-reports/iter55-security.md・盲検2次26経路 approve_with_notes・symlink 後退修正済）
- [x] 環境変数: n/a（フレームワーク）
- [x] install 契約: test_install_ships_scripts_manifest＋test_installed_hook_allows_manifest_script で
      installed tree に manifest 実在＋installed hook 実発火 ALLOW を検証（F6 教訓の契約化）
- [x] git: push は `gh auth switch --user yuuya-miyagaki` 後に手動実行（**本イテレーションはユーザー確認のため push 手前で停止**）

## Mandatory Security Blockers

該当なし。moat 判定変更は全て fail-closed 維持・allow を狭める方向（実行形プレフィックス化は pre-existing
vuln を CLOSE）・stderr 正規化は生 $CMD 検出後の allow 側限定・permissions に状態変異スクリプト非混入。
盲検2次セキュリティ agent が 26 経路実発火で smuggle 全 DENY を実測。secrets ハードコードは iter55 変更行に不在。

## 検証

- full suite **1285 passed / 3 skipped**（record green・manual newest）
- contract full PASS（FRAMEWORK_VERSION 1.16.0 同期・scripts-manifest 3方向 drift 検査 green）/
  check_status PASS / check_reference_drift PASS / bash -n 全変更 hook・bin/setup.sh PASS
- git mode-flip なし（tracked ファイルの exec-bit 変更なし）

## 残留リスク（受容・別テーマ）

- 非ASCII homoglyph・symlink 一般解決・exec ガジェット2本の ask backstop＝いずれも iter54 以前から不変で
  今回悪化なし。FS 実解決（realpath+inode）リアーキ＝次テーマ（OS-lock 昇格）で解消。layer-2 cp-lock が backstop。

## 判定

**PASS。** 全 prior gate approved・blocker なし・退行なし。デプロイ＝main commit
（push は手動 gh switch 後・**本イテレーションは push 手前でユーザー確認待ち**）。

```claims
verdict: approve
```
