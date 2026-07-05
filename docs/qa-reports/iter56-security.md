# セキュリティレビュー（iter56）

- 対象: origin/main..HEAD（iter56・9コミット）
- 中心的関心: **moat 変更**＝check-secrets broad-staging の deny 緩和（先頭ドット
  ファイル名の個別 add 解放）と、full プロファイル配布物の増加

## OWASP チェックリスト（該当項目のみ）

- [x] **Injection**: 新規 bash 正規表現は固定パターン（変数展開は既存 GIT_PRE_OPTS のみ）。
  claims パーサは narrow YAML subset・eval なし。テンプレプレースホルダは文字列として
  のみ扱われ、KNOWN_VERDICTS 外は 🟡 可視化。→ 問題なし
- [x] **Sensitive Data Exposure**: diff 全体を credential パターンで grep → 混入なし。
  judge の scan_secrets も承認時に実走（tier-1）。→ 問題なし
- [x] **Security Misconfiguration（moat 緩和の攻撃面）**: バイパス経路を hook への
  実入力で実測（下記）。→ deny 維持を確認
- [x] **Vulnerable Dependencies**: 依存追加ゼロ（stdlib / pure-bash のみ）。→ 該当なし
- 非該当: Broken Authentication（認証フロー変更なし）

## moat 緩和のバイパス実測（1次・実 .env を置いた tmp repo で hook へ JSON 実入力）

| コマンド | 期待 | 実測 |
|---------|------|------|
| `git add .env` / `git add ".env"` / `git add ./.env` | deny | deny ✅ |
| `git add .env.example .env`（safe variant 偽装複合） | deny | deny ✅ |
| `git ADD .ENV`（大文字 fold） / `git -C . add .env` | deny | deny ✅ |
| `git add .` / `git add -A` / `git add ./` | deny | deny ✅ |
| `(cd sub && git add .)` / `git add .>out`（grill-code 由来） | deny | deny ✅ |
| `git add .env.example` / `git add .gitignore`（解放対象） | allow | allow ✅ |

緩和は「先頭ドットの個別ファイル名」のみ・実 .env は直接検査（:140）が独立に deny。
境界は否定クラス（非パス文字すべて）＝デリミタ列挙より広く安全側。

## 配布物増加の攻撃面（⑥）

full へ追加の5本（retro_report / check_reference_drift / learnings_search /
lint_names / platform_manifest）はいずれも iter55 で allow クラスとして審査済みの
読取検査系（platform_manifest は import-only）。permissions 整合は contract 方向2で
機械強制。install 実在検証テストは setup.sh を tmp に実走＝ホスト状態を変更しない。

## judge 判定変更の承認バイパス検査（③）

- 🟡 抑止は {approve, approve_with_notes} 同士の名目差**のみ**。reject/blocked/未知値
  が絡む相違は従来どおり 🟡。
- 値不正検査は盲検2次 Major 反映で**強化**（claims 存在時に全ゲート常時）＝
  未記入テンプレの沈黙通過を封鎖。tier-1（tests/stubs/secrets/deps）は不変。

## Findings

- Critical: なし
- **Major（盲検2次が実測検出→修正済み）**: `hooks/check-secrets.sh` の broad-dot 否定
  クラス化が緩和し過ぎ、**先頭ドットのグロブ**（`.en*`・`.e?v`・`.*`・`.env.*`）が
  broad 判定も直接 .env 判定もすり抜けて実 .env を silently allow していた（iter56 前は
  deny＝純回帰。commit 時の staged-diff 走査は依然 deny のため実コミット漏洩は最終ゲートで
  阻止）。→ **グロブ節 `\.[^space]*[*?[]` を broad 分岐に追加**（先頭ドット＋グロブ
  メタ文字を deny・非先頭ドットの `foo.txt*` は許容）＋回帰テスト2本
  （test_add_leading_dot_glob_still_broad / test_add_non_leading_dot_glob_is_not_broad）。
  実測: 修正後 `.en*`/`.e?v`/`.*` は deny・`.env.example`/`.gitignore` は allow 維持。
- **Minor（2次 Low・修正済み）**: `build-judge-card.py` で claims に `verdict` キー自体が
  欠落すると値検査を skip して沈黙 → 「claims に verdict キーがありません」🟡 を追加
  （fail-visible）。
- Minor（記録のみ）: 否定クラスの残穴（`.~x` 等2文字目非パス文字の先頭ドットファイルは
  broad 誤検知＝deny 側・安全方向・コメントに Known residual 明記済み）

## Blockers

- なし

## 判定

- 1次: **approve** ／ 2次 approve_with_notes の指摘（Major グロブ回帰・Minor verdict キー
  欠落）は**両方とも push 前に修正済み**（full suite 1322 passed・バイパス実測で deny 回復確認）

## 盲検 第2意見（self-attested）

2次レビュアー（security 役・fresh context・1次結論非開示）が実バイパス試行を含む
独立レビューを実施。verdict= approve_with_notes（Major 1・Low 1）→ **全件修正済み**。

```claims
verdict: approve
second_opinion:
  verdict: approve_with_notes
  notes: Major（先頭ドットグロブ .en* の add-moat 回帰・commit ゲートで漏洩阻止済だが add 側を締め直し）＋Low（verdict キー欠落の沈黙）を push 前に修正・回帰テスト追加・バイパス実測で deny 回復確認
```
