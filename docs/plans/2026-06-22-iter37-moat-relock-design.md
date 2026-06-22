# iteration 37 — moat lifecycle re-lock（設計）

> task_type=framework・size=M（plan で確定）・iteration 35 follow-up（繰延項目）。
> スコープ（ユーザー承認）= **(a) セッション中の task_type 切替での再施錠のみ**。
> アプローチ **C**（共有関数に集約）承認済み。本ドキュメントが決定の正典。

## 背景と問題

layer-2 immutable moat（iteration 35）は安定 CP（hooks/scripts/templates/CLAUDE.md/.claude/rules,skills,commands,agents）を
`chmod -R a-w`（lock）/`chmod -R u+w`（unlock）で OS レベルに保護する事故保険層。
現状の lock/unlock 発火点は **`hooks/session-start.sh:272-280` の1箇所のみ**:

- `task_type == framework` → `aegis_cp_unlock`（framework 編集を許可）
- それ以外 → `aegis_cp_lock`（非 framework 作業中の偶発 framework 編集を防止）

lock 状態は次の session-start まで再評価されない。よって:

- **(a) セッション中 task_type 切替**: framework イテレーションで unlock したまま、同一セッションで
  feature/bugfix に移ると **CP が unlock のまま**＝layer-2 がまさに必要な場面で無効。日常的に発生。
- (b) クラッシュ/終了窓: framework セッションが unlock 後にクラッシュ→次 session-start まで unlock 継続。
  ただし次が非 framework なら session-start が再 lock＝大部分は自己修復。**本イテレーションのスコープ外**。

## アプローチ（採用 C）

| | 案 | トレードオフ | 判定 |
|---|---|---|---|
| A | post-status-audit に lock 判定をインライン追加 | 安価だが判定が session-start と2重化＝ドリフト源 | 不採用 |
| B | PreToolUse で毎ツール前に再評価 | 最も厳密だが hot-path に毎回 chmod 判定＝iter33 方針に逆行・過剰 | 不採用（YAGNI） |
| **C** | **共有関数に集約＋ post-status-audit から呼ぶ** | lock 判定を単一ソース化（ドリフト不能）・的確な発火点・フリップ時のみ chmod で安価 | **採用** |

## 設計詳細

### コンポーネント

1. **新関数 `hooks/lib/cp-lock.sh::aegis_cp_apply <root> <task_type>`**
   - `desired = (task_type == "framework") ? unlock : lock`
   - sentinel プローブで現状を判定し、**desired と不一致のときだけ** `aegis_cp_lock`/`aegis_cp_unlock` を呼ぶ（冪等）。
   - rc 0/1（chmod 失敗は非致命＝既存規約。layer-1 静的 moat は常時有効）。

2. **`hooks/session-start.sh` リファクタ（挙動保存）**
   - `:272-280` のインライン if/else を `aegis_cp_apply "$ROOT" "$TASK_TYPE"` 呼び出しに置換。
   - 失敗時の CONTEXT への WARNING 付与は維持。判定は不変。

3. **`hooks/post-status-audit.sh` 追加**
   - 既に STATUS frontmatter（task_type 等）をパースしている。gate-tamper 監査の**後**に
     `aegis_cp_apply "$ROOT" "$TASK_TYPE"` を副作用として呼ぶ。
   - 失敗は非致命。**emit する JSON 判定（allow/deny）には一切影響させない**（防御的に分離）。

### sentinel プローブと正しさ

- 代表 CP（`hooks/session-start.sh`）の `[ -w ]` で現状を判定: 書込可=unlock 中／不可=lock 中。
- 不一致時のみ `chmod -R`＝頻繁な STATUS 編集でもコスト最小。
- プローブは**最適化**であり、判定方向は常に安全側に倒す:
  - desired=lock: sentinel が書込可（unlock 中）なら lock、不可なら skip。
  - desired=unlock: sentinel が書込不可（lock 中）なら unlock、可なら skip。
- moat は uid≠root 前提なので非 root で `[ -w ]` は正確（root は permission bit を bypass するが、
  その場合でも上記論理は「迷えば lock」側＝安全）。
- **default-lock**: task_type が空/読めない時は非 framework 扱い＝lock（既存 session-start else 分岐と同一の安全既定）。

### データフロー

- session-start: STATUS の TASK_TYPE → `aegis_cp_apply`。
- mid-session: エージェントが STATUS の task_type を Edit/Write → PostToolUse 発火 → post-status-audit.sh が
  新 TASK_TYPE を読む → `aegis_cp_apply` → 必要時に lock をフリップ。

### 重大エッジケース（iter36 と直結・必須対応）

`post-status-audit.sh` を**新たな lock トリガ**にすると、これを起動するテストの scratch が lock される。
`tests/test_phase_skill_injection.py:61` は実 `scripts/check_status.py` を **symlink** しつつ post-status-audit を
起動するため、iter36 Bug A（`TemporaryDirectory` cleanup の `resetperms` が `os.chmod` で symlink を辿り実ファイルを
0o700 化）が**新トリガで再発**する。よって本イテレーションは:

- **post-status-audit を起動する全テスト scaffold の symlink→`shutil.copy2` 化**（実ファイルを scratch に
  symlink しない）。
- **回帰ガード**（scaffold の対象が非 symlink）を追加。
- **不変条件**: full suite 実行後に実 `scripts/check_status.py` の mode が 644 維持（iter36 の不変条件を継続ガード）。

実装時に post-status-audit を起動する全テストを列挙し、実リポファイルを symlink している箇所を洗い出す。

### エラー処理

- chmod 失敗は非致命（警告して継続）。layer-1 静的 moat は常在。
- cp-lock.sh / 関数が利用不可なら skip + 警告（session-start の既存挙動を踏襲）。
- post-status-audit の主務（gate-tamper 監査）を cp_apply 失敗で壊さない（防御的にラップ）。

### テスト（TDD）

- `tests/test_cp_lock_lib.py`: `aegis_cp_apply` の
  framework→unlock／非 framework→lock／既状態→no-op（冪等）／task_type 空→lock（default-lock）。
- 統合: STATUS の task_type を mid-session で feature に変えると post-status-audit が再 lock することを実証。
- 回帰: full suite 後に実 `scripts/check_status.py` が mode 644 維持。
- 挙動保存: session-start の lock/unlock が共有関数化後も同一判定。
- post-status-audit 起動テストの symlink→copy 回帰ガード。

### スコープ境界（YAGNI）

やらないこと:
- PreToolUse 毎ツール再 lock（案 B）
- SessionEnd / Stop での default-lock（(b) クラッシュ窓硬化＝スコープ外）
- `settings.json` の lock（iter35 で意図的除外）
- root 向け `chattr +i` / `chflags uchg` 硬化

### 規模とゲート

- 触るファイル: `hooks/lib/cp-lock.sh`・`hooks/session-start.sh`・`hooks/post-status-audit.sh`・
  `tests/test_cp_lock_lib.py`・`tests/test_phase_skill_injection.py`（＋他の post-status-audit 起動テスト）・
  contract/版・docs。
- 見込み **M**（6+ になれば L に更新）。framework・security 関与（moat）につき **review+qa+security 必須**（M は deploy skip）。
