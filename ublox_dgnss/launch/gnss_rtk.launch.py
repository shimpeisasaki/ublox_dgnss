"""Opt-in RTK with CIT by default; credentials stay outside the repository."""

import json
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def launch_rtk(context):
    launch_dir = PathJoinSubstitution([FindPackageShare('ublox_dgnss'), 'launch'])
    source = LaunchConfiguration('rtk_source').perform(context)
    profiles = {
        'cit': {'host': 'taroz.net', 'port': '2101', 'mountpoint': 'CIT'},
        'matsudo': {'host': 'geortk.jp', 'port': '2101', 'mountpoint': 'Matsudo'},
        'custom': {'host': '', 'port': '2101', 'mountpoint': ''},
    }
    caster_arguments = dict(profiles[source], use_https='false')
    for name in ('host', 'port', 'mountpoint', 'use_https'):
        override = LaunchConfiguration(name).perform(context)
        if override:
            caster_arguments[name] = override
    credentials = {name: LaunchConfiguration(name).perform(context)
                   for name in ('username', 'password')}
    if source == 'cit' and not all(credentials.values()):
        path = Path(LaunchConfiguration('credentials_file').perform(context)).expanduser()
        try:
            saved = json.loads(path.read_text())
            if not isinstance(saved, dict):
                raise ValueError('expected a JSON object')
            for name in credentials:
                if not credentials[name]:
                    credentials[name] = saved.get(name, '')
        except (OSError, ValueError):
            raise RuntimeError(
                f'CIT credentials could not be loaded from {path}; '
                'provide a local JSON file with username/password or NTRIP environment variables'
            ) from None
        if not all(isinstance(value, str) and value for value in credentials.values()):
            raise RuntimeError('CIT credentials require nonempty username and password strings')
    if not caster_arguments['host'] or not caster_arguments['mountpoint']:
        raise RuntimeError('Custom NTRIP source requires host and mountpoint')
    caster_arguments.update(credentials)
    caster_arguments.update({name: LaunchConfiguration(name)
                             for name in ('log_level', 'maxage_conn')})
    receiver_arguments = {
        name: LaunchConfiguration(name)
        for name in ('device_serial_string', 'frame_id', 'log_level')
    }
    receiver_arguments['rtcm_input_enabled'] = 'true'
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([launch_dir, 'gnss_launch_compatible.launch.py'])),
            launch_arguments=receiver_arguments.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([launch_dir, 'ntrip_client.launch.py'])),
            launch_arguments=caster_arguments.items()),
    ]


def generate_launch_description():
    defaults = {
        'device_serial_string': '',
        'frame_id': 'gps',
        'log_level': 'INFO',
        'credentials_file': str(Path.home() / '.config/ublox_dgnss/ntrip_cit.json'),
        'host': '',
        'port': '',
        'mountpoint': '',
        'use_https': '',
        'username': EnvironmentVariable('NTRIP_USERNAME', default_value=''),
        'password': EnvironmentVariable('NTRIP_PASSWORD', default_value=''),
        'maxage_conn': '30',
    }
    arguments = [DeclareLaunchArgument(name, default_value=value)
                 for name, value in defaults.items()]
    return LaunchDescription([
        DeclareLaunchArgument('rtk_source', default_value='cit',
                              choices=['cit', 'matsudo', 'custom']),
        *arguments,
        OpaqueFunction(function=launch_rtk),
    ])
