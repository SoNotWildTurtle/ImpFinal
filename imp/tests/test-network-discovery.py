from pathlib import Path
import importlib.util
import json
import time



ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'security' / 'imp-network-discovery.py'

spec = importlib.util.spec_from_file_location('network_discovery', MODULE_PATH)
network_discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(network_discovery)

print('Testing Network Discovery...')


def _fake_probe(ip, ports, timeout):
    if ip.endswith('1'):
        return True, ports[0], 12.5
    return False, None, None


temp_log = ROOT / 'logs' / 'imp-network-discovery-test.json'
temp_config = ROOT / 'config' / 'imp-network-discovery-test.json'
temp_baseline = ROOT / 'logs' / 'imp-network-baseline-test.json'
temp_diff = ROOT / 'logs' / 'imp-network-diff-test.json'
temp_node_status = ROOT / 'logs' / 'imp-node-status-test.json'
temp_health = ROOT / 'logs' / 'imp-node-health-test.json'

if temp_log.exists():
    temp_log.unlink()
temp_baseline.unlink(missing_ok=True)
temp_diff.unlink(missing_ok=True)
temp_node_status.unlink(missing_ok=True)
temp_health.unlink(missing_ok=True)

temp_config.write_text(
    json.dumps(
        {
            'subnets': ['10.0.0.0/30'],
            'ports': ['22', 443],
            'timeout': '0.05',
            'max_hosts_per_subnet': '4',
            'max_history_entries': 5,
            'manage_baseline': True,
            'update_node_status': True,
            'max_diff_entries': 5,
            'max_node_status_entries': 5,
            'lookup_hostnames': False,
            'latency_warning_ms': 10,
            'flapping_window': 4,
            'flapping_threshold': 2,
            'max_port_change_summary': 2,
            'max_port_change_history': 2,
        }
    )
)

network_discovery.LOG_FILE = temp_log
network_discovery.CONFIG_FILE = temp_config
network_discovery.BASELINE_FILE = temp_baseline
network_discovery.DIFF_FILE = temp_diff

node_control_module = network_discovery.node_control
original_status_log = None
if node_control_module:
    original_status_log = node_control_module.STATUS_LOG
    original_health_log = getattr(node_control_module, 'HEALTH_LOG', None)
    node_control_module.STATUS_LOG = temp_node_status
    if hasattr(node_control_module, 'HEALTH_LOG'):
        node_control_module.HEALTH_LOG = temp_health

results = network_discovery.discover_from_config(probe=_fake_probe)
assert any(entry.get('reachable') for entry in results), 'Expected reachable host'

log_entries = json.loads(temp_log.read_text())
assert log_entries and 'results' in log_entries[-1]
summary = log_entries[-1].get('summary')
assert summary, 'Expected summary block in discovery log'
assert summary['reachable'] == 1
assert summary['unreachable'] == 1
assert summary['new_hosts'], 'First run should mark reachable hosts as new'
assert not summary['lost_hosts'], 'First run should not report lost hosts'
assert summary['recovered_hosts'] == []
assert summary['recovered_host_count'] == 0
assert summary['average_latency_ms'] == 12.5
assert summary['latency_warning_ms'] == 10
assert summary['slow_hosts'] and summary['slow_hosts'][0]['ip'] == '10.0.0.1'
assert summary['slow_hosts'][0]['port'] == 22
assert summary['flapping_hosts'] == []
assert summary['flapping_host_count'] == 0
assert summary['port_changes'] == []
assert summary['port_change_count'] == 0
subnet_stats = summary['subnets']['10.0.0.0/30']
assert subnet_stats['reachable'] == 1
assert subnet_stats['unreachable'] == 1
assert subnet_stats['slow_hosts'] == 1
assert subnet_stats['errors'] == 0
assert subnet_stats['average_latency_ms'] == 12.5
assert subnet_stats['min_latency_ms'] == 12.5
assert subnet_stats['max_latency_ms'] == 12.5

