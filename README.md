# Server Monitor

Dashboard de monitoramento para um celular Android (via Termux) que
funciona como servidor de Minecraft. Backend em **Python + FastAPI**
(escolhido em vez de Node porque `psutil` cobre CPU/RAM/processos de
forma mais direta em Android/Termux, e o FastAPI já traz WebSocket
nativo pra atualização em tempo real).

```
CELULAR PRINCIPAL → GitHub → CELULAR SERVIDOR (Termux) → Dashboard → Internet
```

- Você edita `frontend/` (HTML/CSS/JS) pelo GitHub, de qualquer lugar.
- O celular servidor puxa (`git pull`) essas mudanças automaticamente.
- Os dados dos sensores (CPU, RAM, bateria, etc.) **nunca** vão pro
  GitHub — são coletados e guardados só no próprio celular servidor.

---

## 1. Instalação no Termux (celular servidor)

Rode isto **no celular servidor**, dentro do Termux:

```bash
# 1. Atualizar pacotes do Termux
pkg update -y && pkg upgrade -y

# 2. Instalar dependências do sistema
pkg install -y git python clang termux-api

# 3. (Opcional, mas recomendado) instalar o app "Termux:API"
#    pela Play Store ou F-Droid — sem ele, bateria e wifi ficam
#    "indisponíveis" no dashboard.

# 4. Dar permissão de armazenamento (opcional, só se for ler pastas
#    fora do Termux)
termux-setup-storage

# 5. Clonar o seu repositório (troque pela URL do seu GitHub)
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git server-monitor
cd server-monitor

# 6. Criar e ativar o ambiente virtual Python
python -m venv venv
source venv/bin/activate

# 7. Instalar as dependências Python
pip install -r requirements.txt

# 8. Criar o arquivo de configuração
cp .env.example .env

# 9. Editar o .env e definir pelo menos o AUTH_TOKEN
#    (gere um token forte com o comando abaixo e cole no .env)
openssl rand -hex 24
nano .env
```

No `.env`, no mínimo configure:
- `AUTH_TOKEN` — token de acesso ao dashboard (obrigatório).
- `MC_HOST` / `MC_PORT` — endereço do seu servidor Minecraft (geralmente `127.0.0.1` e `25565`).
- `MC_SERVER_DIR` — caminho da pasta do servidor Minecraft, se quiser ver logs e tamanho em disco.

## 2. Rodando

```bash
bash scripts/start.sh
```

Acesse pelo navegador do próprio celular: `http://localhost:8080`
Vai pedir o **token de acesso** (o mesmo `AUTH_TOKEN` do `.env`).

Pra manter rodando e reiniciar sozinho se cair:

```bash
bash scripts/monitor.sh
```

### Iniciar automaticamente quando o celular ligar

Instale o app **Termux:Boot** (F-Droid) e crie o arquivo
`~/.termux/boot/start-monitor.sh` com:

```bash
#!/data/data/com.termux/files/usr/bin/bash
cd ~/server-monitor
bash scripts/monitor.sh &
```

## 3. Testando

- `curl http://localhost:8080/api/status -H "Authorization: Bearer SEU_TOKEN"` deve devolver um JSON com o status atual.
- Abra `http://localhost:8080` no navegador do próprio celular servidor primeiro, pra confirmar que tudo funciona antes de expor pra internet.

## 4. Editando o visual pelo GitHub

Edite `frontend/index.html`, `frontend/style.css` ou `frontend/script.js`
direto no GitHub (ou no celular principal) e faça commit/push. O
processo de sincronização, que já roda dentro do próprio servidor,
verifica o repositório a cada `GIT_UPDATE_INTERVAL` segundos (padrão:
60) e aplica as mudanças com `git pull`, sem derrubar a API. Pra
forçar uma atualização imediata: `bash scripts/update.sh`.

## 5. Acesso local vs. rede local vs. internet

- **localhost** (`http://localhost:8080`): só funciona dentro do
  próprio celular servidor.
- **IP da rede local** (ex: `http://192.168.0.15:8080`): funciona
  pra qualquer dispositivo conectado ao mesmo Wi-Fi. Descubra o IP
  com `ip addr` ou `ifconfig` dentro do Termux.
