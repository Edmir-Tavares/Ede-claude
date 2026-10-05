# Ede-claude — integração com a API Higgsfield

Projeto Python pronto para chamar **qualquer modelo** da [API Higgsfield](https://docs.higgsfield.ai/docs/models)
(imagem, vídeo, áudio…) usando o SDK oficial [`higgsfield-client`](https://github.com/higgsfield-ai/higgsfield-client).

Todo modelo é acessado pelo seu **ID de endpoint** (ex.: `bytedance/seedream/v4/text-to-image`).
A requisição vai para `POST https://api.higgsfield.ai/<ID do modelo>`, entra numa fila e o
cliente aguarda o resultado. Por isso não há nada fixo no código: para usar um modelo novo,
basta passar o ID dele e os parâmetros listados na página do modelo na documentação.

## 1. Instalação

Requer Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Sua chave de API

1. Gere a chave e o segredo em <https://cloud.higgsfield.ai/>.
2. Copie o modelo de configuração e preencha:

   ```bash
   cp .env.example .env
   ```

   No `.env`, use **uma** das opções:

   ```dotenv
   HF_KEY=SUA_API_KEY:SEU_API_SECRET
   # ou
   HF_API_KEY=SUA_API_KEY
   HF_API_SECRET=SEU_API_SECRET
   ```

   O `.env` está no `.gitignore` e nunca é enviado ao Git.
3. Confira:

   ```bash
   python -m higgsfield_app check
   ```

## Exemplo: Seedance 2.5 (texto → vídeo)

`main.py` chama `bytedance/seedance-2.5/text-to-video` com `subscribe` do SDK oficial
(prompt "A cinematic scene at sunset", 5 s, 720p, 16:9), espera a conclusão e imprime a
URL do vídeo. Pedidos com status `failed`, `nsfw` ou `canceled` terminam com código 1.

```bash
# coloque HF_KEY=key-id:key-secret em .env.local (ignorado pelo Git)
python main.py
```

As credenciais são lidas de `.env.local` e, se ausentes, de `.env`.

## 3. Usando pela linha de comando

```bash
# Texto → imagem, salvando os arquivos em outputs/
python -m higgsfield_app run bytedance/seedream/v4/text-to-image \
  --prompt "Um lago sereno ao pôr do sol" \
  -p resolution=2K -p aspect_ratio=16:9 -p camera_fixed=false \
  --download outputs/

# Imagem → vídeo: --upload envia o arquivo local e usa a URL no parâmetro indicado
python -m higgsfield_app run kling-video/v2.6/pro/image-to-video \
  --prompt "câmera se aproxima lentamente" \
  --upload image_url=./foto.jpg \
  --download outputs/

# Parâmetros complexos em JSON (inline ou @arquivo)
python -m higgsfield_app run <ID-do-modelo> --json @args.json

# Ver o payload sem gastar créditos
python -m higgsfield_app run <ID-do-modelo> --prompt "teste" --dry-run

# Enviar sem esperar e acompanhar depois
python -m higgsfield_app run <ID-do-modelo> --prompt "..." --no-wait [--webhook https://seu.site/hook]
python -m higgsfield_app status <request_id>
python -m higgsfield_app result <request_id> --download outputs/
python -m higgsfield_app cancel <request_id>
```

`-p CHAVE=VALOR` converte o valor como JSON quando possível (`5` → número,
`false` → booleano, `[1,2]` → lista); caso contrário, fica como texto.

> Os nomes dos parâmetros (`image_url`, `duration`, `resolution`…) variam por modelo.
> Consulte a página de cada modelo em <https://docs.higgsfield.ai/docs/models>.

## 4. Usando no seu código Python

```python
from higgsfield_app import generate, upload_file, download_outputs

result = generate(
    'bytedance/seedream/v4/text-to-image',
    {'prompt': 'Um lago ao pôr do sol', 'resolution': '2K', 'aspect_ratio': '16:9'},
)
print(result)                       # JSON completo devolvido pelo modelo
download_outputs(result, 'outputs') # baixa todas as imagens/vídeos do resultado

# Com arquivo de entrada
image_url = upload_file('foto.jpg')
video = generate('kling-video/v2.6/pro/image-to-video', {'image_url': image_url, 'prompt': '...'})
```

Também é possível usar o SDK oficial diretamente (`import higgsfield_client`), incluindo
a versão assíncrona (`subscribe_async`, `submit_async`) e a Agent API (`SyncClient().agents`).
Veja `examples/quickstart.py`.

## Exemplos de IDs de modelos

| Tipo | ID |
| --- | --- |
| Texto → imagem (Seedream 4) | `bytedance/seedream/v4/text-to-image` |
| Imagem → vídeo (Kling 2.6 Pro) | `kling-video/v2.6/pro/image-to-video` |
| Imagem → vídeo (Kling 3.0 Turbo) | `kling-video/v3.0-turbo/image-to-video` |

O catálogo completo (50+ modelos) e os parâmetros de cada um estão em
<https://docs.higgsfield.ai/docs/models>.

## Estrutura

```
higgsfield_app/
  client.py     # generate / submit / upload_file / download_outputs
  __main__.py   # CLI (python -m higgsfield_app ...)
examples/quickstart.py
tests/          # testes offline (pytest), não gastam créditos
.env.example    # modelo das credenciais
```

## Testes

```bash
pip install pytest
python -m pytest
```
