> 履歴資料：元のワークスペース直下の `GNSS_HANDOFF.md` を2026-11-16に移管。
> 本文は当時の記録であり、古い設定・未実装事項・次の作業は現行指示ではない。
> 現行資料は [GNSS資料索引](../README.md) と [受信機設定・残課題](../receiver_configuration.md) を参照。
> 本文中の `src/` で始まるパスは、当時のワークスペースルートを基準に読む。

# GNSSマルチパス対策 引き継ぎ

更新日: 2026-11-10
ワークスペース: `/home/uedalab/ros2_ws`（Ubuntu / ROS 2 Humble）

## 同日追記：受信機設定とlaunchの更新

### NavSatFix出力の整合性修正

- ユーザーの依頼で、位置・共分散・状態のiTOW一致、有効性判定、疑似データ検証まで実施した。
  **無効・欠測・時刻不一致では位置を配信しない**方針で合意済み。
  NO_FIX座標や過去の有効位置を代わりに配信しない。利用側が途絶・鮮度を見て採用を止める。
- `ublox_nav_sat_fix_hp_node` は到着順序に依存せず、同じiTOWの位置・共分散・状態を待ち合わせる。
  既定1秒で期限切れとし、入力headerの鮮度も確認する。最大32エポックまで保持。
  gps_fix_ok、位置invalid、pos_cor_valid、共分散の構造的妥当性を確認する。
  2Dを禁止する追加変更はしていない。
- 速度は同じiTOWの速度・状態・共分散とvel_cor_validを確認し、位置とは独立に配信判定する。
  NAV-COVの速度共分散をENUへ変換し、非対角成分も保持する。
- 同じ/古いエポックの再配信を抑止し、GPS週境界は正常に扱う。
  入力headerを保持するもので、GPS絶対時刻を新たにROS時刻へ変換する処理は追加していない。
- NavSatStatusは状態の誤断定を避け、有効時STATUS_FIX、service=0（未特定）とする。
  RTK Float/Fixや衛星系の判定には元のUBXトピックを使う。
- 関連6パッケージのビルド成功。変換ノードのみを起動する疑似ROS試験42件が成功した。
  到着順序、欠落・無効、古い共分散・header、時刻不一致、期限切れ・復帰、重複・逆順・途絶、
  ENU変換、週境界、不正値を検証した。受信機・NTRIP・ロボットは起動していない。
- 現在の契約は `src/ublox_dgnss/docs/gnss_output_contract.md` を参照。
  以下の経緯にある「時刻一致・無効値処理が未修正」という記述はこの実装で置き換わる。
  実機出力率・保存設定保持・RTK Fix・位置精度の評価は未実施のまま。

### 後続のRTK準備（単独測位の既定は維持）

- **現在のRTK既定接続先は大学CIT局**。ユーザー提供の資料にある設定で
  `taroz.net:2101/CIT` に1回だけ接続し、約9秒でCRC検証済みRTCMを取得した。
  受信記録は `~/.local/share/pygpsclient/review/rtk_cit_probe_20261110.json`。
  実機受信機への補正転送・RTK Fix確認は未実施。
- `gnss_mode:=rtk` は大学CITを選択する。松戸局は `rtk_source:=matsudo` で選択できる。
  既定の `rtk_source` は `cit`。GNSS自体の既定offは維持している。
- 大学局の認証情報は `~/.config/ublox_dgnss/ntrip_cit.json`（権限0600）へ保存した。
  **認証値や提供画像をGitへ入れないこと。** 松戸局選択時にはこのファイルを読まない。
  不足時はRTKノードを起動する前にエラーにする。
- 正常受信中に10コールバックごとに転送を終了していた既存NTRIP処理を削除し、接続を維持する。
  エラー・相手側終了後の待ちは30秒から最大300秒へ増やす。終了・明示的設定変更は進捗で中断する。
  認証値を出力するDEBUGログとlibcurlの詳細ログも無効化した。
  古い `reconnect_every_n_cycles` パラメータは削除した。
