"""Exemplo mínimo: gera uma imagem e salva em outputs/.

Uso: python examples/quickstart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from higgsfield_app import download_outputs, generate  # noqa: E402

result = generate(
    'bytedance/seedream/v4/text-to-image',
    {
        'prompt': 'A serene lake at sunset with mountains',
        'resolution': '2K',
        'aspect_ratio': '16:9',
        'camera_fixed': False,
    },
    on_status=lambda status: print('Status:', type(status).__name__),
)

for path in download_outputs(result, 'outputs'):
    print('Salvo em', path)
