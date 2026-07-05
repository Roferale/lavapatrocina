#!/bin/bash
# =============================================================================
# deploy.sh — Deploy completo na VPS
#
# Uso: ./scripts/deploy.sh
# =============================================================================
set -e

echo "=== LavaJato — Deploy na VPS ==="
echo ""

# Verifica se .env existe
if [ ! -f .env ]; then
    echo "ERRO: Arquivo .env não encontrado."
    echo "Copie o .env.example e preencha as variáveis:"
    echo "  cp .env.example .env && nano .env"
    exit 1
fi

# Carrega variáveis do .env para validação
set -a; source .env; set +a

# Valida variáveis obrigatórias
ERRORS=0
for VAR in SECRET_KEY ENCRYPTION_KEY POSTGRES_PASSWORD DOMAIN; do
    if [ -z "${!VAR}" ]; then
        echo "ERRO: Variável $VAR não definida no .env"
        ERRORS=1
    fi
done

if [ "$ENCRYPTION_KEY" != "" ] && [ "${#ENCRYPTION_KEY}" -ne 32 ]; then
    echo "ERRO: ENCRYPTION_KEY deve ter exatamente 32 caracteres (tem ${#ENCRYPTION_KEY})"
    ERRORS=1
fi

if [ $ERRORS -ne 0 ]; then
    exit 1
fi

echo "✓ Variáveis de ambiente validadas"

# Cria diretório de configuração Nginx se não existir
mkdir -p nginx/conf.d nginx/certbot/conf nginx/certbot/www

# Se ainda não tem SSL configurado, usa HTTP simples
if [ ! -f nginx/conf.d/default.conf ]; then
    echo "Configurando Nginx HTTP (sem SSL ainda)..."
    cp nginx/conf.d/app-nossl.conf nginx/conf.d/default.conf
fi

# Build e sobe todos os serviços
echo "Fazendo build e subindo serviços..."
docker compose pull postgres nginx certbot
docker compose up -d --build

echo ""
echo "Aguardando serviços inicializarem..."
sleep 15

# Verifica se o backend respondeu
if curl -sf "http://localhost/api/v1" > /dev/null 2>&1 || \
   curl -sf "http://localhost/health" > /dev/null 2>&1; then
    echo "✓ Backend respondendo"
else
    echo "Aguardando mais um pouco..."
    sleep 15
fi

echo ""
echo "=== Deploy concluído! ==="
echo ""
echo "Acesse: http://$DOMAIN (ou https:// se já configurou SSL)"
echo ""
echo "Para ativar HTTPS, execute:"
echo "  ./scripts/ssl-init.sh $DOMAIN seu@email.com"
echo ""
echo "Logs:"
echo "  docker compose logs -f"
