# セキュリティレビュー

## 対象

- iter61: iter60 事故クラス（検証サブエージェントの tree 破壊）の機械防御。destructive patterns 拡張＋snapshot 退行ガード。
- 参照: docs/plans/2026-07-07-iter61-incident-class-machine-defense-plan.md（Rev.5）／docs/qa-reports/iter61-review.md

## 確認項目

- 既存 enforcement の後退なし（パターン削除/緩和なし・fail-closed source 経路・byte-identity fallback）
- 追加コードの新規攻撃面（snapshot ガードの入力・sed 埋め込み・ReDoS・CONTEXT 注入）
- バイパス耐性（事故クラスの実用的迂回の残存）
- laundering 経路（復旧アンカー消去）の網羅
- secrets 混入なし・外部依存追加なし（pure bash 維持）

## OWASP Top 10 チェック

- Injection: sed への gate 名埋め込みは `[a-z_]` 検証で封鎖（`.*`/`a/b`/`x&y` は全て continue で除外＝盲検2次実証）。CONTEXT の警告文は固定日本語リテラルで untrusted 補間なし。
- Security Misconfiguration / Broken Access Control: gate 承認・tamper-evidence の enforcement は無改変。snapshot ガードは advisory 層で、既存の deny/block 境界を弱めない。
- その他項目: 本変更はネットワーク・認証・データ永続化に非関与＝非該当。

## STRIDE 脅威評価

- Tampering: 本 iter の主目的＝tamper（親未コミット簿記の revert）への防御強化。復旧アンカー（snapshot）を session 境界での laundering から保護。
- Denial of Service: snapshot ガードの行ごと sed fork による session-start ハング（盲検2次 Major-2）を、gate ブロック1回読み＋case 照合へ変更して解消（119s→1.16s @ 50000行・実測）。destructive パターンは grep -E（ERE・破滅的バックトラックなし）で 200KB コマンド 0.4s。
- 他（Spoofing/Repudiation/Info Disclosure/Elevation）: 非該当または無変更。

## Findings

盲検2次セキュリティレビュー（独立文脈・read-only 委譲）で以下3件を検出、全件 ship 前 fix-forward で解消:

- **Major-1（fix済）**: `git stash 2>/dev/null` 等 fd 前置 redirect が素通り（エージェント最頻出の stash 形＝事故中核）。stash 終端クラスに fd 番号許容を追加。ask テスト+2形、良性ガード（`stash pop/list 2>/dev/null`）+2形。
- **Major-2（fix済）**: 巨大/破損 snapshot で session-start が数分ハング（「brick しない」不変条件違反）。sed の行ごと fork を廃止し gate ブロック単一読み＋case 照合へ。行数上限不要・bash 3.2 互換（連想配列不使用）。回帰テスト（50000行で15秒未満）追加。
- **Minor-3（fix済）**: `git checkout -q -f main` / `--quiet --force main`（フラグ先行 force）が素通り。force エントリに先行フラグ群許容。ask テスト+2形。

fix-forward 後の再検証: 全新形が ask・良性形（`checkout -b`/`--track`/`-q main`/`stash pop`）は allow・B1 drill 9/9 caught・full suite green。

## 残留リスク

- 単一 bare パス checkout（glob/スラッシュ/複数引数/`--`/force なし）はブランチ切替と構文上区別不能＝非対象（iter62 委譲文言層で被覆）。
- mid-session laundering（Bash revert 後に親が update-gate approve）＝session 境界の外（本ガードのスコープ外・plan 明記）。approved→n/a・逆方向 revert も earned→pending のみ検知の設計上スコープ外。
- 変数間接・quote 難読化・`-C` 以外のグローバルフラグ＝SF-004 受容クラス（既存パターン群と同一の限界・ask のみ・accident-prevention スコープ）。
- snapshot ガードが生む新規 laundering 経路は検出されず（盲検2次確認）。

## 総合判定

- 判定: approve（盲検2次: approve_with_notes・指摘3件は全て ship 前 fix-forward 済み・residual なし）
- moat/enforcement の後退ゼロ・secrets 0・依存追加ゼロ。

## Claims（judge が機械読取する）

```claims
verdict: approve
second_opinion:
  verdict: approve_with_notes
  notes: 独立文脈・read-only 拘束委譲での盲検2次。既存 enforcement 弱体化ゼロ（追加のみ・fail-closed source と byte-identity fallback 無傷・REGEX/WARN 24=24 index 整合・sed 注入と phantom-regression 遮断を実証）。Major-1（fd redirect stash）/Major-2（巨大 snapshot で session-start ハング＝brick 不可条件違反・119s実測）/Minor-3（フラグ先行 force checkout）を検出→全件 ship 前 fix-forward 済み・residual なし。secrets 0・外部依存追加なし・pure bash 維持。
```
