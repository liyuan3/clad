from tests.test_reconcile import _run_until_disconnect
from tests.support import make_conversation, submit

def test_done_bypasses_reconciliation(client, make_device, connect_device):
    device, conversation, run = _run_until_disconnect(client, make_device, connect_device)
    fake = connect_device(device)
    fake.done(run['id'])
    response = fake.receive()
    assert response['type'] == 'error', response

def test_uncertain_dispatch_not_found_must_not_release(client, app, monkeypatch, make_device, connect_device):
    device = make_device('alice')
    fake = connect_device(device)
    conversation = make_conversation(client, device['headers'], device['device_id'])
    original = app.state.hub.send
    async def uncertain_send(device_id, payload):
        await original(device_id, payload)
        return False  # delivery happened but transport completion is uncertain
    monkeypatch.setattr(app.state.hub, 'send', uncertain_send)
    run = submit(client, device['headers'], conversation['id'])['body']
    fake.expect('run')
    fake.event(run['id'], 1, 'already executing')
    fake.expect('ack')
    fake.report(run['id'], 'not_found', 0)
    response = fake.expect('report_result')
    assert response['accepted'] is False, response
