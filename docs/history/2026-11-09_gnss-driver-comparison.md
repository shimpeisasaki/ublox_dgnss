> 履歴資料：元のワークスペース直下の `GNSS_DRIVER_COMPARISON.md` を2026-11-16に移管。
> 本文は当時の記録であり、古い設定・未実装事項・次の作業は現行指示ではない。
> 現行資料は [GNSS資料索引](../README.md) と [受信機設定・残課題](../receiver_configuration.md) を参照。
> 本文中の `src/` で始まるパスは、当時のワークスペースルートを基準に読む。

# GNSSドライバ比較

調査日: 2026-11-09。対象はROS 2 Humble、F9Pを想定した単独測位・1 Hz。
ハードウェアの起動・受信機設定変更・実測比較は行っていない。

比較後の対応: 現行の`ublox_dgnss`を継続する方針となり、比較用の`src/ublox`と
`ublox_gps`・`ublox_msgs`・`ublox_serialization`のbuild/install成果物を削除した。
既存のapt版は残している。以下の取得・overlayに関する記述は比較実施時の記録。
`ublox_dgnss`には上流`1cd9ca9`（NAV-SAT予約ビットの修正）を取り込み、
ローカルのGNSS互換launchを保持した。取り込み後のHEADは`b52cee2`。
更新後はHumbleで`ublox_dgnss`・`ublox_nav_sat_fix_hp_node`までの6パッケージの
ビルドが成功した。受信機を使った動作確認は行っていない。
apt版4パッケージ（`ros-humble-ublox`とgps/msgs/serialization）の削除も依頼された。
aptの削除シミュレーションではこの4つのみが対象だったが、実削除はsudoの
パスワードが必要なため実行できず、apt版は残っている。autoremoveは行っていない。
その後ユーザーが削除を実施し、4パッケージがdpkgに存在しないことを確認した。
比較用ソース・build/install成果物も存在せず、ROSから`ublox_gps`は見つからない。
`ublox_dgnss`はワークスペースのinstallから解決されることを再確認した。

## 対象

- 現行: `src/ublox_dgnss`、上流 `aussierobots/ublox_dgnss`、ローカルHEAD `abd2cab`。
- 比較用に取得: `src/ublox`、`KumarRobotics/ublox` の `ros2` ブランチ、
  `3a3e1c253722b68e350a60aee6ef399d8c2304cb`（package version 3.0.0）。
- 比較用取得以外のソース変更、既存bringupの切り替えはしていない。

## ソース比較

| 項目 | 現行 ublox_dgnss | KumarRobotics ublox_gps |
|---|---|---|
| 1 Hz設定 | CFG_RATE_MEAS=1000、CFG_RATE_NAV=1で可能。現在の互換launchは250 ms | rate=1.0、nav_rate=1で可能 |
| 仰角・最低C/N₀・最低衛星数 | 対象CFG項目が静的マップとF9PのTOMLリストにない | メッセージ定義はあるが、設定するROSパラメータと呼び出しがない |
| PDOP・位置精度マスク | 対象CFG項目の登録追加が必要 | 設定するROSパラメータと呼び出しの追加が必要 |
| 位置の生成元 | NAV-HPPOSLLH | F9向けの経路はNAV-PVT |
| NavSatFixの共分散 | NAV-COVのNED行列をENUに変換。非対角成分も保持 | NAV-PVTのhAcc²を東・北、vAcc²を上に設定。非対角は0 |
| 位置と精度の時刻 | 直近の状態・共分散を位置に使用。iTOW一致確認なし | 位置とhAcc/vAccが同一NAV-PVTメッセージ内 |
| 有効判定 | NavSatFix変換でgps_fix_ok、位置invalidフラグ、pos_cor_validを確認しない | GNSS_FIX_OKを確認し、無効時はSTATUS_NO_FIX。ただし座標・共分散付きで配信する |
| 生のNAV-COV | 対応、NavSatFixにも使用 | navcovトピックに出力可能だがNavSatFixには使用しない |
| 接続方式 | libusb | シリアル、TCP/UDP経路 |

主な確認箇所:

- `src/ublox/ublox_gps/src/node.cpp`: パラメータ、受信機設定、NAV-COVの単独配信。
- `src/ublox/ublox_gps/src/ublox_firmware9.cpp`: F9用信号設定。
- `src/ublox/ublox_gps/include/ublox_gps/ublox_firmware7plus.hpp`: NAV-PVTから位置・共分散・有効状態を生成。
- `src/ublox_dgnss/ublox_dgnss_node/include/ublox_dgnss_node/ubx/ubx_cfg_item_map.hpp`: 対応する設定項目。
- `src/ublox_dgnss/ublox_dgnss/config/f9p_ubx_config.toml`: F9P用設定項目の選択。
- `src/ublox_dgnss/ublox_nav_sat_fix_hp_node/src/ublox_nav_sat_fix_hp_node.cpp`: 現行の位置・共分散変換。

## 判断

乗り換えるだけで衛星選別の設定が揃うわけではない。今回の目的には、
現行ドライバに受信機の入力フィルタ設定を追加し、位置・状態・共分散の
有効性と測位時刻を確認する出力処理を整える方が変更範囲は小さいと判断する。

座標と共分散だけを利用する場合、KumarRobotics版のSTATUS_NO_FIXだけでは
無効測位を見落とす。どちらもドライバ出力契約の検討が必要。
無効測位に古い位置や共分散を流用しないこと、欠測を扱うことが必要。
これらは受信機出力の整合性確認であり、ROS側の平滑化・センサー融合を意味しない。

メーカーのF9 HPG 1.32仕様では、CFG-NAVSPG-INFIL_MINCNO、MINELEV、MINSVS、
OUTFIL_PDOP、OUTFIL_PACCが定義されている。実機の型番・FWでの対応と設定反映は未確認。
設定閾値の有効性、マルチパス環境での実精度はソース比較やビルドでは確認できない。

参照: https://content.u-blox.com/sites/default/files/documents/u-blox-F9-HPG-1.32_InterfaceDescription_UBX-22008968.pdf

## ビルド検証

ROS 2 Humbleで`ublox_serialization`、`ublox_msgs`、`ublox_gps`の3パッケージを
ビルド・インストールできた。初回コンパイルではADR関連のメンバー初期化順序警告が
あったが、エラーはなかった。ノードの起動は行っていない。

初回のワークスペース全体探索では`tools/blender_mcp_setup/`内のPythonコードを
colconが誤って探索し、パッケージ識別エラーを表示した。対象ソースに探索範囲を
限定した以下の再確認では、3パッケージが正常終了した。

```bash
source /opt/ros/humble/setup.bash
colcon build --base-paths src/ublox src/rtcm_msgs --symlink-install \
  --packages-up-to ublox_gps --executor sequential
```

既存環境にはapt版`ros-humble-ublox-gps` 2.3.0もインストール済みだった。
今回のソース版3.0.0はワークスペースのoverlayに追加されており、
`install/local_setup.bash`等をsourceするとソース版が優先される。
既存のcat_robot bringupは引き続き`ublox_dgnss`を参照している。
`ros2 pkg prefix ublox_gps`と`ros2 pkg executables ublox_gps`で、ソース版の
パッケージと実行ファイルが解決されることを確認した。
比較表は取得したソース版3.0.0に対するもので、apt版2.3.0の実装比較ではない。
