# 設計: example ミラー自動生成（P3-A / v1.7.2）

- 日付: 2026-06-13
- 対象: v1.7.1（HEAD `33f5c3a`）
- 出典: 第7回全力レビュー `docs/full-review-2026-06-13-context-futureproof.md` §1 M1 / §2 P3
- フェーズ: brainstorm（設計確定）→ writing-plans → grill-plan → TDD 実装 → grill-code

---

## 0. 目的とスコープ

M1＝「example ミラー 520K の手動同期」が最大の保守税。`examples/minimal-project/` が `.claude/{agents,rules,skills,commands}`・`hooks/`・6 scripts を **byte-identical でコミット複製**し、framework の制御ファイルを1つ直すたびに手動 cp が必要（M3 で実際に9ファイル cp した）。

**調査での内訳**: ミラー対象（root のコピー＝自動生成可能）が約66ファイル・~380K、分岐（example 固有の現実プロジェクト中身＝手書き・生成不可）が約24ファイル・~240K。

**スコープ確定（make example 自動生成）**: 生成スクリプトが root のミラー対象を example へ再コピーし、手動 cp の税を消す。example は完全な見本のまま（browsable＝非エンジニア向けの北極星価値を維持）。**committed ミラーの物理除去（smoke-only 化）は非ゴール**（browsable を失うため）。安全網（drift/contract/smoke）は一切改廃しない。

---

## 1. アーキテクチャ

- 新規 `scripts/sync_example_mirror.py` がミラー同期の唯一のエンジン。
- **単一マニフェスト**: `from check_reference_drift import MIRROR_DIRS, MIRROR_FILES, MIRROR_ALLOWLIST`。生成と検証（`check_mirror_identity`）が同じ定義を共有＝乖離しない。`eval_scaffold_smoke.py` が既に `from check_reference_drift import ...` をしている前例あり。
- 薄い `Makefile` に `make example` ターゲット（`python3 scripts/sync_example_mirror.py` を呼ぶだけ）。
- **安全網非破壊**: drift / contract / scaffold smoke はそのまま。生成器は additive。検証は既存 `check_mirror_identity` に委ねる（生成=write、検証=drift で役割分離）。

---

## 2. 同期ロジック（root → example）

- 対象: `MIRROR_DIRS`（`.claude/{agents,rules,skills,commands}`, `hooks`）を rglob ＋ `MIRROR_FILES`（`scripts/` の6本: check_status.py / update-gate.sh / run-test-strength-drill.py / build-judge-card.py / record-test-result.py / status_doctor.py）。
- 各ファイルを root から `examples/minimal-project/<rel>` へ `shutil.copy2`（**mode 保持**＝hooks の実行ビット）。
- **`MIRROR_ALLOWLIST`（`.claude/commands/validate.md`, `retro.md`）は skip**（意図的分岐＝上書きしない）。
- **stale 除去**: MIRROR_DIRS 配下で example に在るが root に無いファイルを削除（allowlist 除外）＝真の sync。分岐ファイル（CLAUDE.md / STATUS.md / docs/*）は MIRROR_DIRS の外なので絶対に触れない。
- 冪等。生成後は現在の committed example と byte 一致（今 in-sync なので無変更＝回帰の起点が明確）。

---

## 3. データフロー・境界

- 入力: root の制御ファイル群。出力: example のミラー部分のみ。
- example 固有の手書き分岐（~240K: README/CLAUDE.md/settings.json/STATUS.md/LEARNINGS.md/docs/requirements・specs・qa-reports・client・handover 等）は**不可侵**。
- 親ディレクトリが無ければ作成（mkdir -p 相当）。

---

## 4. エラー処理・エッジケース

- root に MIRROR_DIRS が無い → その dir は no-op（防御的）。
- example ディレクトリ/サブパスが無ければ作成。
- allowlist ファイルは root/example 双方に在る前提を仮定せず単に skip。
- **`--check` は付けない**: 検証は既存 `check_mirror_identity` が担うため、生成器に検証モードを持たせると重複（DRY 違反）。生成器は write 専任。

---

## 5. テスト（TDD）

- 新規 `tests/test_sync_example_mirror.py`（fake root+example fixture で関数を直接呼ぶ）:
  - **copy**: MIRROR ファイルが byte 一致でコピーされる。
  - **allowlist skip**: example の validate.md/retro.md が上書きされない。
  - **stale 除去**: root に無い example の hook が削除される。MIRROR_DIRS 外の分岐ファイル（CLAUDE.md 相当）は残る。
  - **mode 保持**: 実行ビット付きファイルが実行可能のままコピー。
  - **冪等**: 2回実行で同結果。
- **統合**: 実 repo で sync 実行 → `check_mirror_identity` が緑（現在 in-sync なので無変更で緑＝回帰なし）。
- **マニフェスト共有**: 生成器が drift の MIRROR_* を import している構造自体が単一所有の保証（別途テストは不要）。

---

## 6. 版数・SemVer・docs

- additive ツール・操作契約不変 → **patch v1.7.2**。版数4箇所（`FRAMEWORK_VERSION` 定数 / `templates/STATUS.template.md` / `examples/minimal-project/docs/STATUS.md` / `docs/STATUS.md`）を同期。
- README の dev/メンテ手順に「制御ファイル（hooks/scripts/.claude）編集後は `make example` を実行。未実行は drift が検知」を1文追記。

---

## 7. 検証フロー

設計 commit → writing-plans → grill-plan（致命前提を着手前に実証反映）→ TDD 実装 → grill-code → 全テスト / contract 全 profile / drift / scaffold smoke / redteam PoC 緑 → STATUS.md 更新。

---

## 8. 非ゴール（明示）

- committed ミラーの物理除去（smoke-only 化）。browsable 維持のため不採用。
- 安全網（drift / contract / scaffold smoke）の改廃。生成器は additive。
- 分岐ファイル（example 固有のプロジェクト中身）の生成。
- 生成器への `--check` 検証モード追加（drift に一本化）。
