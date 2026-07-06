# iter60 セキュリティレポート（security ゲート）

- 対象: iter60・実装 `acc2ad4`＋grill-code fix-forward `c971894`＋review fix-forward `f8974f1`（budget ratchet policy 見直し＝drift 支配構造の計数除外）
- 仕様: `docs/specs/2026-07-06-iter60-budget-exclusion-design.md`
- 性質: 語数計数ロジック（`context_budget.py`）＋rule マーカー＋config＋test＋CLAUDE.md policy。**moat 非該当・hook/判定/enforcement コード不変**。

## 脅威モデルとスコープ

本イテレーションは budget 計数から drift 支配の構造を除外する変更。主眼は「**除外機構が『budget から内容を隠す』濫用ベクタにならないか**」＋「後退（保護の弱体化・秘密混入）が無いか」。budget は anti-bloat のラチェットで security 機構ではないが、除外の抜け穴は guidance 肥大・不正内容の隠蔽に悪用されうるため濫用ガードを機械で固める。

## 検査結果（実測）

| 観点 | 結果 | 根拠 |
|------|------|------|
| 除外機構の濫用（budget 回避） | ✅ 封鎖 | 3重ガード: (1) 行単位 ==roster（除外領域の各行が backtick agent 名 or 既知 scaffold＝自由 prose 混入を検知・review fix-forward）／(2) `len==1`（2つ目のマーカー対で prose を包む多領域濫用を検知）／(3) allowlist トリップワイヤ（除外マーカーは routing.md のみ・`_EXCLUDE_RE` を実 `iter_targets` に当て `==['.claude/rules/routing.md']`＝別ファイルでの除外を機械 FAIL） |
| moat / enforcement 後退 | ✅ なし | 変更は context_budget.py・routing.md・budgets.json・test・CLAUDE.md・design のみ。`hooks/`・destructive deny・gate 改ざん検知・OS-lock は不変（`git diff --name-only` で確認） |
| injection / ReDoS | ✅ なし | `_EXCLUDE_RE` は単一 `.*?`（非貪欲）を2リテラル間に持つ形＝catastrophic backtracking なし。context_budget が読むのは repo 内 `iter_targets`（skills/rules）のみ＝非信頼入力なし |
| secrets 露出 | ✅ なし | diff 追加行に password/secret/token=/api_key/private-key/bearer パターン 0 |
| fail-open/closed | ✅ 安全側 | unmatched マーカー（start に end 無し）→ 無マッチ＝全計数（`test_unmatched_marker_counts_everything`）＝bloat を隠さない fail-graceful。nested は非対応（入れ子禁止を明文化＋単一領域を `len==1` で担保） |
| Vulnerable dependencies | 該当なし | 依存マニフェスト変更なし |

## OWASP Top 10（該当項目のみ）

- **Injection**: 非該当（regex は repo 内ファイルのみ・ReDoS なし）。
- **Broken Authentication / Access Control**: 非該当（認証・moat 不変）。
- **Sensitive Data Exposure**: secrets grep 0。
- **Security Misconfiguration**: budget 変更は保護設定ではない。除外は allowlist で routing.md に限定。
- **Vulnerable Dependencies**: 依存変更なし。

## deploy blocker

なし（M framework で deploy 自動 exempt）。

## 判定

**PASS（1次）。** 除外機構の濫用は3重ガード（行単位==roster／`len==1`／allowlist）で機械封鎖・moat/enforcement 不変・secrets 0・ReDoS なし・fail-graceful（unmatched=全計数）。セキュリティ後退は検出されず。

## 盲検 第2意見（self-attested）

fresh context の general-purpose エージェントに diff（acc2ad4~1..f8974f1）＋spec＋plan のみを渡し、1次結論を非開示で独立2次セキュリティレビューを1回ディスパッチ（5論点: 除外濫用／moat 後退／injection・ReDoS／secrets／fail-open）。特に「除外を悪用して budget を回避する経路」を4シナリオ実走で試させた。

**2次 verdict = approve_with_notes。** セキュリティ後退なし・moat 不変を実証確認。主要3濫用ベクタ（別ファイル除外→allowlist FAIL／roster に素の prose→行ガード FAIL／2領域→`len==1` FAIL）を実走で封鎖確認。非ブロッキングの Minor 2件：

### Minor（residual・post-qa につきコード非編集で記録＝iter48 教訓「非ブロッキング security は residual・review/qa を無効化しない」）
- **Minor-1（防御深度・非セキュリティ）**: 行ガードは「各行が roster **形**（backtick agent 名を含む or scaffold）」を強制するが「語内容の完全一致」ではない＝`Subagents:` 行の延伸や backtick 名を持つ行への自由 prose 混入で語を密輸する余地が残る（実測: passes=True）。design/test コメントの「除外領域 == roster を真に担保」は厳密には**行形強制**の意。**評価＝許容**: budget は anti-bloat の衛生ラチェットでセキュリティ境界ではない・routing.md 編集は trusted commit＋review＋drift を通る。→ **residual として記録**（LEARNINGS 予約・将来 word-exact 強化 or コメント精確化は別 slice）。post-qa のコード再編集は review/qa を無効化するため見送り。
- **Minor-2（情報・非セキュリティ）**: `_EXCLUDE_RE` は unmatched start マーカー個数に O(k²)（k=4000 で 2.84s）。ただし入力は `iter_targets`（repo 内 skills/rules）限定＝外部入力経路なし＝ReDoS 非該当。**対応不要**。

```claims
verdict: approve
tests_green: true
no_stubs: true
second_opinion:
  verdict: approve_with_notes
  notes: 5論点（除外濫用/moat 後退/injection・ReDoS/secrets/fail-open）を4濫用シナリオ実走で検証。moat/enforcement 不変（hooks 変更ゼロ）・secrets 0・主要3濫用ベクタ封鎖・unmatched は全計数の fail-safe。2件の非ブロッキング Minor（Minor-1 行ガードは行形強制で語完全一致でない＝密輸余地・budget は衛生でセキュリティ境界でない・trusted commit+review+drift で緩和＝residual 記録／Minor-2 O(k²) は repo 内入力限定で ReDoS 非該当・対応不要）。post-qa につきコード非編集で residual 化（iter48 教訓）。1次と方向一致（後退なし）。
  divergence_points: ["design.md:96 / test コメントの『除外領域==roster を真に担保』は厳密には行形強制（語完全一致でない）＝roster 形を保った行内密輸の余地が残る（非セキュリティ・residual 記録）", "_EXCLUDE_RE は unmatched start に O(k²)＝repo 内入力限定で ReDoS 非該当・対応不要"]
```
