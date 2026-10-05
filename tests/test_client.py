"""Testes offline: nenhuma chamada real à API é feita."""
import json

import pytest

from higgsfield_app import client as hf
from higgsfield_app.__main__ import build_parser, build_arguments, main, parse_value


class FakeClient:
    def __init__(self):
        self.calls = []

    def subscribe(self, model, arguments, on_queue_update=None):
        self.calls.append((model, arguments))
        return {'images': [{'url': 'https://cdn.example/a.png'}], 'video': {'url': 'https://cdn.example/b.mp4'}}


@pytest.fixture
def no_credentials(monkeypatch):
    for name in ('HF_KEY', 'HF_API_KEY', 'HF_API_SECRET'):
        monkeypatch.delenv(name, raising=False)


def test_has_credentials(monkeypatch, no_credentials):
    assert not hf.has_credentials()
    monkeypatch.setenv('HF_API_KEY', 'k')
    assert not hf.has_credentials()
    monkeypatch.setenv('HF_API_SECRET', 's')
    assert hf.has_credentials()


def test_get_client_without_credentials_raises(no_credentials):
    with pytest.raises(hf.CredentialsMissedError):
        hf.get_client()


def test_generate_passes_any_model_id():
    fake = FakeClient()
    result = hf.generate('/vendor/any/model/', {'prompt': 'x'}, client=fake)
    assert fake.calls == [('vendor/any/model', {'prompt': 'x'})]
    assert list(hf.iter_media_urls(result)) == ['https://cdn.example/a.png', 'https://cdn.example/b.mp4']


def test_parse_value():
    assert parse_value('2K') == '2K'
    assert parse_value('5') == 5
    assert parse_value('false') is False
    assert parse_value('[1, 2]') == [1, 2]


def test_build_arguments_merges_sources(tmp_path):
    payload = tmp_path / 'args.json'
    payload.write_text(json.dumps({'resolution': '1K', 'seed': 1}))
    args = build_parser().parse_args([
        'run', 'm', '--json', f'@{payload}', '--prompt', 'oi', '-p', 'resolution=2K', '-p', 'camera_fixed=false',
    ])
    assert build_arguments(args) == {'resolution': '2K', 'seed': 1, 'prompt': 'oi', 'camera_fixed': False}


def test_check_command(no_credentials, capsys):
    assert main(['check']) == 1
