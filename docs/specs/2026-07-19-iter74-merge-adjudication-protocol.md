# Aegis 二重レビュー — 突合・裁定プロトコル（親セッション用）

> 目的: Codex（外部・隔離 clone）と Fable（盲検2次・隔離 clone）の2レビュー出力を突合し、
> 乖離を実証で裁定し、確定所見を iter74+ の改善ロードマップに落とす。
> この文書は**親（オーケストレーター）だけが使う**。2人のレビュアーには渡さない（盲検維持）。

## 0. 前提の固定（レビュー起動前に親が確定）

- **対象コミット**: `77566eda7d15cb70d6ca68377fdbd764834d6fe5`（両指示文 §0 に埋め込み済み）。
- **2つの clone を用意**: それぞれ read-only。Codex 用と Fable 用で同一 SHA を checkout。
- **Fable の起動条件（盲検）**: 本セッション（レビュー設計を全て見た文脈）から起動しない。
  clean context の別 Claude Code セッション、または clean な subagent に、
  `fable-review-instruction.md` の中身**だけ**を渡す。設計議論・攻撃仮説を持ち込まない。
- **Codex の起動条件**: 隔離 clone で `codex` を起動し `codex-review-instruction.md` を渡す。
  実行環境（OS/grep/bash/python/locale）は成果物冒頭に記録される規約。
- **成果物パス**: Codex→`docs/codex-review-<date>.md`、Fable→`docs/fable-review-<date>.md`。
  ※隔離 clone 内の docs/ に書かれる。親は両ファイルを回収して突合する。

## 1. 回収・健全性チェック（突合の前提）

両成果物を回収したら、突合前に次を確認する。欠けていたら当該レビューを差し戻す（SendMessage で継続）:

- [ ] 冒頭に対象 SHA が一致記録されているか（不一致なら結果は無効）。
- [ ] 実行環境（特に **grep が BSD か GNU か**）が記録されているか。
- [ ] `STATUS: PARTIAL` か。PARTIAL なら未着手次元を把握し、突合で「片方未カバー」として扱う。
- [ ] `reproduced` 所見に生出力が逐語で貼られているか。無ければ `hypothesis` に格下げして扱う。
- [ ] ID が `<次元>-<連番>` 規約に従っているか。層1の6プレフィックス（MOAT/SF/LOCALE/TEST/REGR/NORTH）が両者で一致しているか。

## 2. 突合表の作成

**層1（共通6次元）は次元プレフィックスで同次元内マッチング**する。各次元ごとに、両者の所見を並べ、意味ベースで対応付けて3分類:

| 分類 | 定義 | 扱い |
|---|---|---|
| **一致（both）** | 両者が同一対象を指摘 | **高確度**。severity は高い方を採用（差があれば §3 で較正）。確定所見候補。 |
| **片方のみ（single）** | 一方だけが指摘 | **要裁定**。相手が「見落とし」か「見て非該当と判断」かを区別（相手の除外リスト §末尾と照合）。 |
| **乖離（divergence）** | 同一対象で verdict/severity が食い違う | **最優先裁定**。iter72 F-CRIT-1 の実績どおり、ここに High 級バグが潜む。 |

- 層2 は次元が非重複（Codex=DIST / Fable=HARNESS・CTX・MODEL）なので突合対象外。各々を independent finding として確定プールへ入れる（ただし §3 の実証裁定は等しく課す）。
- `FRESH-1/2/3`（白紙 top3）は「既知に落ちたか/新規か」を別欄で記録。両者の白紙 top3 が一致する経路は特に注視（独立に危険と見た＝高確度）。

## 3. 乖離・片方のみの裁定（親が実証）

**意見では決めない。親が再現手順を実走して真偽を判定する。** Aegis の既存原則を継承:

1. **生出力の再走**: 所見の実行コマンドを親環境（macOS/BSD grep が基準）で再実行し、主張どおりの出力になるか確認。
2. **環境差の切り分け**: 乖離が Codex(Linux/GNU) と Fable(macOS/BSD) の grep 実装差に起因しないか。差なら「真の乖離」ではなく「移植性の所見」として別枠（＝それ自体が locale/byte 次元の新規指摘になりうる）。
3. **到達可能性の検証**: severity 較正。「モデルが実際に emit しうる入力か」を実証（iter73 の格下げ教訓）。理論限界の主張は実証してからのみ受理。
4. **裁定記録**: 各裁定に {対象 ID, 分類, 親の再現結果, 最終 verdict, 最終 severity, 根拠} を残す。

## 4. 確定所見 → ロードマップ

裁定を通った確定所見を、impact × effort でスコアしてテーマ分割:

- **impact**: North Star（配布可否・保守負荷・非エンジニア運用）への影響 × severity。
- **effort**: 既存機構内の配線変更（S）／新機構（M/L）。前回レビューの「配線変更で根絶可能」分類を踏襲。
- **出力**: iter74 以降の複数 iteration に割り付けたロードマップ。1テーマ=1 iteration を基本（前回 R 群と同型）。
- **この二重レビュー実施＋ロードマップ策定そのものを1つの framework iteration** として STATUS に載せる（成果物＝新レビュー正本 = 突合済み確定所見 + 本ロードマップ）。

## 5. 成果物（親が書く）

- `docs/full-review-<date>-dual-<codex+fable>.md` — 突合済みの確定所見・裁定記録・ロードマップ（前回 `full-review-2026-07-06-six-dimensions-evolution.md` の後継正本）。
- 元の2レビュー（codex-review / fable-review）は evidence として docs/ に残す（監査証跡）。
- 新規 SF が出たら `docs/security-followups.md` に起票。恒久教訓は `docs/LEARNINGS.md`（confidence 付き）。

## 6. 実行順チェックリスト

1. [ ] 2 clone を SHA `77566ed` で用意（read-only）。
2. [ ] Codex を隔離 clone で起動（codex-review-instruction.md）。
3. [ ] Fable を clean context で起動（fable-review-instruction.md・設計文脈を持ち込まない）。
4. [ ] 両成果物を回収 → §1 健全性チェック（不備は差し戻し）。
5. [ ] §2 突合表作成（次元内マッチ・3分類）。
6. [ ] §3 乖離/片方のみを親が実走裁定。
7. [ ] §4 確定所見を impact×effort でロードマップ化。
8. [ ] §5 正本を書き、iteration として STATUS 更新・ユーザー承認。
