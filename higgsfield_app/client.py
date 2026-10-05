"""Camada fina sobre o SDK oficial `higgsfield-client`.

Qualquer modelo da Higgsfield é chamado pelo seu ID de endpoint
(ex.: "bytedance/seedream/v4/text-to-image"), então nada aqui é
específico de um modelo: basta passar o ID e os argumentos que a
documentação do modelo pede.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional
from urllib.parse import urlparse
from urllib.request import urlopen

from dotenv import load_dotenv

import higgsfield_client
from higgsfield_client import CredentialsMissedError, Status

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Carrega o .env da raiz do projeto sem sobrescrever variáveis já exportadas.
load_dotenv(PROJECT_ROOT / '.env', override=False)


def has_credentials() -> bool:
    """True se HF_KEY ou o par HF_API_KEY + HF_API_SECRET estiver definido."""
    if os.getenv('HF_KEY'):
        return True
    return bool(os.getenv('HF_API_KEY') and os.getenv('HF_API_SECRET'))


def get_client(api_key: Optional[str] = None) -> higgsfield_client.SyncClient:
    """Cria um cliente síncrono. Sem `api_key`, usa as variáveis de ambiente."""
    if api_key is None and not has_credentials():
        raise CredentialsMissedError(
            'Credenciais da Higgsfield ausentes. Copie .env.example para .env e '
            'preencha HF_KEY (formato "API_KEY:API_SECRET") ou HF_API_KEY + HF_API_SECRET.'
        )
    return higgsfield_client.SyncClient(api_key=api_key)


def generate(
    model: str,
    arguments: Dict[str, Any],
    *,
    on_status: Optional[Callable[[Status], None]] = None,
    client: Optional[higgsfield_client.SyncClient] = None,
) -> Dict[str, Any]:
    """Envia uma geração para `model` e espera o resultado final (JSON)."""
    client = client or get_client()
    return client.subscribe(
        model.strip('/'),
        arguments=arguments,
        on_queue_update=on_status,
    )


def submit(
    model: str,
    arguments: Dict[str, Any],
    *,
    webhook_url: Optional[str] = None,
    client: Optional[higgsfield_client.SyncClient] = None,
) -> higgsfield_client.SyncRequestController:
    """Envia sem esperar; use o controller retornado (ou o request_id) depois."""
    client = client or get_client()
    return client.submit(model.strip('/'), arguments=arguments, webhook_url=webhook_url)


def upload_file(path: os.PathLike | str, client: Optional[higgsfield_client.SyncClient] = None) -> str:
    """Faz upload de um arquivo local e retorna a URL pública para usar como argumento."""
    client = client or get_client()
    return client.upload_file(Path(path))


def iter_media_urls(result: Any) -> Iterator[str]:
    """Percorre o JSON de resultado e devolve toda URL http(s) em chaves 'url'."""
    if isinstance(result, dict):
        for key, value in result.items():
            if key == 'url' and isinstance(value, str) and value.startswith(('http://', 'https://')):
                yield value
            else:
                yield from iter_media_urls(value)
    elif isinstance(result, list):
        for item in result:
            yield from iter_media_urls(item)


def download_outputs(result: Dict[str, Any], out_dir: os.PathLike | str, prefix: str = '') -> List[Path]:
    """Baixa todas as mídias do resultado para `out_dir` e retorna os caminhos."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    for index, url in enumerate(iter_media_urls(result)):
        name = Path(urlparse(url).path).name or f'output_{index}'
        target = out / f'{prefix}{index:02d}_{name}'
        with urlopen(url) as response, open(target, 'wb') as fh:
            fh.write(response.read())
        saved.append(target)
    return saved
