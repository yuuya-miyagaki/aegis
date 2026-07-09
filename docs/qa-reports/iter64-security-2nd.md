# iter64 セキュリティ 盲検第2レビュー（self-attested・独立）

- 日付: 2026-07-09
- レビュア: `security` エージェント（フレッシュ context・1次 verdict 非共有＝盲検）
- 手法: 隔離 scratchpad git repo で敵対再現し**動的実証**（Plan Mode 下でも Bash 使用可）
- 対象: コミット 992ff4f

## 観点別 verdict（全て動的 evidence つき・PASS）

1. **silent-green 非復活**: clean→clean の2連続 code commit で fp 分離（P1≠P2・committed tree-hash 単独担保）／docs-only・.claude-only で不変／`aclaude/code.py` 変更で fp 変化（char-class 保持）／committed=""（全docs）は has-code fp と非 alias／除外除去 mutant で docs-only 不感が破れる＝テスト検出。
2. **注入**: `$(touch PWN)`／バッククォート／`;touch;`／`$IFS`／glob／`--opt` のファイル名をコミット→fp は clean 64-hex・全 PWN マーカー非生成＝非実行。committed 部は内容 cat なし・`printf '%s'` 固定フォーマット。
3. **移行 fail-closed**: 旧 head:sha fp ≠ 新 tree: fp→`read_test_result` が unverified。3書き手（evidence.sh/record-test-result.py）＋1読み手すべてで `head:`/`tree:` 非依存を確認（内部表現は fingerprint.sh:109 のみ）。
4. **OR marker**: `A OR B`→`A` 単独＝発火面を厳密縮小・bypass lever なし。unlock 実行体/第2防御/対象集合は無改変。off は関数先頭 return で fail-closed。date-ordering を git log で裏取り（stamp 66e59e8 2026-06-13 ＜ cp-lock 1e46e4d 2026-06-21・8日先行）。
5. **secrets/deps**: 追加行の secret 走査 0・新規 import/外部バイナリなし。

## STRIDE

- Spoofing: self-heal は stamp AND 実 lock の連言＝planted stamp のみでは不発。本変更は spoofing 面を縮小。脅威モデルは良性（起動ユーザ権限・驚き回避目的）。
- Tampering/Repudiation/EoP: 敵対コミット名は非実行データ・unlock 既存経路・昇格なし。
- Information Disclosure: fp は sha256 トークンのみ。
- DoS: committed 成分は ls-tree メタデータ1回＋grep＋sha256（+25ms・hot-path 外）。working 成分の oversize ガード不変＝brick 不変条件保全。

## Findings

なし（HIGH/MEDIUM/LOW 0）。

## divergence_points（🟢 非ブロッキング）

1. committed 成分に oversize 上限がない（working 成分は MAX_FILES/BYTES でガード）。ただし内容 cat なし・行あたり定数長メタデータのみ・459 files +25ms・brick リスクなし＝residual 受容。
2. deps 監査: requirements.txt 無しで `audit_deps` は unverified（🟡 advisory）＝契約どおり・🔴 でない。

## 総合 verdict: approve

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve
```
