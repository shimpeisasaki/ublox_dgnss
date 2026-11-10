"""Launch a ZED-F9P at 5 Hz; RTCM correction input is opt-in."""

import launch
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
  """Generate launch description for a ZED-F9P rover."""

  device_serial_string = LaunchConfiguration('device_serial_string')
  frame_id = LaunchConfiguration('frame_id')

  log_level_arg = DeclareLaunchArgument(
    'log_level', default_value=TextSubstitution(text='INFO'))
  device_serial_string_arg = DeclareLaunchArgument(
    'device_serial_string',
    default_value='',
    description='USB serial string of the receiver')
  frame_id_arg = DeclareLaunchArgument(
    'frame_id',
    default_value='gps',
    description='Frame ID used by the published GNSS messages')
  rtcm_input_arg = DeclareLaunchArgument(
    'rtcm_input_enabled', default_value='false', choices=['true', 'false'],
    description='Enable ROS RTCM forwarding and RTCM3 input on receiver USB')
  rtcm_input = ParameterValue(LaunchConfiguration('rtcm_input_enabled'), value_type=bool)

  receiver_parameters = [
    {'DEVICE_FAMILY': 'F9P'},
    {'DEVICE_SERIAL_STRING': device_serial_string},
    {'FRAME_ID': frame_id},
    {'RTCM_INPUT_ENABLED': rtcm_input},
    # Satellite selection and quality masks are managed in receiver BBR/Flash.
    # Only the rate and USB protocol/output settings are overridden in RAM.
    {'CFG_USBINPROT_RTCM3X': rtcm_input},
    {'CFG_USBOUTPROT_NMEA': False},
    {'CFG_RATE_MEAS': 200},
    {'CFG_RATE_NAV': 1},
    {'CFG_MSGOUT_UBX_NAV_HPPOSLLH_USB': 1},
    {'CFG_MSGOUT_UBX_NAV_STATUS_USB': 1},
    {'CFG_MSGOUT_UBX_NAV_COV_USB': 1},
    {'CFG_MSGOUT_UBX_NAV_VELNED_USB': 1},
    {'CFG_MSGOUT_UBX_RXM_RTCM_USB': 1},
  ]

  receiver_container = ComposableNodeContainer(
    name='ublox_dgnss_container',
    namespace='',
    package='rclcpp_components',
    executable='component_container_mt',
    arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
    composable_node_descriptions=[
      ComposableNode(
        package='ublox_dgnss_node',
        plugin='ublox_dgnss::UbloxDGNSSNode',
        name='ublox_dgnss',
        parameters=receiver_parameters),
    ])

  output_container = ComposableNodeContainer(
    name='ublox_gnss_output_container',
    namespace='',
    package='rclcpp_components',
    executable='component_container_mt',
    arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
    composable_node_descriptions=[
      ComposableNode(
        package='ublox_nav_sat_fix_hp_node',
        plugin='ublox_nav_sat_fix_hp::UbloxNavSatHpFixNode',
        name='ublox_gnss_output',
        remappings=[
          ('fix', '/gnss/fix'),
          ('fix_velocity', '/gnss/fix_velocity'),
        ]),
    ])

  return launch.LaunchDescription([
    log_level_arg,
    device_serial_string_arg,
    frame_id_arg,
    rtcm_input_arg,
    receiver_container,
    output_container,
  ])