port_stats = summary['ports']['22']
assert port_stats['reachable'] == 1
assert port_stats['slow_hosts'] == 1
assert port_stats['average_latency_ms'] == 12.5


baseline_entries = json.loads(temp_baseline.read_text())
assert '10.0.0.1' in baseline_entries, 'Reachable host should update baseline log'

diff_entries = json.loads(temp_diff.read_text())
assert diff_entries[-1]['new_hosts'], 'Diff log should capture new hosts'

# Run a second discovery cycle to ensure history trimming and host diffing work.
time.sleep(0.01)
results_second = network_discovery.discover_from_config(probe=_fake_probe)
assert results_second, 'Expected discovery results on second run'

log_entries = json.loads(temp_log.read_text())
assert len(log_entries) == 2, 'History should grow until reaching the configured maximum'
second_summary = log_entries[-1]['summary']
assert second_summary['new_hosts'] == [], 'No additional hosts expected on repeat scan'
assert second_summary['lost_hosts'] == [], 'Reachable host should remain present'
assert second_summary['recovered_hosts'] == []
assert second_summary['recovered_host_count'] == 0
assert second_summary['flapping_host_count'] == 0
assert second_summary['port_changes'] == []
assert second_summary['port_change_count'] == 0

diff_entries = json.loads(temp_diff.read_text())
assert len(diff_entries) == 1, 'No new diff entries expected when topology unchanged'

# Simulate a recovery where a previously unreachable host comes online.
def _recovery_probe(ip, ports, timeout):
    if ip.endswith('2'):
        return True, ports[0], 8.0
    return False, None, None

time.sleep(0.01)
results_third = network_discovery.discover_from_config(probe=_recovery_probe)
assert results_third, 'Expected discovery results on third run'

log_entries = json.loads(temp_log.read_text())
assert len(log_entries) == 3
third_summary = log_entries[-1]['summary']
assert any(item['ip'] == '10.0.0.2' for item in third_summary['recovered_hosts'])
assert third_summary['recovered_host_count'] == len(third_summary['recovered_hosts']) == 1
assert third_summary['flapping_host_count'] == 0
assert third_summary['port_changes'] == []
assert third_summary['port_change_count'] == 0

diff_entries = json.loads(temp_diff.read_text())
assert len(diff_entries) == 2
assert '10.0.0.2' in diff_entries[-1]['new_hosts']

# Final scan toggles 10.0.0.1 back online to trigger flapping detection.
def _flap_probe(ip, ports, timeout):
    if ip.endswith('1'):
        return True, ports[0], 9.0
    if ip.endswith('2'):
        return True, ports[0], 8.0
    return False, None, None

time.sleep(0.01)
results_fourth = network_discovery.discover_from_config(probe=_flap_probe)
assert results_fourth, 'Expected discovery results on fourth run'

log_entries = json.loads(temp_log.read_text())
assert len(log_entries) == 4
fourth_summary = log_entries[-1]['summary']
flapping_ips = {item['ip'] for item in fourth_summary['flapping_hosts']}
assert '10.0.0.1' in flapping_ips, 'Recovered host should be flagged as flapping'
assert fourth_summary['flapping_host_count'] == len(fourth_summary['flapping_hosts']) == 1
flap_entry = next(item for item in fourth_summary['flapping_hosts'] if item['ip'] == '10.0.0.1')
assert flap_entry['current_state'] == 'online'
assert flap_entry['transitions'] >= 2
assert any(item['ip'] == '10.0.0.1' for item in fourth_summary['recovered_hosts'])
assert fourth_summary['port_changes'] == []
assert fourth_summary['port_change_count'] == 0

diff_entries = json.loads(temp_diff.read_text())
assert len(diff_entries) == 2
assert '10.0.0.2' in diff_entries[-1]['new_hosts']

