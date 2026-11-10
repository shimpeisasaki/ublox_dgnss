# 津田沼キャンパスでのRTK準備

確認日：2026-11-10。対象：ZED-F9P HPG 1.32、Harxon HX-CSX601A。

## 大学CIT局（RTKの既定接続先）

当初の公開HP・GitHub調査では接続先を確認できなかったが、その後ユーザー提供資料で
鈴木太郎先生のNTRIP配信設定が判明した。認証値はこの文書やGitへ保存しない。

| 項目 | 値 |
|---|---|
| ホスト・ポート | `taroz.net:2101` |
| マウントポイント | `CIT` |
| プロファイル | `rtk_source:=cit`（既定） |
| 認証ファイル | `~/.config/ublox_dgnss/ntrip_cit.json`、権限0600、Git管理外 |
| ファイル形式 | `username` と `password` の文字列を持つJSONオブジェクト |
| 基準局座標 | RTCM 1006より北緯35.68844588°、東経140.02018985°、楕円体高145.470 m |

画像の認証情報を使い、**1接続だけ・約9秒**の受信で `ICY 200 OK` と約20 KBのRTCMを確認した。
1006、1077、1087、1097、1117、1127、1230を含む14種類のメッセージがCRC検証を通過した。
GGA送信は行っていない。基準局座標は津田沼キャンパス近傍である。
受信記録は `/home/uedalab/.local/share/pygpsclient/review/rtk_cit_probe_20261110.json`。
この確認以降、今回の既定接続先変更のために大学サーバーへ追加接続はしていない。

認証ファイルは実行時に読む。別PCでは同じ形式のローカルファイルを作成するか、
`credentials_file` 引数または `NTRIP_USERNAME` / `NTRIP_PASSWORD` で認証情報を渡す。
不足時は受信機・NTRIPクライアントを起動する前にエラーにする。
松戸局を選んだ場合は大学の認証ファイルを読み込まない。

## 公開松戸局（選択肢として保持）

GeoRTKは基準局データの利用料を無料としている。
公式一覧から松戸局を候補に選び、以下の接続で実データを取得した。
受信機には接続せず、補正データも渡していない。

| 項目 | 値 |
|---|---|
| ホスト | `geortk.jp` |
| ポート | `2101` |
| マウントポイント | `Matsudo`（大文字小文字を区別） |
| 接続 | HTTP / NTRIP、TLSなし |
| ユーザー名・パスワード | 空欄で受信確認 |
| GGAによる現在位置の送信 | なしで受信確認 |
| 基準局座標 | RTCM 1005より北緯35.77565448°、東経139.92636403°、楕円体高106.281 m |

短時間の受信では、CRCが正しいRTCM 1005、1008、1077、1087、1097、1117、1127、1230を確認した。
基準局位置とMSM観測データの両方が取得でき、F9Pで試すための候補になる。
ネットワークから受信できたことは、キャンパスでRTK Fixすることや精度の保証ではない。
公式一覧と実配信内容には差があり、QZSSの1117は実配信で確認した。

記録：`/home/uedalab/.local/share/pygpsclient/review/rtk_matsudo_probe_20261110.json`。
この記録のCRCエラー数はフレーム同期候補の拒否を含む。配信全体の品質評価は未実施。
配信の継続性、基準局の座標基準・成果の時点、キャンパスの地図との整合は未検証。

参照：

- [GeoRTKの利用案内・無料利用](https://geortk.jp/)
- [GeoRTK公式マウントポイント一覧](https://geortk.jp/mountpoint)
- [F9P HPG 1.32 Interface Description](https://content.u-blox.com/sites/default/files/documents/u-blox-F9-HPG-1.32_InterfaceDescription_UBX-22008968.pdf)

## 準備したROS経路

`NTRIP → ntrip_client_node → /ntrip_client/rtcm → ublox_dgnss_node → F9P USB`

RTK計算はF9Pが行う。PCでは補正データを受信・転送する。
`gnss_rtk.launch.py` は次をまとめて起動する。

- 既存の互換出力launch：5 Hz、ROS RTCM転送とUSB RTCM3入力を有効化。
- 既存のNTRIPクライアント：既定は大学CIT局。`rtk_source:=matsudo` で松戸局を選択可能。

RTKを使わない通常の `gnss_launch_compatible.launch.py` は補正入力無効が既定。
いずれのlaunchもBBR・Flashへは書かない。両方のlaunchを同時起動しない。

## 接続を維持する処理と検証

正常な補正ストリームは同じ接続で受信し続ける。
従来クライアントにあった「10受信コールバックごとに切断」の処理は削除した。
切断・エラー時は30、60、120、240、300秒と再接続待ちを延ばし、最大300秒間隔とする。
遠隔側が正常終了しても即時再接続しない。明示的な設定変更と終了時は進捗コールバックで中断する。
認証値を表示するDEBUGログとlibcurlの認証ヘッダー出力も無効化した。
`reconnect_every_n_cycles` は不要となったため削除した。

継続受信・再接続間隔・終了処理は、公開サーバーではなくループバックの模擬NTRIPで検証する。
実機へRTCMを送ってのFloat/Fix確認、長時間の稼働・精度評価は未実施。

## 実機確認時のコマンド

cat_robotから使う場合は、既存のbringup・mapping・navigation起動コマンドへ
`gnss_mode:=rtk` の一設定を追加する。これだけでGNSS有効化、大学CIT局への接続、
補正転送までを選択する。`use_gnss:=true` を追加する必要はない。
`gnss_mode:=standalone` で単独測位、`gnss_mode:=off` でGNSS無効に戻せる。
松戸局を使う場合は `rtk_source:=matsudo` を追加する。
切り替えはlaunchの再起動時に適用する。

以下は実機確認の手順であり、今回の準備では実行していない。
インターネット接続と、空が開けた場所でのアンテナ設置が必要。

```bash
source /opt/ros/humble/setup.bash
source /home/uedalab/ros2_ws/install/setup.bash
ros2 launch ublox_dgnss gnss_rtk.launch.py frame_id:=gnss_antenna_link
```

別のターミナルで次を確認する。

```bash
ros2 topic hz /ntrip_client/rtcm
ros2 topic echo /ubx_rxm_rtcm
ros2 topic echo /ubx_nav_status
ros2 topic hz /gnss/fix
```

`/ntrip_client/rtcm` はROSへのデータ到着、`/ubx_rxm_rtcm` は受信機側のRTCM処理状態。
RTK状態は `/ubx_nav_status` の `gps_fix_ok`、`carr_soln_valid` と `carr_soln.status` を合わせて確認する。
`carr_soln.status` は0が解なし、1がFloat、2がFix。位置の鮮度も確認する。
NavSatFixのstatusだけではFloatとFixを区別できないため、Fixの判定には使わない。

補正データを受信できてもFloatや単独測位に留まることがある。Fixの有無・継続時間と、
位置・共分散・欠測を単独測位と比較する。RTKも建物付近のマルチパスを解消する保証はない。
保存済みの最低10衛星・仰角30°・C/N0 30 dB-Hzは維持するが、
単独測位用の入力条件がRTKにも同じように適用されるかは実機評価が必要。
既存NavSatFix変換の時刻一致・無効値処理の改善も引き続き必要。

単独測位に戻す場合はRTK launchを終了し、通常の互換出力launchを起動する。
これでROS転送とUSB RTCM3入力を無効にする。受信済み補正の効果が消えるまでの遷移は、
受信機の有効状態・RTK状態を見て判断する。
