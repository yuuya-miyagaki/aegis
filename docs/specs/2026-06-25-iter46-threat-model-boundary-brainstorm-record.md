# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-25（iteration 46）

## テーマ

- full-review backlog の **C4**（gate 値パーサ乖離）と **G4**（secret ゲートの scope）を、検証済みの正直な verdict として明文化してクローズする。あわせて Aegis の脅威モデルを 1 箇所に正典化する。

## コンテキスト

- 現在の状況: iteration 46 / brainstorm。full-review（2026-06-24）の残 backlog は C1〜C4, G4。C2/C3 は iter45 で実装済、C5 は iter44 で実装済。
- きっかけ: C4 を grill-premise + 実測 probe（`/tmp/c4_probe.py`、12 形）で検証した結果、**security ホールではない**と確定（bypass-direction 0 行・strict 化は tamper backstop を弱める net-negative）。G4 も同様に grill-premise すると **大半 by-design**（secret ゲートは Bash git add/commit の**ファイル名**ゲート＝D2 scope。Write/Edit の .env はローカル生成が正常で commit が既存 chokepoint／curl exfil はモデル外かつ regex で防げず futile）。両件ともコード修正は不要で、必要なのは「検証済みの境界を消えない形で残す」こと。

## 検討したアプローチ

### アプローチ A（採用）: 既存 `docs/security-followups.md` を拡張

- 概要: 新規ファイルを作らず、既存の durable security トラッカーに「脅威モデル（canonical）」節を新設し、C4=SF-007（NOT-A-VULN）/ G4=SF-008（by-design）を既存エントリ様式で追記して CLOSED にする。full-review doc の backlog 行と README posture を整合。
- 利点: 既存の正典に集約＝**第3の同期先を作らない**（fragmentation 回避）。SF-001〜006 と同じ読み手の心智モデル。CLOSED 節（現状空）を初めて埋める自然な拡張。脅威モデル文言が各 SF に重複している現状を 1 箇所に集約できる。
- 欠点: security-followups.md が肥大化する（ただし durable トラッカーの本来用途）。

### アプローチ B: 新規 `docs/THREAT-MODEL.md` を作成

- 概要: 脅威モデルと境界を独立ドキュメントに切り出す。
- 利点: 脅威モデルの単一の顔ができる。
- 欠点: security-followups.md / architecture-overview.md / README posture と**第3〜4の同期先**になり drift リスク（過去 second-opinion で「declarative mirror=第3同期先」を P1 指摘された反省と同型）。YAGNI。

### アプローチ C: full-review doc 内だけで closed マークする

- 概要: per-review artifact 内で C4/G4 を closed にするだけ。
- 利点: 最小。
- 欠点: full-review doc は per-review の使い捨て寄り＝durable な security 正典ではない。C4/G4 の verdict は cross-iteration で参照される durable な知見なので不適。

## 決定

- 採用アプローチ: **A（security-followups.md 拡張）**
- 採用理由: 既存の durable 正典に集約するのが maintainability・drift 最小・読み手一貫の観点で最良。脅威モデルの正典化も同ファイルで自然に達成。
- 不採用理由: B=同期先増（YAGNI/drift）。C=durable 性不足。

## スコープ境界

- やること:
  - `docs/security-followups.md` に `## 脅威モデル（canonical）` 節を新設（LLM self-bypass・非 sandbox・非 exfil 耐性・非 content スキャナ・chmod 権持つ敵対者は対象外、を一度だけ明記）。
  - SF-007（C4・NOT-A-VULN・実証付き）と SF-008（G4・by-design boundary）を追記し CLOSED 節へ。
  - full-review doc の backlog 行で C4/G4 を closed 化＋SF へポインタ。
  - README §95 posture を必要なら secret ゲート境界で一行整合。
- やらないこと: 新 THREAT-MODEL.md／curl-exfil の regex ブロック／Write・Edit への新 .env block／content スキャナ／check-control-plane 再設計／コード変更全般。

## 未解決事項

- なし（C4 は実測で verdict 確定済。G4 の境界は threat-model 準拠で確定。security ゲートで verdict を独立検証する）。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-25-iter46-threat-model-boundary-design.md`
- テンプレート名: `SPEC.template.md`