if node_control_module:
    status_history = json.loads(temp_node_status.read_text())
    assert status_history, 'Node status log should contain discovery snapshot'
    statuses = status_history[-1]['statuses']
    assert any(
        any(entry['host'] == '10.0.0.2' and entry.get('recovered') for entry in snapshot['statuses'])
        for snapshot in status_history
    ), 'Recovered host should appear in status history'
    reachable_entry = next(entry for entry in statuses if entry['host'] == '10.0.0.2')
    assert reachable_entry.get('reachable') is True
    flapping_entry = next(entry for entry in statuses if entry['host'] == '10.0.0.1')
    assert flapping_entry.get('flapping') is True
    if reachable_entry.get('latency_ms') is not None:
        assert abs(reachable_entry.get('latency_ms') - 8.0) < 1e-6
    if temp_health.exists():
        health_data = json.loads(temp_health.read_text())
        assert '10.0.0.2' in health_data
        assert health_data['10.0.0.2']['state'] == 'online'
        assert health_data['10.0.0.2']['recovery_count'] >= 1
        assert health_data['10.0.0.2'].get('last_recovery')
        assert '10.0.0.1' in health_data
        assert health_data['10.0.0.1'].get('flapping') is True
        assert health_data['10.0.0.1'].get('flap_count', 0) >= 1
        assert health_data['10.0.0.1'].get('last_flap')

# Trigger a port change on 10.0.0.2 to ensure detection and status logging.
def _port_change_probe(ip, ports, timeout):
    if ip.endswith('1'):
        return True, ports[0], 9.5
    if ip.endswith('2'):
        return True, ports[1], 7.0
    return False, None, None

time.sleep(0.01)
results_fifth = network_discovery.discover_from_config(probe=_port_change_probe)
assert results_fifth, 'Expected discovery results on fifth run'

log_entries = json.loads(temp_log.read_text())
fifth_summary = log_entries[-1]['summary']
changes = fifth_summary['port_changes']
assert changes, 'Port change list should not be empty when port shifts'
change_ips = {item['ip'] for item in changes}
assert '10.0.0.2' in change_ips
change_entry = next(item for item in changes if item['ip'] == '10.0.0.2')
assert change_entry['previous_port'] == 22
assert change_entry['current_port'] == 443
assert change_entry.get('timestamp') is not None
assert fifth_summary['port_change_count'] == len(changes)
assert fifth_summary['port_change_total'] >= len(changes)

subnet_bucket = fifth_summary['subnets']['10.0.0.0/30']
assert subnet_bucket['port_changes'] == len(changes)
assert subnet_bucket.get('port_changes_total', 0) >= subnet_bucket['port_changes']

if node_control_module:
    status_history = json.loads(temp_node_status.read_text())
    latest_snapshot = status_history[-1]
    latest_statuses = latest_snapshot['statuses']
    port_changed_entry = next(entry for entry in latest_statuses if entry['host'] == '10.0.0.2')
    assert port_changed_entry.get('port_changed') is True
    assert port_changed_entry.get('previous_port') == 22
    assert port_changed_entry.get('current_port') == 443
    assert port_changed_entry.get('port') == 443
    if temp_health.exists():
        health_data = json.loads(temp_health.read_text())
        assert health_data['10.0.0.2'].get('port_change_count', 0) >= 1
        assert health_data['10.0.0.2'].get('last_port_change')
        assert health_data['10.0.0.2'].get('previous_port') == 22
        assert len(health_data['10.0.0.2'].get('port_change_history', [])) <= 2

# Trigger simultaneous port changes to ensure multiple entries are logged.
def _multi_port_change_probe(ip, ports, timeout):
    if ip.endswith('1'):
        return True, ports[1], 6.5
    if ip.endswith('2'):
        return True, ports[0], 7.5
    return False, None, None

time.sleep(0.01)
results_sixth = network_discovery.discover_from_config(probe=_multi_port_change_probe)
assert results_sixth

