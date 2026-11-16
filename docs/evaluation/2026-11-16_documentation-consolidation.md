# ワークスペース直下GNSS資料の統合・整理

実施日：2026-11-16。対象repoは `ublox_dgnss`、作業ブランチは
`refactor/implementation-20261112`、開始コミットは
`e8deb989d2188d380e55d98ba50953a3239d3443`。開始時の作業ツリーはclean。

## 変更内容と元資料

| 元のワークスペース直下ファイル | 移管先 |
| --- | --- |
| GNSS_HANDOFF.md | [履歴引継ぎ](../history/2026-11-10_gnss-handoff.md) |
| GNSS_DRIVER_COMPARISON.md | [ドライバー比較](../history/2026-11-09_gnss-driver-comparison.md) |
| PYGPSCLIENT_CONFIG_REVIEW.md | [PyGPSClientレビュー](../history/2026-11-09_pygpsclient-config-review.md) |

元の本文を保存し、先頭に履歴資料の注意書きを加え、移管文書間のMarkdown相対リンクだけを
修正した。日付は記録の元日付であり、2026-11-16の実測や再試験を意味しない。
各原文のSHA-256を下記へ記録する。

- `GNSS_HANDOFF.md`：`aefa67fb4de41922ef96de941a230dc41379be1cde607608e0010566cd3b461c`
- `GNSS_DRIVER_COMPARISON.md`：`db972b0c5e1f6a11d87919dee80a1ea619bed493be505b9c3216eac62e2343c6`
- `PYGPSCLIENT_CONFIG_REVIEW.md`：`43caaaecd591d1e8f9d35a986519e8f1f65366a474fad3bd8eb6b8e94755ec48`

現行情報は [受信機設定](../receiver_configuration.md)へ統合し、出力・RTKの詳細は既存の
正本へリンクした。古い1 Hz案、4 Hz時代のlaunch、出力整合性の未実装記述を
現行手順から分離し、5 Hzの採用設定・残課題・PyGPSClientの注意をまとめた。
既存README、LOCAL_MAINTENANCE、AGENTSとワークスペースの資料索引から案内する。

ワークスペース直下の `symlink_install_manifest.txt` は、旧 `install/cat_panorama/` の
生成物パス一覧であることと、関連資料・保守ツールから参照が見つからないことを確認して除去した。
この一覧にあるinstall成果物自体は削除しない。

## 文書検証

入力は元の3文書、現行のGNSS出力・RTK仕様、互換launchソース。
環境は当ワークスペースのPython 3とGit。外部URLの取得、受信機・NTRIP接続は行わない。
変更したのは文書のみで、製品コード・受信機設定・認証情報は変更していない。

- 原文保存：3文書で一致。変更は注意書きと移管文書への相対リンクのみ。
- Markdown相対リンク：58件の参照先が実在。外部リンク・見出しfragmentの網羅検証は対象外。
- 旧install一覧：27行すべてが旧cat_panoramaの生成物パス。
- `git diff --check`：終了0。最終stage後にも差分検査を行う。
- 実行結果：文書確認成功。runtimeテスト件数0（実施不要）、実機検証なし。

実行時は開始コミットに今回の文書差分がある状態で確認した。
チェックの内容：原文保存照合、Markdown相対リンクの実在確認、
旧ファイル名へのリンク残存検索、文書以外のrepo変更がないこと、`git diff --check`。
ソース変更のない文書整理のため、build、pytest、ROS試験、GUI、実機操作、
大容量ログ・画像・重みの読み込みは実施していない。

## 保存範囲

このrepoへ移した文書と索引はrepoの履歴に保存する。
ワークスペース直下の `docs/README.md` の索引更新や直下ファイルの除去は、
ワークスペースがGit管理されていないため、このrepoのコミットには含まれない。
元の引継ぎ本文と外部証拠ファイルのパスは残すが、証拠JSON自体の移管・再検証は行わない。
