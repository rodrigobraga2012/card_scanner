# Pokémon Card Scanner

Web app (PWA) que roda no navegador do Android e do iPhone: você fotografa a carta,
o app identifica **qual carta exata** ela é (nome, coleção e número) e mostra o
**valor de mercado em reais**.

## Como funciona

1. **Foto** – câmera ao vivo (precisa de HTTPS) ou câmera/galeria do próprio celular
   (funciona até em HTTP). A foto é reduzida no celular antes de enviar.
2. **Leitura** – o backend envia a foto para o Claude (visão), que lê o nome, o número
   da carta (ex.: `136/189`), a sigla da coleção, o idioma e se é holo/reverse.
3. **Identificação** – esses dados são casados com o catálogo da
   [TCGdex](https://tcgdex.dev): número + total da coleção + nome apontam a carta exata.
   Se houver dúvida, o app mostra as alternativas para você tocar na certa.
4. **Preço em R$** – preços de mercado do Cardmarket (EUR) e do TCGplayer (USD), vindos
   da TCGdex, convertidos pela cotação do dia (AwesomeAPI). O app também ajusta pelo
   estado da carta e tem links para conferir na Liga Pokémon e na MYP Cards.

## Instalação

```powershell
cd backend
pip install -r requirements.txt
copy .env.example .env
```

Edite `backend/.env` e coloque sua chave em `ANTHROPIC_API_KEY`
(crie em https://console.anthropic.com/settings/keys). Sem a chave, a busca por nome
continua funcionando, mas a identificação por foto fica desligada.

Custo aproximado: cerca de US$ 0,01 a 0,02 por foto identificada.

## Rodando

```powershell
cd backend
python main.py
```

Abra `http://localhost:5000` no computador.

### No celular (mesma rede Wi-Fi)

Abra `http://IP-DO-COMPUTADOR:5000` (ex.: `http://192.168.0.10:5000`).
Assim o botão **Escanear** abre a câmera nativa do celular, tira a foto e identifica.
Funciona no Android e no iPhone.

### Câmera ao vivo dentro do app (HTTPS)

Navegadores só liberam a câmera ao vivo em HTTPS. Opções:

- **Cloudflare Tunnel (recomendado, funciona no iPhone e Android, de qualquer lugar):**
  instale o `cloudflared` e rode, com o servidor já ligado:

  ```powershell
  cloudflared tunnel --url http://localhost:5000
  ```

  Ele mostra uma URL `https://....trycloudflare.com` para abrir no celular.
  Qualquer pessoa com o link acessa enquanto o túnel estiver aberto.

- **Certificado autoassinado (só rede local, melhor no Android):** coloque `HTTPS=1`
  no `.env` e abra `https://IP-DO-COMPUTADOR:5000` (aceite o aviso de segurança).

### Instalar como app

No celular, abra o site e use **Adicionar à tela inicial** (Safari: botão Compartilhar;
Chrome: menu ⋮).

## Estrutura

```
backend/
  main.py               servidor Flask (serve o frontend e a API)
  routes/cards.py       /api/identify, /api/cards/search, /api/cards/<id>
  routes/prices.py      /api/prices/<id>  (preço em R$)
  routes/collection.py  /api/collection   (coleção local em SQLite)
  services/identify.py  leitura da carta pela foto (Claude)
  services/tcgdex.py    catálogo e casamento da carta exata
  services/pricing.py   conversão de preços para R$
frontend/               PWA (HTML/CSS/JS puro)
```

## Observações

- Os preços são **internacionais convertidos**; o mercado brasileiro pode ser diferente.
- Cartas japonesas e promos muito raras podem não ter preço na TCGdex.
- Nunca rode com `FLASK_DEBUG=1` exposto na rede.
