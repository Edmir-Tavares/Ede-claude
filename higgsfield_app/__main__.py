"""CLI para chamar qualquer modelo da Higgsfield.

Exemplos:
    python -m higgsfield_app check
    python -m higgsfield_app run bytedance/seedream/v4/text-to-image \\
        --prompt "Um lago ao pôr do sol" -p resolution=2K -p aspect_ratio=16:9
    python -m higgsfield_app run kling-video/v2.6/pro/image-to-video \\
        --prompt "câmera lenta" --upload image_url=./foto.jpg --download outputs/
    python -m higgsfield_app status <request_id>
    python -m higgsfield_app result <request_id> --download outputs/
    python -m higgsfield_app cancel <request_id>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx

from higgsfield_app import client as hf


def parse_value(raw: str) -> Any:
    """Converte '2K' -> '2K', '5' -> 5, 'false' -> False, '[1,2]' -> [1, 2]."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_pairs(pairs: List[str], flag: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition('=')
        if not sep or not key:
            raise SystemExit(f'{flag} espera CHAVE=VALOR, recebido: {pair!r}')
        parsed[key] = value
    return parsed


def build_arguments(args: argparse.Namespace) -> Dict[str, Any]:
    arguments: Dict[str, Any] = {}
    if args.json:
        source = Path(args.json[1:]).read_text() if args.json.startswith('@') else args.json
        arguments.update(json.loads(source))
    if args.prompt is not None:
        arguments['prompt'] = args.prompt
    for key, value in parse_pairs(args.param, '--param').items():
        arguments[key] = parse_value(value)
    for key, path in parse_pairs(args.upload, '--upload').items():
        print(f'Enviando {path}...', file=sys.stderr)
        arguments[key] = hf.upload_file(path)
    return arguments


def finish(result: Dict[str, Any], download: str | None) -> None:
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if download:
        for path in hf.download_outputs(result, download):
            print(f'Salvo: {path}', file=sys.stderr)


def cmd_check(_: argparse.Namespace) -> int:
    if not hf.has_credentials():
        print('Credenciais NÃO encontradas. Copie .env.example para .env e preencha HF_KEY.')
        return 1
    print('Credenciais encontradas (HF_KEY ou HF_API_KEY + HF_API_SECRET).')
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    arguments = build_arguments(args)
    if args.dry_run:
        print(json.dumps({'model': args.model, 'arguments': arguments}, indent=2, ensure_ascii=False))
        return 0

    if args.no_wait:
        controller = hf.submit(args.model, arguments, webhook_url=args.webhook)
        print(json.dumps({'request_id': controller.request_id}))
        return 0

    result = hf.generate(
        args.model,
        arguments,
        on_status=lambda status: print(f'Status: {type(status).__name__}', file=sys.stderr),
    )
    finish(result, args.download)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(type(hf.get_client().status(args.request_id)).__name__)
    return 0


def cmd_result(args: argparse.Namespace) -> int:
    finish(hf.get_client().result(args.request_id), args.download)
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    hf.get_client().cancel(args.request_id)
    print('Cancelamento solicitado.')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='python -m higgsfield_app', description='Cliente da API Higgsfield.')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('check', help='verifica se as credenciais estão configuradas').set_defaults(func=cmd_check)

    run = sub.add_parser('run', help='executa qualquer modelo pelo ID do endpoint')
    run.add_argument('model', help='ID do modelo, ex.: bytedance/seedream/v4/text-to-image')
    run.add_argument('--prompt', help='atalho para o argumento "prompt"')
    run.add_argument('-p', '--param', action='append', default=[], metavar='CHAVE=VALOR',
                     help='argumento do modelo; valores são lidos como JSON quando possível (repetível)')
    run.add_argument('--json', help='argumentos como JSON, ou @arquivo.json')
    run.add_argument('--upload', action='append', default=[], metavar='CHAVE=ARQUIVO',
                     help='faz upload do arquivo local e usa a URL como argumento (repetível)')
    run.add_argument('--download', metavar='PASTA', help='baixa as mídias geradas para esta pasta')
    run.add_argument('--no-wait', action='store_true', help='apenas envia e imprime o request_id')
    run.add_argument('--webhook', help='URL chamada pela Higgsfield ao concluir (com --no-wait)')
    run.add_argument('--dry-run', action='store_true', help='mostra o payload sem chamar a API')
    run.set_defaults(func=cmd_run)

    for name, func, help_text in (
        ('status', cmd_status, 'mostra o status de uma requisição'),
        ('result', cmd_result, 'espera e mostra o resultado de uma requisição'),
        ('cancel', cmd_cancel, 'cancela uma requisição ainda na fila'),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument('request_id')
        if name == 'result':
            p.add_argument('--download', metavar='PASTA')
        p.set_defaults(func=func)

    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except hf.CredentialsMissedError as exc:
        print(exc, file=sys.stderr)
        return 1
    except httpx.HTTPStatusError as exc:
        print(f'Erro da API ({exc.response.status_code}): {exc.response.text}', file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f'Falha de conexão com a API: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
