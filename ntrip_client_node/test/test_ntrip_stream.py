"""Exercise the actual client against loopback only; no receiver or public caster."""

import base64
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time

from ament_index_python.packages import get_package_prefix
import pytest


class LocalCaster:
    def __init__(self, response, stream=False):
        self.socket = socket.socket()
        self.socket.bind(('127.0.0.1', 0))
        self.socket.listen()
        self.socket.settimeout(0.1)
        self.port = self.socket.getsockname()[1]
        self.response = response
        self.stream = stream
        self.requests = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.socket.accept()
            except socket.timeout:
                continue
            with connection:
                connection.settimeout(2)
                request = b''
                try:
                    while b'\r\n\r\n' not in request:
                        chunk = connection.recv(4096)
                        if not chunk:
                            break
                        request += chunk
                    self.requests.append((time.monotonic(), request))
                    connection.sendall(self.response)
                    while self.stream and not self.stop.wait(0.05):
                        connection.sendall(b'\xd3\x00\x03\x00\x00\x00\x00\x00\x00')
                except (OSError, TimeoutError):
                    pass

    def close(self):
        self.stop.set()
        self.thread.join(timeout=3)
        self.socket.close()


def start_client(caster, log_path):
    executable = Path(get_package_prefix('ntrip_client_node')) / 'lib/ntrip_client_node/ntrip_client_node'
    environment = dict(os.environ, NO_PROXY='127.0.0.1', no_proxy='127.0.0.1')
    with log_path.open('w') as log:
        return subprocess.Popen([
            str(executable), '--ros-args', '--log-level', 'debug',
            '-p', 'use_https:=false', '-p', 'host:=127.0.0.1',
            '-p', f'port:={caster.port}', '-p', 'mountpoint:=LOCAL_TEST',
            '-p', 'username:=test-user', '-p', 'password:=dummy-password',
            '-p', 'log_level:=DEBUG',
        ], stdout=log, stderr=subprocess.STDOUT, env=environment)


def stop_client(process):
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        pytest.fail('NTRIP client did not stop promptly')


def wait_until(predicate, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    pytest.fail('Timed out waiting for local client/server activity')


@pytest.mark.parametrize('response', [
    b'HTTP/1.1 200 OK\r\nContent-Type: gnss/data\r\n\r\n',
    b'ICY 200 OK\r\n',
])
def test_healthy_stream_stays_connected(response, tmp_path):
    caster = LocalCaster(response, stream=True)
    log_path = tmp_path / 'client.log'
    process = start_client(caster, log_path)
    try:
        wait_until(lambda: log_path.read_text().count('Received size:') >= 40, 10)
        assert len(caster.requests) == 1
        assert process.poll() is None
        authorization = base64.b64encode(b'test-user:dummy-password')
        assert b'Authorization: Basic ' + authorization in caster.requests[0][1]
        log = log_path.read_text()
        assert 'dummy-password' not in log
        assert authorization.decode() not in log
    finally:
        stop_client(process)
        caster.close()


def test_auth_failure_waits_before_reconnect(tmp_path):
    caster = LocalCaster(b'HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\n\r\n')
    process = start_client(caster, tmp_path / 'client.log')
    try:
        wait_until(lambda: len(caster.requests) >= 2, 36)
        assert caster.requests[1][0] - caster.requests[0][0] >= 29.5
        time.sleep(1)
        assert len(caster.requests) == 2
    finally:
        stop_client(process)
        caster.close()


def test_clean_remote_close_also_backs_off(tmp_path):
    caster = LocalCaster(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n')
    log_path = tmp_path / 'client.log'
    process = start_client(caster, log_path)
    try:
        wait_until(lambda: 'retrying in 30 seconds' in log_path.read_text(), 5)
        time.sleep(2)
        assert len(caster.requests) == 1
    finally:
        stop_client(process)
        caster.close()
