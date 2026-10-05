"""Offline tests for main.py: the SDK call is stubbed, nothing is billed."""
import pytest

import main


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setattr(main, 'has_credentials', lambda: True)


def stub_result(monkeypatch, result):
    calls = []

    def fake_subscribe(model, arguments, **_):
        calls.append((model, arguments))
        return result

    monkeypatch.setattr(main.higgsfield_client, 'subscribe', fake_subscribe)
    return calls


def test_completed_prints_video_url(monkeypatch, capsys):
    calls = stub_result(monkeypatch, {'status': 'completed', 'video': {'url': 'https://cdn.example/v.mp4'}})
    assert main.main() == 0
    assert capsys.readouterr().out.strip() == 'https://cdn.example/v.mp4'
    assert calls == [('bytedance/seedance-2.5/text-to-video', {
        'prompt': 'A cinematic scene at sunset', 'duration': 5, 'resolution': '720p', 'aspect_ratio': '16:9',
    })]


@pytest.mark.parametrize('status', ['failed', 'nsfw', 'canceled', 'weird'])
def test_non_completed_statuses_fail(monkeypatch, capsys, status):
    stub_result(monkeypatch, {'status': status, 'video': {'url': 'https://cdn.example/v.mp4'}})
    assert main.main() == 1
    assert capsys.readouterr().out == ''


def test_completed_without_url_fails(monkeypatch):
    stub_result(monkeypatch, {'status': 'completed'})
    assert main.main() == 1
