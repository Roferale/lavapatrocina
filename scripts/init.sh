#!/bin/bash
set -e

echo "=== LavaJato - Sistema de Contagem de Veículos ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Criando arquivo .env a partir do exemplo..."
    cp .env.example .env
    echo "AVISO: Arquivo .env criado com valores padrão. Edite-o antes de usar em produção!"
    echo ""
fi

echo "Iniciando serviços com Docker Compose..."
docker compose up -d --build

echo ""
echo "Aguardando o banco de dados ficar disponível..."
sleep 10

echo ""
echo "=== Sistema iniciado com sucesso! ==="
echo ""
echo "Acesse o painel em: http://localhost:3000"
echo "API disponível em: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Login padrão:"
echo "  E-mail: admin@lava.local"
echo "  Senha:  admin123"
echo ""
echo "IMPORTANTE: Altere a senha padrão após o primeiro acesso!"