- この変更のため大学・松戸サーバーへの追加アクセスは行っていない。
  対象4パッケージのビルド、ループバック模擬NTRIPの4試験（38秒）、
  各起動経路の選択24ケースと認証不足の拒否3ケースを確認した。
  模擬試験ではHTTP/ICYの継続受信、実際の30秒再接続待ち、正常切断後の待ち、速やかな終了と
  DEBUGログへテスト認証が出ないことを確認した。公開サーバーや受信機は使っていない。

以下はRTK準備の経緯であり、既定接続先は上記のCIT設定を優先する。

- ユーザーの「設定一つで使えるように」の依頼により、cat_robotのbringup・mapping・navigationに
  `gnss_mode`（`off` / `standalone` / `rtk`）を追加した。
  **`gnss_mode:=rtk` だけでGNSSと松戸局NTRIPを有効化**できる。
  既定はoff、従来の `use_gnss:=true` は単独測位として互換維持。
  `gnss_mode` 明示時はそちらを優先し、切り替えはlaunch再起動時に適用する。
  対象3パッケージのビルドと、3起動経路×7条件の計21ケースをオフラインで確認した。
  実機ノード・ロボットは起動していない。
- ユーザーの依頼で `gnss_rtk.launch.py` を追加した。既定の候補は無料GeoRTKの
  `geortk.jp:2101/Matsudo`。ネットワークから補正データを受信し、CRCが正しい基準局座標・
  MSM観測メッセージを確認したが、受信機へのRTCM送信・RTKの実機起動はしていない。
- 通常の互換launchに `rtcm_input_enabled`（既定false）を追加。
  ROS転送とUSB RTCM3入力を同時に切り替える。RTK launchだけtrueを渡す。
  したがって現在は周期・USB出力に加え `CFG_USBINPROT_RTCM3X` もRAMへ設定する。
  単独測位でfalse、RTKでtrue。衛星選別条件は上書きしない。
- NTRIP launchのパラメータ型を明示し、空の認証情報や数字のみの文字列を保持できるようにした。
- 関連6パッケージのビルド、単独/RTKのネストしたlaunchのオフライン構築、
  既定値・接続先変更・空の認証情報・数字に見える文字列の確認、diffチェックを通過。
- 学内の鈴木太郎先生のRTKサーバーを優先する可能性がある。
  公開HPと関連GitHub資料では接続情報を確認できていない。先生への問い合わせ送信はしていない。
- 詳細と未検証事項：`src/ublox_dgnss/docs/rtk_tsudanuma.md`。

以下の「最初に読む要約」以降は、この会話を開始した時点の引き継ぎ記録。
現在の設定・実施状況はこの追記を優先する。

- 実機を接続し、PyGPSClient経由のMON-VERで **ZED-F9P / HPG 1.32 / PROTVER 27.31** を確認した。
- アンテナはユーザー申告で **Harxon HX-CSX601A**。
- ユーザーの確定指示で、GPS・GLONASS・Galileo・BeiDou・QZSS・SBASと対応する
  測位用信号帯を有効化し、**5 Hz（200 ms / NAV周期1）、最低使用10衛星、最低仰角30°、
  最低C/N₀ 30 dB-Hz** を設定した。以前の1 Hz方針を置き換える。
- RAMへ適用後、明示的な指示でBBR・Flashにも保存した。全22キーを各層から読み戻し、
  期待値との一致を確認した。BBRにも保存したのは、起動時にFlashより優先されるため。
- 電源の入れ直し・再起動後の保持確認、屋外での測位性能評価は未実施。
- 3Dのみは未確定のまま。FIXMODEは既存の3（Auto 2D/3D）を維持した。
  PDOP・位置精度マスクも変更していない。QZSS L1Sの追加有効化もしていない。
- 読み戻し記録：
  `/home/uedalab/.local/share/pygpsclient/review/receiver_flash_20261110.json`。
  RAMのSBAS L1C/Aは応答値1を取得したがGUI表示が空欄だったため、同キーのみ再取得し、
  応答値・GUI表示とも1と確認した記録が `receiver_flash_ram_recheck_20261110.json` にある。
- `src/ublox_dgnss/ublox_dgnss/launch/gnss_launch_compatible.launch.py` を5 Hzに変更し、
  単独測位用に `RTCM_INPUT_ENABLED=False` を指定した。ROSの補正入力を無効にする指定であり、
  受信機の他ポートの設定を変更するものではない。
