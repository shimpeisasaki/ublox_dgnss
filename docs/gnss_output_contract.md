# GNSS出力契約

対象：`ublox_nav_sat_fix_hp_node`。2026-11-10に合意した「無効な位置は配信しない」方針。
測位の再計算・平滑化・他センサーとの融合や、位置の統計的な外れ値除去は行わない。

## 位置：`fix`（互換launchでは `/gnss/fix`）

NAV-HPPOSLLH、NAV-COV、NAV-STATUSの **GPS iTOWが完全一致**した組だけを使用する。
到着順序は問わず、必要なメッセージが揃った時点で1回だけ配信する。

- NAV-STATUSの `gps_fix_ok` がtrueで、fix typeが2D・3D・GNSSと推測航法の複合であること。
  未受信・No Fix・推測航法のみ・時刻のみ・未知のfix typeでは配信しない。
  3Dのみに制限する変更はしていない。
- 出力に使う緯度・経度・楕円体高と、それぞれの高精度成分のinvalidフラグがfalseであること。
  緯度・経度が物理的な範囲内であること。出力しないMSL高度のinvalidフラグは判定対象にしない。
- 同じiTOWの `pos_cor_valid` がtrueであること。
  共分散は有限値・非負の対角成分・半正定値（float丸め誤差の許容あり）を要求する。
  誤差の大きさによる閾値選別は追加していない。
- 共分散はNEDからENUへ変換し、非対角成分も保持する。
- `header` はNAV-HPPOSLLHのものをそのまま使用する。緯度・経度・楕円体高も受信機の値を単位変換する。

**不成立時には何も配信しない。** 無効値を載せたNO_FIXメッセージや、最後の有効位置の再配信はしない。
利用側が受信の途絶・古さを検出して採用を止める。受信機の共分散や有効フラグが正常でも、
マルチパスによる実位置の誤りがないことを保証するものではない。

NAV-STATUSだけでは、使用した全衛星系や補正の種類を特定できないため、
`NavSatStatus.service` は0（未特定）、`status` は有効な測位を表すSTATUS_FIXとする。
これらの値から単独測位・SBAS・RTK Float・RTK Fixを区別しない。
RTK状態は元の `/ubx_nav_status` のキャリア解・有効フラグで確認する。

## 速度：`fix_velocity`（互換launchでは `/gnss/fix_velocity`）

NAV-VELNED、NAV-COV、NAV-STATUSのiTOWを一致させ、位置と同じ状態・鮮度条件を要求する。
さらに `vel_cor_valid` と速度共分散の妥当性を確認する。
速度と共分散をNEDからENUへ変換し、並進3×3の非対角成分も保持する。
以前の `s_acc` から等方分散を作る処理は使用しない。
headerはNAV-VELNEDからコピーし、角速度の不明表現（共分散index 21が-1）は既存互換として維持する。

位置と速度はそれぞれ独立に成立を判定する。例えば位置フラグが無効でも、
状態・速度・速度共分散が有効なら速度のみ配信できる。

## 待ち合わせ・鮮度

- 起動時パラメータ `sync_timeout_sec` は既定1.0秒。有限の正値を指定する。
- 最初のメッセージの受信からタイムアウトするまで、同一iTOWの組を保持する。
  受信時間の計測には単調時計を使い、最大32エポックまで保持する。
- 各入力headerはゼロ・不正・未来の時刻を拒否し、現在のROS時刻からタイムアウト以内であることを要求する。
  配信直前にも確認する。ROS時刻と入力headerは同じ時刻基準が必要。
- 同一エポック・同一種類の重複入力は最初の値を保持する。
  既に配信したエポックとそれより古いエポックは再配信しない。
  GPS週境界のiTOW折り返しは正常な進行として扱う。
- 出力headerを現在時刻に付け替えない。これは入力headerの保持であり、
  GPS絶対時刻からROS時刻を新たに構成する変更ではない。

## オフライン検証

`test/test_epoch_output.py` は変換ノードだけを起動し、隔離したROSドメイン214・localhostで
疑似UBXトピックを送る。USB受信機ドライバ・NTRIPクライアント・ロボットは起動しない。

検証対象：位置3種類の全到着順、速度の先行到着、座標・単位・ENU共分散変換、
無効フラグとfix type、共分散の無効値、時刻不一致、入力欠落、古いheader、
待ち合わせ期限切れと復帰、重複・逆順・途絶時の非再配信、GPS週境界、不正時刻・座標。

```bash
source /opt/ros/humble/setup.bash
colcon build --base-paths src/ublox_dgnss src/rtcm_msgs --symlink-install \
  --packages-up-to ublox_dgnss --executor sequential
source install/setup.bash
colcon test --base-paths src/ublox_dgnss src/rtcm_msgs \
  --packages-select ublox_nav_sat_fix_hp_node \
  --ctest-args -R '^epoch_output$' --return-code-on-test-failure
colcon test-result --test-result-base build/ublox_nav_sat_fix_hp_node --verbose
```

実機の正常出力率、通信断、RTK Float/Fix、位置誤差の検証は別途必要。