log_entries = json.loads(temp_log.read_text())
sixth_summary = log_entries[-1]['summary']
assert sixth_summary['port_change_count'] == 2
assert sixth_summary['port_change_total'] >= 2
change_hosts = {item['ip'] for item in sixth_summary['port_changes']}
assert {'10.0.0.1', '10.0.0.2'}.issubset(change_hosts)
subnet_bucket = sixth_summary['subnets']['10.0.0.0/30']
assert subnet_bucket['port_changes'] == 2
assert subnet_bucket.get('port_changes_total') >= 2

if node_control_module:
    status_history = json.loads(temp_node_status.read_text())
    latest_snapshot = status_history[-1]
    latest_statuses = latest_snapshot['statuses']
    changed_hosts = {
        entry['host']
        for entry in latest_statuses
        if entry.get('port_changed')
    }
    assert {'10.0.0.1', '10.0.0.2'}.issubset(changed_hosts)
    if temp_health.exists():
        health_data = json.loads(temp_health.read_text())
        assert len(health_data['10.0.0.1'].get('port_change_history', [])) <= 2
        assert len(health_data['10.0.0.2'].get('port_change_history', [])) <= 2

# Reduce port change summary/history limits to verify trimming keeps the newest entry.
trimmed_config = {
    'subnets': ['10.0.0.0/30'],
    'ports': ['22', 443],
    'timeout': '0.05',
    'max_hosts_per_subnet': '4',
    'max_history_entries': 5,
    'manage_baseline': True,
    'update_node_status': True,
    'max_diff_entries': 5,
    'max_node_status_entries': 5,
    'lookup_hostnames': False,
    'latency_warning_ms': 10,
    'flapping_window': 4,
    'flapping_threshold': 2,
    'max_port_change_summary': 1,
    'max_port_change_history': 1,
}
temp_config.write_text(json.dumps(trimmed_config))


def _trimmed_port_change_probe(ip, ports, timeout):
    if ip.endswith('1'):
        return True, ports[0], 5.5
    if ip.endswith('2'):
        return True, ports[1], 5.0
    return False, None, None


time.sleep(0.01)
results_seventh = network_discovery.discover_from_config(probe=_trimmed_port_change_probe)
assert results_seventh

log_entries = json.loads(temp_log.read_text())
seventh_summary = log_entries[-1]['summary']
assert seventh_summary['port_change_total'] >= 2
assert seventh_summary['port_change_count'] == 1
assert len(seventh_summary['port_changes']) == 1
trimmed_entry = seventh_summary['port_changes'][0]
assert trimmed_entry['ip'] in {'10.0.0.1', '10.0.0.2'}
subnet_bucket = seventh_summary['subnets']['10.0.0.0/30']
assert subnet_bucket['port_changes'] == 1
assert subnet_bucket.get('port_changes_total', 0) >= 2

if node_control_module:
    status_history = json.loads(temp_node_status.read_text())
    latest_statuses = status_history[-1]['statuses']
    changed_hosts = {
        entry['host']
        for entry in latest_statuses
        if entry.get('port_changed')
    }
    assert {'10.0.0.1', '10.0.0.2'}.issubset(changed_hosts)
    if temp_health.exists():
        health_data = json.loads(temp_health.read_text())
        for host in ['10.0.0.1', '10.0.0.2']:
            history = health_data.get(host, {}).get('port_change_history', [])
            assert len(history) <= 1

print('Network Discovery Test Passed')

temp_log.unlink(missing_ok=True)
temp_config.unlink(missing_ok=True)
temp_baseline.unlink(missing_ok=True)
temp_diff.unlink(missing_ok=True)
temp_node_status.unlink(missing_ok=True)
temp_health.unlink(missing_ok=True)

if node_control_module and original_status_log is not None:
    node_control_module.STATUS_LOG = original_status_log
    if original_health_log is not None:
        node_control_module.HEALTH_LOG = original_health_log
