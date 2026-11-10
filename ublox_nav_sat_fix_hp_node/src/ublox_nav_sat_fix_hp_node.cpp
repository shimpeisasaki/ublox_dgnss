// Copyright 2023 CMP Engineers Pty Ltd
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <map>
#include <optional>
#include <stdexcept>

#include "geometry_msgs/msg/twist_with_covariance_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_components/register_node_macro.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "sensor_msgs/msg/nav_sat_status.hpp"
#include "ublox_nav_sat_fix_hp_node/visibility_control.h"
#include "ublox_ubx_msgs/msg/gps_fix.hpp"
#include "ublox_ubx_msgs/msg/ubx_nav_cov.hpp"
#include "ublox_ubx_msgs/msg/ubx_nav_hp_pos_llh.hpp"
#include "ublox_ubx_msgs/msg/ubx_nav_status.hpp"
#include "ublox_ubx_msgs/msg/ubx_nav_vel_ned.hpp"

namespace ublox_nav_sat_fix_hp
{

class UbloxNavSatHpFixNode : public rclcpp::Node
{
  using Position = ublox_ubx_msgs::msg::UBXNavHPPosLLH;
  using Covariance = ublox_ubx_msgs::msg::UBXNavCov;
  using Status = ublox_ubx_msgs::msg::UBXNavStatus;
  using Velocity = ublox_ubx_msgs::msg::UBXNavVelNED;
  using SteadyClock = std::chrono::steady_clock;
  static constexpr uint32_t WEEK_MS = 604800000;
  static constexpr size_t MAX_PENDING_EPOCHS = 32;

  struct Epoch
  {
    SteadyClock::time_point first_received;
    std::optional<Position> position;
    std::optional<Covariance> covariance;
    std::optional<Status> status;
    std::optional<Velocity> velocity;
  };

public:
  UBLOX_NAV_SAT_FIX_HP_NODE_PUBLIC
  explicit UbloxNavSatHpFixNode(const rclcpp::NodeOptions & options)
  : Node("ublox_nav_sat_fix_hp",
      rclcpp::NodeOptions(options).automatically_declare_parameters_from_overrides(true))
  {
    if (!has_parameter("sync_timeout_sec")) {
      declare_parameter("sync_timeout_sec", 1.0);
    }
    sync_timeout_sec_ = get_parameter("sync_timeout_sec").as_double();
    if (!std::isfinite(sync_timeout_sec_) || sync_timeout_sec_ <= 0.0) {
      throw std::invalid_argument("sync_timeout_sec must be finite and positive");
    }

    auto qos = rclcpp::SensorDataQoS();
    rclcpp::PublisherOptions pub_options;
    pub_options.qos_overriding_options = rclcpp::QosOverridingOptions::with_default_policies();
    fix_pub_ = create_publisher<sensor_msgs::msg::NavSatFix>("fix", qos, pub_options);
    velocity_pub_ = create_publisher<geometry_msgs::msg::TwistWithCovarianceStamped>(
      "fix_velocity", qos, pub_options);

    // Default mutually exclusive callback group serializes cache access, including expiry.
    position_sub_ = create_subscription<Position>("ubx_nav_hp_pos_llh", qos,
        [this](Position::ConstSharedPtr msg) {receive(*msg, &Epoch::position);});
    covariance_sub_ = create_subscription<Covariance>("ubx_nav_cov", qos,
        [this](Covariance::ConstSharedPtr msg) {receive(*msg, &Epoch::covariance);});
    status_sub_ = create_subscription<Status>("ubx_nav_status", qos,
        [this](Status::ConstSharedPtr msg) {receive(*msg, &Epoch::status);});
    velocity_sub_ = create_subscription<Velocity>("ubx_nav_vel_ned", qos,
        [this](Velocity::ConstSharedPtr msg) {receive(*msg, &Epoch::velocity);});
    expiry_timer_ = create_wall_timer(std::chrono::milliseconds(100),
        [this]() {expire(SteadyClock::now());});
  }

private:
  double sync_timeout_sec_;
  std::map<uint32_t, Epoch> epochs_;
  std::optional<uint32_t> last_fix_epoch_;
  std::optional<uint32_t> last_velocity_epoch_;
  rclcpp::Publisher<sensor_msgs::msg::NavSatFix>::SharedPtr fix_pub_;
  rclcpp::Publisher<geometry_msgs::msg::TwistWithCovarianceStamped>::SharedPtr velocity_pub_;
  rclcpp::Subscription<Position>::SharedPtr position_sub_;
  rclcpp::Subscription<Covariance>::SharedPtr covariance_sub_;
  rclcpp::Subscription<Status>::SharedPtr status_sub_;
  rclcpp::Subscription<Velocity>::SharedPtr velocity_sub_;
  rclcpp::TimerBase::SharedPtr expiry_timer_;

