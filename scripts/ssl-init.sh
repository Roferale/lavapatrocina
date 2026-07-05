#!/bin/bash
# =============================================================================
# ssl-init.sh — Obtém o primeiro certificado Let's Encrypt para o domínio
#
# Uso: ./scripts/ssl-init.sh seudominio.com email@exemplo.com
# =============================================================================
set -e

DOMAIN=${1:-""}
EMAIL=${2:-""}

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Uso: ./scripts/ssl-init.sh <domínio> <email>"
    echo "Exemplo: ./scripts/ssl-init.sh meulavajato.com.br admin@meulavajato.com.br"
    exit 1
fi

echo "=== Configurando SSL para $DOMAIN ==="

# 1. Garante que o .env tem o domínio
if grep -q "^DOMAIN=" .env 2>/dev/null; then
    sed -i "s|^DOMAIN=.*|DOMAIN=$DOMAIN|" .env
else
    echo "DOMAIN=$DOMAIN" >> .env
fi

# 2. Configura o Nginx temporariamente sem SSL (apenas HTTP) para o desafio ACME
echo "Ativando configuração HTTP temporária..."
cp nginx/conf.d/app-http.conf.template nginx/conf.d/default.conf

# 3. Cria diretórios necessários
mkdir -p nginx/certbot/conf nginx/certbot/www

# 4. Baixa parâmetros recomendados do Let's Encrypt se ainda não existirem
if [ ! -f "nginx/certbot/conf/options-ssl-nginx.conf" ]; then
    echo "Baixando parâmetros SSL recomendados..."
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
        > nginx/certbot/conf/options-ssl-nginx.conf
    openssl dhparam -out nginx/certbot/conf/ssl-dhparams.pem 2048 2>/dev/null
fi

# 5. Sobe apenas o Nginx (sem SSL ainda)
echo "Subindo Nginx temporário..."
docker compose up -d nginx

# 6. Obtém o certificado
echo "Solicitando certificado para $DOMAIN..."
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# 7. Ativa a configuração HTTPS definitiva
echo "Ativando configuração HTTPS..."
sed "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx/conf.d/app-ssl.conf.template > nginx/conf.d/default.conf

# 8. Reinicia o Nginx com SSL
docker compose restart nginx

echo ""
echo "=== SSL configurado com sucesso! ==="
echo "Acesse: https://$DOMAIN"
