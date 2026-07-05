# 🚗 LavaJato — Sistema de Contagem Automática de Veículos

Sistema completo para contar veículos que entram no lava jato usando câmera IP existente, detecção com YOLO e rastreamento por linha virtual configurável.

## Funcionalidades

- **Detecção em tempo real** com YOLO (carros, caminhões, motos, ônibus)
- **Rastreamento individual** por ByteTrack — cada veículo tem um ID
- **Linha virtual configurável** — desenhe no frame da câmera pelo painel
- **Contagem direcional** — entrada, saída ou ambos
- **Anti-duplicidade** — cooldown por tracker ID, cross-product geometry
- **Dashboard** com gráficos por hora e por dia, atualização automática
- **Histórico filtrado** com exportação CSV e Excel
- **Correção manual** com auditoria completa
- **Usuários e permissões** — Admin, Operador, Leitura
- **HTTPS automático** via Let's Encrypt / Certbot
- **Interface em português** (pt-BR)

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python + FastAPI + SQLAlchemy async |
| Visão computacional | OpenCV + Ultralytics YOLO |
| Rastreamento | ByteTrack (embutido no Ultralytics) |
| Banco de dados | PostgreSQL 16 |
| Frontend | Next.js 14 + Tailwind CSS |
| Reverse proxy | Nginx + Certbot (Let's Encrypt) |
| Deploy | Docker Compose |

---

## Pré-requisitos na VPS

- Ubuntu 22.04 ou Debian 12 (recomendado)
- Mínimo 2 vCPU, 4 GB RAM, 20 GB disco
- Domínio apontando para o IP da VPS (registro A no DNS)
- Portas 80 e 443 abertas no firewall

```bash
# Instalar Docker na VPS (se ainda não tiver)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose plugin
sudo apt-get install -y docker-compose-plugin
```

---

## Deploy na VPS — Passo a Passo

### 1. Clonar o repositório

```bash
git clone https://github.com/Roferale/lavapatrocina.git
cd lavapatrocina
```

### 2. Configurar o arquivo .env

```bash
cp .env.example .env
nano .env
```

Preencha obrigatoriamente:

| Variável | Como gerar | Exemplo |
|---|---|---|
| `DOMAIN` | Seu domínio | `meulavajato.com.br` |
| `POSTGRES_PASSWORD` | Invente uma senha forte | `xK9#mP2$vL` |
| `SECRET_KEY` | `openssl rand -hex 32` | `a1b2c3...` |
| `ENCRYPTION_KEY` | `openssl rand -hex 16` | `1234567890abcdef1234567890abcdef` |
| `NEXT_PUBLIC_API_URL` | `https://SEU_DOMINIO/api/v1` | `https://meulavajato.com.br/api/v1` |

> ⚠️ **ENCRYPTION_KEY deve ter exatamente 32 caracteres.**

### 3. Subir os serviços (HTTP primeiro)

```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

Isso sobe todos os serviços em HTTP. Acesse `http://SEU_DOMINIO` para confirmar que está funcionando.

### 4. Ativar HTTPS (Let's Encrypt)

> O DNS do domínio deve estar apontando para o IP da VPS antes deste passo.

```bash
./scripts/ssl-init.sh meulavajato.com.br admin@meulavajato.com.br
```

O script:
1. Obtém o certificado via Certbot
2. Ativa a configuração Nginx com HTTPS
3. Reinicia o Nginx

Após isso, acesse `https://SEU_DOMINIO`.

### 5. Primeiro acesso

```
URL:   https://SEU_DOMINIO
Login: admin@lava.local
Senha: admin123
```

> ⚠️ **Altere a senha padrão imediatamente após o primeiro login.**

---

## Como Cadastrar a Câmera

1. Acesse **Câmeras** → **Nova Câmera**
2. Preencha o nome e a URL RTSP da câmera
3. Clique **Testar Conexão** para validar antes de salvar
4. Salve a câmera

### Formatos de URL RTSP comuns

```bash
# Genérico
rtsp://usuario:senha@192.168.1.100:554/stream

# Intelbras
rtsp://admin:senha@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0

# Hikvision
rtsp://admin:senha@192.168.1.100:554/h264/ch1/main/av_stream

# Dahua
rtsp://admin:senha@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0

# Testar com VLC (no seu computador)
vlc rtsp://admin:senha@192.168.1.100:554/stream
```

> ⚠️ **Atenção VPS:** A câmera precisa ser acessível a partir da VPS.
> Se a câmera está na rede local do lava jato e a VPS é externa, o worker
> não conseguirá acessar o stream RTSP.
>
> **Solução:** Rode o worker localmente (no mini PC do lava jato) conectado
> ao mesmo banco PostgreSQL da VPS. Veja a seção "Worker Remoto" abaixo.

---

## Worker Remoto (câmera local + painel na nuvem)

Se a câmera está na rede local e o painel está na VPS, rode o worker localmente:

```bash
# No mini PC do lava jato
cd apps/worker
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://lava:SENHA@SEU_DOMINIO:5432/lavadb"
export ENCRYPTION_KEY="mesma_chave_do_env"
python -m worker.main
```

> Para isso, exponha a porta 5432 do PostgreSQL na VPS (edite `docker-compose.yml`
> e adicione `ports: - "5432:5432"` no serviço postgres, e libere no firewall).

---

## Como Configurar a Linha Virtual

1. Vá em **Câmeras** → clique em **Linha** na câmera desejada
2. Clique em **Capturar Frame** para carregar a imagem ao vivo
3. Clique em **Desenhar Linha** e clique em **dois pontos** na imagem
4. Escolha o sentido: **Entrada**, **Saída** ou **Ambos**
5. Selecione os tipos de veículo a detectar
6. Clique em **Salvar Linha**

**Dica:** Posicione a linha em uma área pela qual o carro obrigatoriamente passa,
não onde ele para. A entrada ou saída do lava jato é ideal.

---

## Como Validar a Contagem

1. Acesse o **Dashboard** — verifique o contador "Hoje"
2. Passe um carro pela câmera e aguarde alguns segundos
3. Verifique se o evento aparece em **Eventos** com sentido e tipo correto
4. Se necessário, ajuste a posição da linha ou a confiança mínima em **Configurações**

---

## Comandos Úteis

```bash
# Ver logs em tempo real
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f worker
docker compose logs -f backend

# Reiniciar um serviço
docker compose restart worker

# Parar tudo
docker compose down

# Atualizar (após git pull)
git pull
docker compose up -d --build
```

---

## Backup do Banco de Dados

```bash
./scripts/backup.sh
```

Backups são salvos em `./backups/` com timestamp. Os 10 mais recentes são mantidos.

Para restaurar:
```bash
docker compose exec -T postgres psql -U lava lavadb < backups/lava_backup_YYYYMMDD_HHMMSS.sql
```

---

## Estrutura do Projeto

```
lavapatrocina/
├── docker-compose.yml          # 6 serviços: postgres, backend, worker, frontend, nginx, certbot
├── .env.example                # Variáveis de ambiente documentadas
├── nginx/
│   └── conf.d/
│       ├── app.conf            # Config Nginx com HTTPS
│       └── app-nossl.conf      # Config HTTP temporária (antes do SSL)
├── scripts/
│   ├── deploy.sh               # Deploy completo na VPS
│   ├── ssl-init.sh             # Obtém certificado Let's Encrypt
│   └── backup.sh               # Backup do PostgreSQL
└── apps/
    ├── backend/                # FastAPI — API REST, autenticação, CRUD
    ├── worker/                 # Worker de processamento de vídeo (YOLO + ByteTrack)
    └── frontend/               # Next.js 14 — painel web em pt-BR
```

---

## Solução de Problemas

### O painel não abre
```bash
docker compose ps                    # verifica se todos os serviços estão Up
docker compose logs nginx            # erros de proxy
docker compose logs frontend         # erros do Next.js
curl http://localhost/health         # testa o backend direto
```

### Câmera não conecta
```bash
docker compose logs worker           # veja a mensagem de erro exata
# Teste a URL RTSP com VLC no computador onde a câmera está acessível
vlc rtsp://usuario:senha@IP:554/stream
```

### Worker não detecta veículos
- Verifique se a linha virtual está configurada (Câmeras → Linha)
- Confirme que o worker está rodando: `docker compose logs -f worker`
- Reduza a confiança mínima em Configurações (ex: 0.3)

### Certificado SSL não renova
```bash
docker compose logs certbot          # verifica renovações
docker compose restart certbot       # força verificação
```

### Como ver o uso de recursos
```bash
docker stats
```

---

## Segurança

- Credenciais RTSP são armazenadas com criptografia Fernet (AES-128)
- Senhas de usuários com bcrypt
- Tokens JWT com expiração configurável
- Nginx com HTTPS e headers de segurança
- Nenhuma imagem enviada para serviços externos
- O sistema roda inteiramente na sua infraestrutura

> O uso de câmeras para monitoramento deve respeitar a legislação vigente (LGPD)
> e as normas de privacidade aplicáveis ao seu município.