  void expire(SteadyClock::time_point now)
  {
    for (auto it = epochs_.begin(); it != epochs_.end(); ) {
      if (std::chrono::duration<double>(now - it->second.first_received).count() >
        sync_timeout_sec_)
      {
        it = epochs_.erase(it);
      } else {
        ++it;
      }
    }
  }

  bool fresh(const std_msgs::msg::Header & header)
  {
    if (header.stamp.sec < 0 || header.stamp.nanosec >= 1000000000u) {
      return false;
    }
    const auto stamp = rclcpp::Time(header.stamp, get_clock()->get_clock_type());
    const auto age = (now() - stamp).seconds();
    return stamp.nanoseconds() > 0 && age >= 0.0 && age <= sync_timeout_sec_;
  }

  static bool newer(uint32_t epoch, const std::optional<uint32_t> & previous)
  {
    if (!previous) {
      return true;
    }
    // GPS iTOW wraps at the end of a week. Equality also suppresses duplicates.
    const uint32_t delta = (epoch + WEEK_MS - *previous) % WEEK_MS;
    return delta > 0 && delta < WEEK_MS / 2;
  }

  template<typename Message>
  void receive(const Message & msg, std::optional<Message> Epoch::* field)
  {
    const auto received = SteadyClock::now();
    expire(received);
    if (msg.itow >= WEEK_MS || !fresh(msg.header)) {
      return;
    }
    auto found = epochs_.find(msg.itow);
    if (found == epochs_.end()) {
      if (epochs_.size() >= MAX_PENDING_EPOCHS) {
        auto oldest = std::min_element(epochs_.begin(), epochs_.end(),
            [](const auto & a, const auto & b) {
              return a.second.first_received < b.second.first_received;
            });
        epochs_.erase(oldest);
      }
      found = epochs_.try_emplace(msg.itow).first;
      found->second.first_received = received;
    }
    // Each UBX message occurs once per epoch; do not let a duplicate change its validity.
    auto & slot = found->second.*field;
    if (!slot) {
      slot = msg;
    }
    publish_ready(msg.itow, found->second);
  }

  static bool valid_status(const Status & status)
  {
    using Fix = ublox_ubx_msgs::msg::GpsFix;
    const auto type = status.gps_fix.fix_type;
    return status.gps_fix_ok && (type == Fix::GPS_FIX_2D || type == Fix::GPS_FIX_3D ||
           type == Fix::GPS_PLUS_DEAD_RECKONING);
  }

  static bool valid_position(const Position & position)
  {
    // Only ellipsoidal height is published; invalid MSL height does not invalidate it.
    const double lat = position.lat * 1e-7 + position.lat_hp * 1e-9;
    const double lon = position.lon * 1e-7 + position.lon_hp * 1e-9;
    return !position.invalid_lat && !position.invalid_lon && !position.invalid_height &&
           !position.invalid_lat_hp && !position.invalid_lon_hp && !position.invalid_height_hp &&
           std::abs(lat) <= 90.0 && std::abs(lon) <= 180.0;
  }

  static std::array<double, 9> to_enu(
    double nn, double ne, double nd, double ee, double ed, double dd)
  {
    return {ee, ne, -ed, ne, nn, -nd, -ed, -nd, dd};
  }