- コード監査では、起動時にlaunch等で明示したCFG項目をRAMへ書く構造だった。
  今回のlaunchは周期・USB出力のみを指定し、保存した衛星選別条件を上書きしない。
  F9PのTOMLは対応キーの一覧であり、受信機を既定値へ初期化する設定ではない。
- 今回のlaunch変更後、ROS実機ノードは起動していない。
- 検証：探索範囲を限定した関連6パッケージのビルド成功。
  launchをオフラインで構築して5 Hz・RTCM入力無効・CFG上書き8項目のみであることを確認し、
  `git diff --check` も通過した。起動アクションは実行していない。
- 次に残る作業は、位置・共分散・状態の時刻一致と無効時の出力契約を決めて修正し、
  疑似データで検証すること。その後、明示的な指示で実機ROS出力と保存設定の保持を確認する。

## 最初に読む要約

ユーザーの目的は、受信機内部で最低限の衛星選別を行い、その受信機が計算した
GNSS位置・共分散をROSトピックへ出すこと。利用側は他センサーの状況も踏まえて
GNSSを採用するかその都度判断する。RTK、RAWからの独自測位、ROS側の位置平滑化や
GNSS外れ値除去は今回の対象ではない。

現在、受信機はユーザーの手元にない。受信機への設定書き込み・実機評価は未実施。
ハードウェア起動・受信機操作・ロボットへの運動指令は明示的な指示なしに行わない。
ワークスペースのAGENTS.md指示も参照すること。

## 決定事項と未確定事項

| 項目 | 方針と状態 |
|---|---|
| ドライバ | 現行`ublox_dgnss`を継続。乗り換えない |
| 測位方式 | RTKなしの単独測位 |
| 測位周期 | 1 Hzにすることは決定。ただしlaunchは未変更 |
| 衛星系 | 実機が同時利用できる衛星系を広く使う。型番・FWによる制約を確認する |
| 仰角マスク | 30°以下で、評価しながらできるだけ低くする。最終角度は未確定 |
| 最低使用衛星数 | 10衛星にすることは決定 |
| 最低C/N₀ | 30 dB-Hzが評価開始用の候補。最終確定ではない |
| 測位形式 | 3Dのみが候補。ユーザーの最終確定はまだない |
| PDOP・位置精度マスク | 値は未決定 |
| RAWからの独自測位 | 行わない |
| PyGPSClient | 受信機設定の書き込み・読み戻し確認に使う。通常運用の測位エンジンにはしない |

ユーザーは40°マスクを強すぎると考えている。30°を物理的な限界とは考えていない。
一般論の15°を押し付けたり、40°評価を再提案したりせず、上記方針を引き継ぐこと。
最低10衛星は受信・追尾総数ではなく、測位に使用する衛星数の条件。
その条件を満たさない場面では欠測が増えることを説明済み。

## 処理の役割分担

1. 受信機: 仰角・C/N₀等のマスク、内部の測位処理を行う。
2. ドライバ: 受信機の位置・共分散・有効状態を正しくトピックへ変換する。
   独自の平滑化、他センサーとの融合、RAWからの測位は追加しない。
3. ロボット側: 他センサーの状況やGNSSの鮮度・品質を見て採用可否を決める。

位置・共分散の時刻一致、有効フラグ反映はドライバの整合性処理として改善対象。
無効時の出力契約（配信しない、NO_FIX等）はまだ実装・最終確定していない。
利用側が座標と共分散だけを見るため、NO_FIXだけでは無効値を見落とす可能性を説明済み。
欠測時に古い座標を使い続けない扱いも必要。

## 実施済み作業

### ublox_dgnss

- リポジトリ: `src/ublox_dgnss`
- origin: `git@github.com:shimpeisasaki/ublox_dgnss.git`
- upstream: `git@github.com:aussierobots/ublox_dgnss.git`
- 現在のブランチ: `main`
- 2026-11-10確認時HEAD: `b52cee2`（upstream/mainをマージ）
- 取り込んだ上流コミット: `1cd9ca9`。NAV-SATフラグの予約ビット15の欠落修正。
- 既存の独自GNSS互換launch追加コミット`abd2cab`は保持。
- 取得・マージはローカルのみ。リモートへpushしていない。
- 更新後、関連6パッケージのビルド成功。実機起動はしていない。
- 2026-11-10確認時、作業ツリーはクリーン。

