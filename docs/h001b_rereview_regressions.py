from tests.test_review_fixes import _started
from tests.support import wait_for

def test_delivered_without_events_cannot_be_not_found(client, make_device, connect_device):
    device, fake, _, run = _started(client, make_device, connect_device)
    fake.close()
    wait_for(lambda: client.get('/api/runs/'+run['id'], headers=device['headers']).json()['status']=='unknown')
    fake = connect_device(device)
    fake.report(run['id'], 'not_found', last_seq=0)
    result = fake.expect('report_result')
    assert result['accepted'] is False, result

def test_gap_requires_resending_highest_rejected_event(client, make_device, connect_device):
    device, fake, _, run = _started(client, make_device, connect_device)
    fake.event(run['id'], 1, 'one'); fake.expect('ack')
    fake.event(run['id'], 3, 'three'); fake.expect('error')
    fake.event(run['id'], 2, 'two'); fake.expect('ack')
    fake.done(run['id'], 'completed', last_seq=2)
    result = fake.receive()
    assert result['type']=='error', result
