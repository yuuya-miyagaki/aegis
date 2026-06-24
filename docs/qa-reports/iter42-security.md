# iteration 42 G1-G3 — Security Review

- date: 2026-06-24
- task: framework / L / guard 網羅
- 脅威モデル: docs/security-followups.md（guard=事故防止／敵対的 interpreter・var 間接は SF-004 受容）に照らす。

## 監査サーフェス

- 変更: hooks/lib/patterns.sh（破壊+deploy パターン）、check-deploy-gate.sh / check-cron-gate.sh（single-source）、check-secrets.sh（git -C 抽出＝secret-staging deny 経路）。
- 観点: G2 が新たな bypass/regression を生まないか、G1/G3 が既存 deny を弱めないか、injection・fail-open。

## findings

| # | 項目 | 判定 | 根拠 |
|---|------|------|------|
| F1 | G2 quoted-path-with-space の miss | Low（修正で縮小・非 fresh hole） | `extract_command` は引用符保持＝`-C "/p with space"` で `"/p` 抽出→対象 repo 誤り→staged .env 見逃し。**較正**: 素の `git -C repo commit` は本変更で fail-open→deny に改善（純増）。space 付き quoted のみ残存＝pre-G2 baseline（CWD scan）も同様に見逃し＝HEAD 比で新規穴ではない。**対処**: 囲み引用符 strip を追加（quoted-no-space 回復）。space 含む quoted は既知限界として記録。 |
| Q2 | injection | PASS | 抽出 path は bash 配列 `GIT_DIR_ARGS+=("$_a")`→`git "${GIT_DIR_ARGS[@]}" diff` の引数（eval/word-split なし）。注入なし。 |
| Q3 | 既存 deny の弱体化 | PASS | AEGIS_DEPLOY_REGEX は旧 inline DEPLOY_RE と byte 同一（逐語移設）。cron single-source は旧 DANGER_RE の strict superset（rm -rf/drop/force-push/rimraf/find -delete を全保持＋dd/chmod -R 追加）。脱落パターンなし。 |
| Q4 | `/dev` truncate 除外 | 許容 | `> /dev/sda` は ask しないが `dd of=/dev/sda`（if= 有無とも）が ask＝主要経路被覆。`> /dev/null` を benign に保つトレードオフ。事故防止スコープ＋脅威モデル上許容。 |
| Q5 | secret 露出 / fail-open | PASS（純増） | G2 は secret-staging deny 経路の fail-open（git -C で CWD scan＝空振り）を塞ぐ修正。新規 fail-open は F1 圏のみ（baseline 同等）。 |

## 盲検 第2意見（self-attested）

独立 security エージェント（1次非共有・diff＋脅威モデルのみ）実走。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["F1 quoted-path-with-space miss（Low・非 fresh hole）→ quote strip で縮小"]
```

## 判定

**PASS（approve_with_notes）。** G2 は fail-open を塞ぐ純増の修正。G1/G3 は既存 deny を弱めず（deploy regex 逐語・cron は superset）。新規脆弱性なし。F1 は Low で baseline 同等＝quote strip で realistic ケースを回復、space 付き quoted は既知限界として記録。deps 変更なし（bash + grep）。
