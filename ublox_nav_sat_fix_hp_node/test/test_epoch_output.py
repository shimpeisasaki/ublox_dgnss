"""Publish synthetic UBX topics to the conversion node; never start a receiver driver."""

from copy import deepcopy
import itertools
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from ament_index_python.packages import get_package_prefix
from geometry_msgs.msg import TwistWithCovarianceStamped
import pytest
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import NavSatFix
from ublox_ubx_msgs.msg import UBXNavCov, UBXNavHPPosLLH, UBXNavStatus, UBXNavVelNED

WEEK_MS = 604800000
TIMEOUT = 0.6


@pytest.fixture(scope='module', autouse=True)
def ros_context():
    assert os.environ['ROS_LOCALHOST_ONLY'] == '1'
    assert os.environ['ROS_DOMAIN_ID'] == '214'
    rclpy.init()
    yield
    rclpy.shutdown()


class Peer:
    def __init__(self, node):
        self.node = node
        self.fixes = []
        self.velocities = []
        types = {'position': UBXNavHPPosLLH, 'covariance': UBXNavCov,
                 'status': UBXNavStatus, 'velocity': UBXNavVelNED}
        topics = {'position': 'ubx_nav_hp_pos_llh', 'covariance': 'ubx_nav_cov',
                  'status': 'ubx_nav_status', 'velocity': 'ubx_nav_vel_ned'}
        self.publishers = {key: node.create_publisher(kind, topics[key], 10)
                           for key, kind in types.items()}
        self.subscriptions = [
            node.create_subscription(NavSatFix, 'fix', self.fixes.append, qos_profile_sensor_data),
            node.create_subscription(TwistWithCovarianceStamped, 'fix_velocity',
                                     self.velocities.append, qos_profile_sensor_data)]

    def spin(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.01)

    def bundle(self, epoch=1000):
        position = UBXNavHPPosLLH(itow=epoch, lat=355000000, lon=1400000000,
                                 lat_hp=7, lon_hp=-8, height=123450, height_hp=4)
        covariance = UBXNavCov(itow=epoch, pos_cor_valid=True, vel_cor_valid=True,
                              pos_cov_nn=4.0, pos_cov_ne=0.5, pos_cov_nd=0.25,
                              pos_cov_ee=9.0, pos_cov_ed=-0.75, pos_cov_dd=16.0,
                              vel_cov_nn=0.04, vel_cov_ne=0.005, vel_cov_nd=0.0025,
                              vel_cov_ee=0.09, vel_cov_ed=-0.0075, vel_cov_dd=0.16)
        status = UBXNavStatus(itow=epoch, gps_fix_ok=True, tow_set=True, wkn_set=True)
        status.gps_fix.fix_type = 3
        velocity = UBXNavVelNED(itow=epoch, vel_n=123, vel_e=-234, vel_d=56, s_acc=9999)
        messages = dict(position=position, covariance=covariance, status=status, velocity=velocity)
        for msg in messages.values():
            msg.header.stamp = self.node.get_clock().now().to_msg()
            msg.header.frame_id = 'gnss_antenna_link'
        return messages

    def send(self, name, msg):
        self.publishers[name].publish(msg)
        self.spin(0.025)

    def send_all(self, messages, order=('position', 'covariance', 'status', 'velocity')):
        for name in order:
            self.send(name, messages[name])
        self.spin(0.05)


