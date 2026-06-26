# iter48 要件: 配布の参照整合性（self-containment）

## 背景

North Star は「知識の乏しい人が AI と堅牢に作り運用できる足場」。今は solo dogfood、
将来配布予定。配布バグは過去に実害 P1（F6: setup が hooks/lib を配らず install 先で
moat 全死、2026-06-07）。backlog 枯渇後の最初の実需テーマとして配布面の「正しさの穴」
を恒久封鎖する。

## 問題（grill-premise で実証済み・一次情報）

profile↔checker parity / judge toolchain / safety-lib 登録 / moat registration は
**個別には**テスト済みだが、「shipped artifact が参照する依存ファイルが同 profile に
同梱されているか」を**横断的に**検査する仕組みが無い。その網の隙間から、すでに 2 件の
機能が現場（install 先）でサイレントに死んでいる:

1. **D5 ドリフト警告が full install で永久に沈黙**
   `status_doctor.py`（full 同梱）は版ドリフト判定に `check_framework_contract.py` を
   読むが、後者は**どの profile にも入っていない**。実証: `--profile=full` install →
   `check_framework_contract.py` 不在 → stamp を 1.0.0 に改竄しても version-drift 警告
   が出ない（D5 inert）。

2. **JNY-07 の非エンジニア向けテンプレ位置ヒントが install で消える**
   `check_status.py`（全 profile 同梱）は client gate の deny メッセージにテンプレ場所を
   出すため `_artifact_template_map.py` を import するが、`try/except ImportError` で
   **空 dict に degrade**。`_artifact_template_map.py` は**どの profile にも入っていない**。
   実証: full install で import → ImportError → 空マップ。非エンジニア（JNY-07 の対象）は
   「テンプレが無いのに埋めろ」のヒント無し deny に逆戻り。

いずれも「graceful degrade が、未同梱依存のせいで shipped 機能をサイレントに殺す」
同一クラス。iter41 D1（judge toolchain の依存閉包を profile に入れる）と同型で、
個別対処の漏れ。

## 受け入れ基準（このイテレーションの成功条件・測定可能）

- [ ] 各 profile（minimal/standard/full）について、同梱される .py スクリプトが
  実行時に参照する兄弟スクリプト依存が「同 profile に同梱」か「意図的非同梱として
  理由付き allow-list に明記」のいずれかであることを恒久検査するテストが存在する。
- [ ] そのテストが、現状の 2 穴（D5 / JNY-07）を**修正前は RED** で捕まえる。
- [ ] JNY-07 穴を実修正（`_artifact_template_map.py` を full に同梱）して GREEN。
- [ ] D5 穴は「maintainer 専用ツールチェーンで field no-op は by-design」と
  allow-list に理由明記して GREEN（contract ツールチェーン
  = check_framework_contract+platform_manifest+context_budget を install に
  引きずり込まない）。
- [ ] 3 点検証（pytest + `check_framework_contract.py` + `eval_scaffold_smoke.py`）緑
  （LEARNINGS conf9: pytest 単独では framework-root 専用 contract ロジックに未到達）。
- [ ] profile 件数変更に伴い README を同期（`test_readme_profile_counts.py`）。

## スコープ境界

- **やる**: Python モジュール import 辺 + status_doctor→check_framework_contract の
  既知 string-read 辺の横断検査。JNY-07 実修正。D5 allow-list 明記。
- **やらない（YAGNI 線）**: command(.md)→script 参照の網羅検査 / skill 散文中のパス参照
  検査 / 対話的インストーラ / downgrade ガード / orphan 削除（現アーキでは害が投機的）/
  外部ユーザー向けエルゴノミクス / contract ツールチェーンの install 同梱。

## 非対象（将来スライス候補）

- command→script・skill→asset の参照整合性（本スライスの仕組みを拡張すれば追える）。