- **Internet** (fora da sua rede): o celular normalmente está atrás
  de NAT/CGNAT da operadora, então não dá pra simplesmente abrir uma
  porta. As opções mais simples, mantendo o dashboard hospedado no
  próprio celular:
  - **Tailscale** (`pkg install tailscale` ou app oficial): cria uma
    rede privada entre seus dispositivos — acesso simples e seguro,
    sem expor a porta pra internet pública.
  - **Cloudflare Tunnel** (`cloudflared`): cria um túnel autenticado
    até o celular sem abrir portas no roteador. Requer conta
    Cloudflare (gratuita).
  - **ngrok**: alternativa rápida pra testes, túnel temporário.

  Qualquer uma dessas opções apenas cria um "caminho" até o celular —
  o servidor continua sendo o Termux, nada é hospedado fora dele.
  **Sempre mantenha o `AUTH_TOKEN` configurado** antes de expor o
  dashboard pra fora da sua rede local.

## 6. Limitações reais do Android/Termux (leia antes de reportar "bug")

- Sem root, o Android **não expõe**: IMEI, gateway/DNS detalhados,
  ciclos de carga da bateria, capacidade real em mAh, e a maioria dos
  sensores térmicos internos além da bateria e (às vezes) da CPU. O
  dashboard mostra "Indisponível" nesses casos — não inventamos valor.
- **TPS do Minecraft** não existe no protocolo padrão de status —
  só é possível via RCON + comando de um plugin (Paper/Spigot
  trazem o comando `tps` nativo). Configure `MC_RCON_PASSWORD` no
  `.env` e habilite `enable-rcon=true` no `server.properties` do
  Minecraft se quiser esse dado.
- "Velocidade de download/upload" no card de rede é a **taxa real de
  tráfego** da interface (bytes/s medidos), não um teste de
  velocidade — de propósito, pra não gastar dados/CPU do celular que
  já está rodando o Minecraft.
- O Android pode **matar processos em segundo plano** pra economizar
  bateria. Desative a otimização de bateria pro Termux (Ajustes >
  Apps > Termux > Bateria > Sem restrições) e use
  `termux-wake-lock` (já incluso no `scripts/monitor.sh`).
- Fabricantes como Xiaomi/Samsung têm gerenciadores de energia
  próprios que também podem matar o Termux — pode ser necessário
  liberar o app nas configurações específicas do fabricante.
- É necessário manter o celular ligado e conectado (Wi-Fi ou dados
  móveis) o tempo todo pro servidor continuar no ar.

## 7. Segurança

- O token de acesso (`AUTH_TOKEN`) fica só no `.env` do celular
  servidor — nunca no código, nunca no GitHub (o `.gitignore` já
  exclui o `.env`).
- Todas as rotas `/api/*` e o `/ws` exigem o token.
- Não deixe `ALLOW_NO_AUTH=true` a não ser que esteja testando
  isoladamente sem exposição de rede.

## 8. Estrutura do projeto

```
server-monitor/
├── frontend/           # editado pelo GitHub — HTML/CSS/JS do dashboard
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── assets/
├── backend/             # roda só no celular servidor
│   ├── server.py         # FastAPI: rotas /api/*, /ws, servir o frontend
│   ├── system.py          # CPU, RAM, uptime, info do Android
│   ├── storage.py         # armazenamento
│   ├── battery.py         # bateria (via termux-api)
│   ├── temperature.py     # sensores térmicos
│   ├── network.py         # wifi, IP, tráfego, ping
│   ├── processes.py       # lista de processos
│   ├── minecraft.py       # status do servidor Minecraft
│   ├── history.py         # histórico em SQLite (local, nunca vai pro git)
│   ├── alerts.py          # cálculo dos alertas
│   ├── git_sync.py        # sincronização periódica com o GitHub
│   ├── auth.py            # autenticação por token
│   └── config.py          # variáveis de ambiente
├── scripts/
│   ├── start.sh
│   ├── update.sh
│   └── monitor.sh
├── .env.example
├── .gitignore
└── requirements.txt
```

## 9. Endpoints da API

Todos exigem `Authorization: Bearer <AUTH_TOKEN>`.

| Rota | Descrição |
|---|---|
| `GET /` | Dashboard (HTML) |
| `GET /api/status` | Snapshot completo (usado pelo card principal) |
| `GET /api/system` | Informações do Android |
| `GET /api/cpu` | CPU |
| `GET /api/memory` | RAM |
| `GET /api/storage` | Armazenamento |
| `GET /api/battery` | Bateria |
| `GET /api/temperature` | Temperatura |
| `GET /api/network` | Rede |
| `GET /api/processes?sort=cpu\|ram\|pid\|name` | Processos |
| `GET /api/minecraft` | Status do Minecraft |
| `GET /api/history?period=5m\|1h\|6h\|24h` | Histórico |
| `GET /api/events` | Notificações/eventos |
| `GET /api/git-sync` | Status da última sincronização com o GitHub |
| `WS /ws?token=...` | Atualização em tempo real (a cada 3s) |