@pytest.fixture
def peer(tmp_path):
    namespace = '/gnss_epoch_' + uuid.uuid4().hex
    node = rclpy.create_node('synthetic_ubx', namespace=namespace)
    fixture = Peer(node)
    executable = Path(get_package_prefix('ublox_nav_sat_fix_hp_node')) / (
        'lib/ublox_nav_sat_fix_hp_node/ublox_nav_sat_fix_hp')
    with (tmp_path / 'converter.log').open('w') as log:
        process = subprocess.Popen([
            str(executable), '--ros-args', '-r', '__ns:=' + namespace,
            '-p', 'sync_timeout_sec:=' + str(TIMEOUT),
        ], stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            fixture.spin(0.02)
            assert process.poll() is None, (tmp_path / 'converter.log').read_text()
            if (all(pub.get_subscription_count() for pub in fixture.publishers.values()) and
                    node.count_publishers('fix') and node.count_publishers('fix_velocity')):
                break
        else:
            pytest.fail('Synthetic topics did not discover the conversion node')
        # DDS graph discovery may precede best-effort output matching. Establish
        # actual bidirectional data flow before making any output-count assertions.
        deadline = time.monotonic() + 3
        epoch = WEEK_MS - 10000
        while time.monotonic() < deadline:
            fixture.send_all(fixture.bundle(epoch))
            if fixture.fixes and fixture.velocities:
                break
            epoch += 200
        else:
            pytest.fail('Synthetic input/output data flow did not become ready')
        fixture.spin(0.1)
        fixture.fixes.clear()
        fixture.velocities.clear()
        yield fixture
        assert process.poll() is None, (tmp_path / 'converter.log').read_text()
    finally:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        node.destroy_node()


@pytest.mark.parametrize('order', list(itertools.permutations(('position', 'covariance', 'status'))))
def test_normal_output_and_arrival_order(peer, order):
    messages = peer.bundle()
    peer.send_all(messages, ('velocity',) + order)
    assert len(peer.fixes) == len(peer.velocities) == 1
    fix = peer.fixes[0]
    assert fix.header == messages['position'].header
    assert fix.latitude == pytest.approx(35.500000007, abs=1e-10)
    assert fix.longitude == pytest.approx(139.999999992, abs=1e-10)
    assert fix.altitude == pytest.approx(123.4504)
    assert list(fix.position_covariance) == pytest.approx(
        [9, 0.5, 0.75, 0.5, 4, -0.25, 0.75, -0.25, 16])
    assert fix.position_covariance_type == NavSatFix.COVARIANCE_TYPE_KNOWN
    assert fix.status.status == 0 and fix.status.service == 0
    velocity = peer.velocities[0]
    assert velocity.header == messages['velocity'].header
    assert velocity.twist.twist.linear.x == pytest.approx(-2.34)
    assert velocity.twist.twist.linear.y == pytest.approx(1.23)
    assert velocity.twist.twist.linear.z == pytest.approx(-0.56)
    indices = [0, 1, 2, 6, 7, 8, 12, 13, 14]
    assert [velocity.twist.covariance[i] for i in indices] == pytest.approx(
        [0.09, 0.005, 0.0075, 0.005, 0.04, -0.0025, 0.0075, -0.0025, 0.16])


@pytest.mark.parametrize('fix_type,ok', [(3, False), (0, True), (1, True), (5, True), (255, True)])
def test_invalid_status_suppresses_both_outputs(peer, fix_type, ok):
    messages = peer.bundle()
    messages['status'].gps_fix.fix_type = fix_type
    messages['status'].gps_fix_ok = ok
    peer.send_all(messages)
    assert peer.fixes == [] and peer.velocities == []


@pytest.mark.parametrize('flag', [
    'invalid_lat', 'invalid_lon', 'invalid_height',
    'invalid_lat_hp', 'invalid_lon_hp', 'invalid_height_hp'])
def test_invalid_position_flags(peer, flag):
    messages = peer.bundle()
    setattr(messages['position'], flag, True)
    peer.send_all(messages)
    assert peer.fixes == []
    assert len(peer.velocities) == 1  # Velocity has its own validity contract.


def test_invalid_msl_does_not_invalidate_ellipsoidal_height_or_2d(peer):
    messages = peer.bundle()
    messages['position'].invalid_hmsl = True
    messages['position'].invalid_hmsl_hp = True
    messages['status'].gps_fix.fix_type = 2
    peer.send_all(messages)
    assert len(peer.fixes) == 1


@pytest.mark.parametrize('field,value', [
    ('pos_cor_valid', False), ('pos_cov_nn', -1.0), ('pos_cov_ne', 100.0),
    ('pos_cov_ee', float('nan')), ('pos_cov_dd', float('inf'))])
def test_invalid_position_covariance(peer, field, value):
    messages = peer.bundle()
    setattr(messages['covariance'], field, value)
    peer.send_all(messages)
    assert peer.fixes == [] and len(peer.velocities) == 1


@pytest.mark.parametrize('field,value', [
    ('vel_cor_valid', False), ('vel_cov_nn', -1.0), ('vel_cov_ne', 100.0),
    ('vel_cov_ee', float('nan'))])
def test_invalid_velocity_covariance(peer, field, value):
    messages = peer.bundle()
    setattr(messages['covariance'], field, value)
    peer.send_all(messages)
    assert len(peer.fixes) == 1 and peer.velocities == []


def test_epoch_mismatch_and_late_matching_covariance(peer):
    messages = peer.bundle()
    old_covariance = deepcopy(messages['covariance'])
    old_covariance.itow = 800
    peer.send('covariance', old_covariance)
    peer.send_all(messages, ('position', 'status', 'velocity'))
    assert peer.fixes == [] and peer.velocities == []
    peer.send('covariance', messages['covariance'])
    assert len(peer.fixes) == len(peer.velocities) == 1


@pytest.mark.parametrize('missing', ['position', 'status', 'covariance'])
def test_missing_input_does_not_publish_position(peer, missing):
    messages = peer.bundle()
    peer.send_all(messages, tuple(name for name in messages if name != missing))
    assert peer.fixes == []
    if missing != 'position':
        assert peer.velocities == []


@pytest.mark.parametrize('part', ['position', 'covariance', 'status', 'velocity'])
def test_stale_source_stamp(peer, part):
    messages = peer.bundle()
    messages[part].header.stamp.sec -= 2
    peer.send_all(messages)
    if part == 'velocity':
        assert len(peer.fixes) == 1 and peer.velocities == []
    elif part == 'position':
        assert peer.fixes == [] and len(peer.velocities) == 1
    else:
        assert peer.fixes == [] and peer.velocities == []


def test_expired_partial_epoch_is_not_completed_with_old_position(peer):
    old = peer.bundle()
    peer.send('position', old['position'])
    peer.spin(TIMEOUT + 0.15)
    messages = peer.bundle()
    peer.send_all(messages, ('status', 'covariance'))
    assert peer.fixes == []
    peer.send('position', messages['position'])
    assert len(peer.fixes) == 1


def test_duplicates_older_epochs_and_outage_do_not_republish(peer):
    messages = peer.bundle(2000)
    peer.send_all(messages)
    peer.send_all(messages)
    peer.send_all(peer.bundle(1800))
    assert len(peer.fixes) == len(peer.velocities) == 1
    peer.spin(TIMEOUT + 0.15)
    assert len(peer.fixes) == len(peer.velocities) == 1
    peer.send_all(peer.bundle(2000))
    assert len(peer.fixes) == len(peer.velocities) == 1
    peer.send_all(peer.bundle(2200))
    assert len(peer.fixes) == len(peer.velocities) == 2


def test_week_rollover(peer):
    peer.send_all(peer.bundle(WEEK_MS - 200))
    peer.send_all(peer.bundle(0))
    assert len(peer.fixes) == len(peer.velocities) == 2


@pytest.mark.parametrize('sec,nanosec', [(0, 0), (-1, 0), (1, 1000000000)])
def test_invalid_stamp_does_not_crash_or_publish(peer, sec, nanosec):
    messages = peer.bundle()
    messages['position'].header.stamp.sec = sec
    messages['position'].header.stamp.nanosec = nanosec
    peer.send_all(messages)
    assert peer.fixes == []


def test_out_of_range_coordinates_and_epoch(peer):
    messages = peer.bundle()
    messages['position'].lat = 910000000
    peer.send_all(messages)
    assert peer.fixes == []
    peer.send_all(peer.bundle(WEEK_MS))
    assert peer.fixes == []