### 比較用ublox_gps

- KumarRobotics/ubloxのros2ブランチ3.0.0を取得・ビルドしてソース比較した。
- 現行継続の判断後、比較用`src/ublox`と対応build/install成果物を削除済み。
- apt版`ros-humble-ublox`、`ros-humble-ublox-gps`、`ros-humble-ublox-msgs`、
  `ros-humble-ublox-serialization`もユーザーが削除し、削除を確認済み。
- `ros2 pkg prefix ublox_gps`はPackage not found。
- 比較の詳細は[GNSS_DRIVER_COMPARISON.md](2026-11-09_gnss-driver-comparison.md)。
  過去の取得・インストール状態についての記録もあるので冒頭の追記を読むこと。

### PyGPSClient

- 導入済み: PyGPSClient 1.8.0、pyubx2 1.4.1。
- 専用venv: `/home/uedalab/.local/share/pygpsclient/venv`
- 起動コマンド: `/home/uedalab/.local/bin/pygpsclient`（通常は`pygpsclient`で起動可能）
- ランチャーはROS等のPYTHONPATH/PYTHONHOMEを除いて起動する。
- デスクトップエントリ: `/home/uedalab/.local/share/applications/pygpsclient.desktop`
- GUI起動と専用環境のpip checkを確認済み。
- 受信機接続・書き込みはしていない。
- RAWログ記録とRINEX変換（ベータ）はあるが、RAWから位置を再計算する機能は見当たらない。

## 現行コードで未対応の箇所

### launchはまだ4 Hz

`src/ublox_dgnss/ublox_dgnss/launch/gnss_launch_compatible.launch.py`

- `CFG_RATE_MEAS: 250`、`CFG_RATE_NAV: 1`。1 Hzなら1000 ms / 1へ変更が必要。
- F9P向けの設定。実機の型番・FWを読み取って確認する必要がある。
- 出力: `/gnss/fix`、`/gnss/fix_velocity`。
- cat_robotのbringupからこのlaunchを利用している。

### NavSatFix変換の確認不足

`src/ublox_dgnss/ublox_nav_sat_fix_hp_node/src/ublox_nav_sat_fix_hp_node.cpp`

- NAV-HPPOSLLHから位置を生成する。
- NAV-COVのNED共分散をENUへ変換し、非対角成分も保持する。
- 直近の状態・共分散を再利用しており、位置とのiTOW一致を確認していない。
- `gps_fix_ok`、位置のinvalidフラグ、`pos_cor_valid`の確認が不足している。
- これらは未修正。ソース比較だけで実機誤動作を検証したわけではない。

### 受信機設定項目

F9P HPG 1.32仕様には以下があるが、現行ドライバの設定マップに登録されていない。

- `CFG_NAVSPG_INFIL_MINELEV`
- `CFG_NAVSPG_INFIL_MINCNO`
- `CFG_NAVSPG_INFIL_MINSVS`
- `CFG_NAVSPG_OUTFIL_PDOP` / `CFG_NAVSPG_OUTFIL_PACC`

ただし受信機にPyGPSClient等で直接設定・保存できるため、これらをROSパラメータに
追加すること自体は必須ではない。起動時にドライバが上書きする項目に注意する。
設定の管理元を受信機保存とドライバ起動設定で食い違わせないこと。

## 受信機出力に関する確認と重要な訂正

- 現行ドライバはNAV-PVT、NAV-COV、NAV-SAT、NAV-SIG、NAV-DOP、RXM-MEASX、
  RXM-RAWX等の受信に対応。必要に応じ出力設定を有効化する。
- 衛星・信号ごとのC/N₀、仰角、方位角、使用フラグ、疑似距離残差を取得できる。
- 平均C/N₀は、上記データから集計する値。位置再計算とは別。
- RXM-MEASXには`mpathIndic`（未測定/低/中/高）が仕様上ある。
  実機で有効な値が出るかは未確認。