  static bool valid_covariance(const std::array<double, 9> & matrix)
  {
    double scale = 0.0;
    for (double value : matrix) {
      if (!std::isfinite(value)) {
        return false;
      }
      scale = std::max(scale, std::abs(value));
    }
    const double a = matrix[0], d = matrix[4], f = matrix[8];
    if (a < 0.0 || d < 0.0 || f < 0.0) {
      return false;
    }
    if (scale == 0.0) {
      return true;
    }
    // All principal minors must be nonnegative (allow float roundoff after scaling).
    const double x = a / scale, y = d / scale, z = f / scale;
    const double b = matrix[1] / scale, c = matrix[2] / scale, e = matrix[5] / scale;
    constexpr double tolerance = 1e-6;
    return x * y - b * b >= -tolerance && x * z - c * c >= -tolerance &&
           y * z - e * e >= -tolerance &&
           x * y * z + 2 * b * c * e - x * e * e - y * c * c - z * b * b >= -tolerance;
  }

  void publish_ready(uint32_t itow, const Epoch & epoch)
  {
    if (!epoch.status || !epoch.covariance || !valid_status(*epoch.status) ||
      !fresh(epoch.status->header) || !fresh(epoch.covariance->header))
    {
      return;
    }
    const auto & cov = *epoch.covariance;
    if (epoch.position && newer(itow, last_fix_epoch_) && cov.pos_cor_valid &&
      fresh(epoch.position->header) && valid_position(*epoch.position))
    {
      const auto matrix = to_enu(cov.pos_cov_nn, cov.pos_cov_ne, cov.pos_cov_nd,
          cov.pos_cov_ee, cov.pos_cov_ed, cov.pos_cov_dd);
      if (valid_covariance(matrix)) {
        sensor_msgs::msg::NavSatFix fix;
        const auto & position = *epoch.position;
        fix.header = position.header;
        fix.latitude = position.lat * 1e-7 + position.lat_hp * 1e-9;
        fix.longitude = position.lon * 1e-7 + position.lon_hp * 1e-9;
        fix.altitude = position.height * 1e-3 + position.height_hp * 1e-4;
        // NAV-STATUS cannot identify all used constellations or the correction source.
        fix.status.service = 0;
        fix.status.status = sensor_msgs::msg::NavSatStatus::STATUS_FIX;
        fix.position_covariance = matrix;
        fix.position_covariance_type = sensor_msgs::msg::NavSatFix::COVARIANCE_TYPE_KNOWN;
        fix_pub_->publish(fix);
        last_fix_epoch_ = itow;
      }
    }
    if (epoch.velocity && newer(itow, last_velocity_epoch_) && cov.vel_cor_valid &&
      fresh(epoch.velocity->header))
    {
      const auto matrix = to_enu(cov.vel_cov_nn, cov.vel_cov_ne, cov.vel_cov_nd,
          cov.vel_cov_ee, cov.vel_cov_ed, cov.vel_cov_dd);
      if (valid_covariance(matrix)) {
        geometry_msgs::msg::TwistWithCovarianceStamped velocity;
        velocity.header = epoch.velocity->header;
        velocity.twist.twist.linear.x = epoch.velocity->vel_e * 1e-2;
        velocity.twist.twist.linear.y = epoch.velocity->vel_n * 1e-2;
        velocity.twist.twist.linear.z = -epoch.velocity->vel_d * 1e-2;
        for (size_t row = 0; row < 3; ++row) {
          for (size_t col = 0; col < 3; ++col) {
            velocity.twist.covariance[row * 6 + col] = matrix[row * 3 + col];
          }
        }
        velocity.twist.covariance[21] = -1.0;  // Preserve existing angular-unknown convention.
        velocity_pub_->publish(velocity);
        last_velocity_epoch_ = itow;
      }
    }
  }
};

}  // namespace ublox_nav_sat_fix_hp

RCLCPP_COMPONENTS_REGISTER_NODE(ublox_nav_sat_fix_hp::UbloxNavSatHpFixNode)
