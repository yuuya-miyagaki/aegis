# iteration 46 review — threat-model 境界ドキュメント（C4/G4 クローズ）

- 日付: 2026-06-25
- task_type/size: framework / M（docs-only）
- 対象 diff: `docs/security-followups.md`（canonical 脅威モデル節＋SF-007＋SF-008）、`docs/full-review-2026-06-24-...md`（backlog 行＋C4/G4 finding pointer）、`docs/LEARNINGS.md`（C4 tech 1件）
- 参照: plan=`docs/plans/2026-06-25-iter46-threat-model-boundary-implementation-plan.md` / spec=`docs/specs/2026-06-25-iter46-threat-model-boundary-design.md`

## 対照表（plan タスク → 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | security-followups.md 拡張（canonical 脅威モデル＋SF-007＋SF-008） | `docs/security-followups.md` | 完了 | NOT-A-VULN 節を CLOSED と分離（grill-plan 致命1）。最小再構築キット付き。 |
| 2 | full-review backlog 行の closed 化＋C1 反映 | `docs/full-review-2026-06-24-...md` | 完了 | backlog 行＋C4(:69)/G4(:60) finding に closure pointer。C1=訂正・残留留意点は別系統と明記。 |
| 3 | README posture（条件付き） | — | **skip（正当）** | §95 は secret ゲート非言及かつ既に security-followups.md 参照済＝触らない（YAGNI）。`architecture-overview.md` も脅威モデルの競合記述なし（信頼境界節は agent readOnly の話）＝ポインタ不要。 |

未着手タスクなし。

## findings（severity / confidence）

1 次（self）＋盲検 2 次（`reviewer-maintainability`・fresh context・diff と plan/spec のみ）を統合。

- **Minor / conf 8** — `security-followups.md` SF-007「bash が exact approved を返すのは clean トークンのみ」が enforcement の所在を `gate_value` に誤帰属（実際は consumer の `check-gate.sh:174` exact-match）。→ **反映済み**: 「`gate_value` は値をそのまま返す／拒否は消費側」に書き換え。
- **Minor / conf 7** — SF-008 が「`.gitignore` nudge は未実装」と読め、`check-secrets.sh:241-258`（Check 3＝Bash redirect 経由 .env の advisory）の存在と矛盾しうる。→ **反映済み**: 「Bash 経由は Check 3 で advisory 済・未カバーは Write/Edit ツール経由のみ」に明確化。
- **Minor / conf 6** — 再構築キットの form 一覧に `"n/a"`(quoted) が無い。→ **不採用（accuracy 優先）**: probe で実際に試した 12 形のみ列挙する方針。キットは「代表」と明記済で、reconstructor が追加 form を試せる。未試行 form を「試した」と書くのは不正確。
- **Minor / conf 6** — Task 3（architecture-overview 確認）の「nothing to do」が成果物に未記録。→ **反映済み**: 本レポート対照表 #3 に「競合記述なし＝ポインタ不要」を記録。

Critical=0 / Major=0。技術主張（bypass-direction 0 行／strict 化は tamper backstop 弱体化／commit chokepoint）は実コード（`frontmatter.sh`・`check_status.py:267/865`・`check-gate.sh:174`・`post-status-audit.sh:128-137`・`check-secrets.sh:108-258`）と照合し正確。

## Evidence Checklist

- [x] diff を Read で実読（chat summary ではなく実ファイル）
- [x] plan/spec の受入条件と突合（対照表）
- [x] 未カバーのエッジケースを列挙（Write/Edit ツール経由 .env は意図的に未カバー＝SF-008 で記録）
- [x] 全 finding に severity と confidence 付与
- [x] 技術主張をコードで検証（特に過大主張になりやすい SF-008 commit chokepoint・SF-007 bypass 0 行）

## 判定

**PASS**（Critical/Major=0。Minor 4 件は反映 3・不採用 1〔accuracy 理由〕）。docs-only・production code 変更なし。過大/過小主張なし。canonical 節は「守るもの」を先出しし境界を明示。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "M3（quoted n/a を form 一覧へ追加）は accuracy 優先で不採用＝2次の completeness 指摘に対し『試した form のみ列挙』方針を取った"
    - "他 3 notes（M1/M2/M4）は反映済で 1 次と 2 次に実質的な相違なし（verdict=approve_with_notes 一致）"
```
