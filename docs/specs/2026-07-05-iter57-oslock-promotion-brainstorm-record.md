# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-05

## テーマ

- iter57 構造リアーキ: 主 moat 交代 — OS-lock（cp-lock）昇格・`check-control-plane.sh`（979行）退役

## コンテキスト

- 現在の状況: control-plane 保護は layer-1（`check-control-plane.sh`・コマンド文字列の静的解析・deny）＋
  layer-2（`hooks/lib/cp-lock.sh`・chmod ベース OS-lock・非致命）の二層。layer-1 は SF-001〜005 の
  バイパス実績があり、iter54 の Critical（case-insensitive FS）もこの「文字列判定」クラス。
  グリル 2026-07-02 が「共通根＝文字列判定。OS-lock 昇格＋層1退役が最大 ROI」と評価。
- きっかけ: 退役は 2026-06-21 PoC で一度 GO 判定 → 同日の設計 rev.2 で撤回（①Windows で chmod no-op
  ②raw EACCES が chmod +w 自己修復を誘発 ③難読化耐性の無償維持）という**相反する先行判断**が併存していた。
  本 brainstorm は rev.2 撤回理由 3 点の現時点再評価が核心。

## 検討したアプローチ

### アプローチ A: 一気交代（1イテレーション完結）

- 概要: cp-lock を主 moat に昇格（fail-visible 化＋実状態検証）、残余ミニフック新設
  （runtime-state ガード＋chmod-unlock deny）、EACCES 説明 advisory 新設、`check-control-plane.sh` 削除。
- 利点: 複雑性負債（979行＋専用テスト群＋SF 追いかけっこ）を即解消。保護は文字列照合の「形の列挙」から
  syscall の「形非依存」へ強化。検証は SF 再現カタログの lock 下実走（EACCES＋INTACT）で構造的に可能。
- 欠点: moat 交代と退行網の張り直しが同時＝ブラスト半径が大きい。テスト置換を1イテレーションで完遂する必要。

### アプローチ B: 2段階移行（iter57 advisory 共存 → iter58 削除）

- 概要: iter57 で cp-lock 昇格＋check-control-plane を deny→warn 降格、実運用1周後に iter58 で削除。
- 利点: 実証データを1周挟める。
- 欠点: deny→warn のテスト全面書換を iter57 で行い iter58 で全て捨てる二度手間。2イテレーション拘束。
  advisory×EACCES ペアログの情報量は案 A の lock 下実走テストとほぼ等価で、追加の安全マージンが薄い。

### アプローチ C: rev.2 維持（昇格のみ・退役なし）

- 概要: layer-1 存置のまま cp-lock のロバスト化のみ。
- 利点: 回帰リスク最小。
- 欠点: 複雑性負債が丸ごと残り、グリル指摘の ROI を放棄。文字列判定の穴を毎グリルで塞ぎ続ける
  トレッドミル（iter54 Critical で実証）が継続。

## 決定

- 採用アプローチ: **A（一気交代）**
- 採用理由: rev.2 撤回理由の再評価で全点に決着 — ①Windows: **公式サポートを macOS/Linux/WSL に限定**と
  ユーザー決定（実利用は macOS・Windows 配布は現状仮定の話・退役コードは git 履歴に残存）
  ②EACCES 自己修復誘発: 残余ミニフックの chmod-unlock deny 維持＋EACCES 説明 advisory で恒久対処
  ③無償維持ではない: iter54 Critical・SF 追いかけっこでトレッドミルコストが実証済み。
- 不採用理由: B は二度手間で安全マージンの上積みが薄い。C は Windows 割り切り決定後に残る根拠がない。

## スコープ境界

- やること: `check-control-plane.sh` 退役／cp-lock 昇格（fail-visible＋verify）／残余ミニフック新設／
  EACCES advisory 新設／SF-001〜005 台帳更新／README・脅威モデル記述・profile/contract/配線の整合／
  テストの置換マッピング付き移行。
- やらないこと: check-secrets / check-gate の改修（文字列判定の縮退は別テーマ）／意味ドリフト検査の機械化／
  fable lineage manifest／敵対 sandbox 化（os.chmod 解錠は従来どおり脅威モデル外）。

## 未解決事項

- SemVer の最終判定（MINOR v1.18.0 想定・Windows サポート表明の扱いを plan で確定）
- 残余ミニフックの正式名・EACCES advisory の PostToolUse 出力形式（plan で確定）

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-05-iter57-oslock-promotion-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->