- **「そのマルチパス指標を条件に受信機内部で衛星除外する設定がある」とは確認できていない。**
  過去の説明がそう受け取られたため、明示的に訂正済み。再び断定しないこと。
- 仰角マスクは軌道上の衛星方向による選別であり、到来波の方向を測って反射波を遮断する機能ではない。
- 高仰角・強いC/N₀でも反射・回折の影響は残る。共分散が小さいことも実位置の正しさの保証ではない。
- 除外された衛星の内部判断理由をすべて取得できるわけではない。

## PyGPSClient書き込み機能レビュー

詳細: [PYGPSCLIENT_CONFIG_REVIEW.md](2026-11-09_pygpsclient-config-review.md)

設定コマンド生成・RAM/BBR/Flashの層指定は実装されており、今回の候補6項目の
バイト列をオフラインで確認した。一方、以下を疑似応答で再現した。

1. 別コマンドに対するACKでも成功表示になる。
2. GET応答に対象キーがなくても成功表示になり、元の値が残る。
3. SET時にDEFAULT・未選択でも暗黙にRAMを選ぶ。
4. 符号付き整数の上限判定が1大きく、範囲外で例外になる。

書き込み後の自動読み戻し・期待値比較はない。使用時は同じキー・層をGETして
応答を確認する。Flashだけの書き込みは、現在のRAMへ同時適用する指定ではない。
Flash保存後は再起動後のRAMも確認する。アプリコード自体は改変していない。

再現スクリプトと結果:

- `/home/uedalab/.local/share/pygpsclient/review/reproduce_config_review.py`
- `/home/uedalab/.local/share/pygpsclient/review/results.json`

## 次に進める作業

以下は未実施の候補であり、新しい会話で依頼範囲を確認して進める。

1. 1 Hz、最低10衛星、仰角30°以下の方針を仕様・設定ファイルとして整理する。
   最低C/N₀と3Dのみは確定事項に勝手に昇格させない。
2. launchの測位周期を1 Hzへ変更する。
3. 位置・共分散・状態の測位時刻と有効性を扱う出力契約を決め、ドライバを修正する。
4. 受信機なしの疑似データで、正常・無効・古い共分散・時刻不一致を検証する。
5. 受信機入手後、明示的な指示のもとで型番/FW・現在値を取得し、設定を保存・読み戻す。
6. 開けた場所と建物付近で、位置誤差・共分散・使用衛星数・欠測時間を比較し、
   時間帯も変えて仰角/C/N₀を調整する。共分散が小さいのに大きくずれる場合を重視する。

ビルド例（受信機は起動しない）:

```bash
source /opt/ros/humble/setup.bash
colcon build --base-paths src/ublox_dgnss src/rtcm_msgs --symlink-install \
  --packages-up-to ublox_dgnss ublox_nav_sat_fix_hp_node --executor sequential
```

ワークスペース全体を無指定で探索すると`tools/blender_mcp_setup/`内のPythonコードを
colconが誤検出したことがある。探索範囲を限定する。

## 参照資料

- F9P HPG 1.32 Interface Description（実機FWとの対応確認が必要）:
  https://content.u-blox.com/sites/default/files/documents/u-blox-F9-HPG-1.32_InterfaceDescription_UBX-22008968.pdf
- F9P Integration Manual:
  https://content.u-blox.com/sites/default/files/ZED-F9P_IntegrationManual_UBX-18010802.pdf
- PyGPSClient: https://github.com/semuconsulting/PyGPSClient
- ubxtool: https://gpsd.gitlab.io/gpsd/ubxtool.html
- ubxtool examples: https://gpsd.gitlab.io/gpsd/ubxtool-examples.html

u-blox公式GUIのu-centerはWindows向け。F9Pは従来版u-centerの対象。
UbuntuではPyGPSClientやubxtoolから同じUBX設定コマンドを送れる。
ubxtoolの資料には汎用の設定取得・変更例はあるが、今回のマルチパス対策に対する
最適閾値・性能保証のレシピは見つかっていない。
