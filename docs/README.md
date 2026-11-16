# GNSS資料索引

現行設定・仕様・残課題は以下の正本を参照する。
履歴資料の「次に進める作業」をそのまま現在の指示として実行しない。

| 資料 | 役割 |
| --- | --- |
| [受信機設定・確認状況・残課題](receiver_configuration.md) | 採用した5 Hz・衛星選別設定、保存の証拠、PyGPSClientの注意、今後の検証 |
| [GNSS出力契約](gnss_output_contract.md) | 測位時刻・有効性・共分散・鮮度、無効時非配信、疑似入力試験 |
| [RTK準備と確認記録](rtk_tsudanuma.md) | CIT/松戸の選択、補正経路、認証情報の扱い、再接続、受信とFixの区別 |
| [READMEの互換出力・起動設定](../README.md#gnss_launch-compatible-topics) | 導入・起動・出力トピックの入口 |
| [ローカル保守](../LOCAL_MAINTENANCE.md) | 採用コミット・上流差分・オフライン検証・記録規則 |

## 過去の判断・評価記録

| 記録 | 読む目的 |
| --- | --- |
| [2026-11-09 ドライバー比較](history/2026-11-09_gnss-driver-comparison.md) | ublox_dgnss継続の理由、比較対象と当時の制約 |
| [2026-11-09 PyGPSClientレビュー](history/2026-11-09_pygpsclient-config-review.md) | 特定バージョンの疑似応答で確認した4指摘と再現方法 |
| [2026-11-10までの引継ぎ記録](history/2026-11-10_gnss-handoff.md) | 1 Hz案から5 Hz採用、実機設定保存、RTK既定変更、出力修正までの経緯 |
| [2026-11-16 文書統合の記録](evaluation/2026-11-16_documentation-consolidation.md) | 元資料の対応、保存範囲、文書確認の結果と未実施事項 |

機能変更時は対応する正本を同じ変更で更新し、過去の結果は当時の条件とともに保持する。
新しい受信機設定・実機検証は、明示指示と新たな結果記録が必要。
