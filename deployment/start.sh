#!/bin/bash
# start.sh - Inicia a aplicação Dash Ticket Vendedor em produção
# Uso: bash start.sh

cd /home/sup/dash_ticket_vendedor

# Garantir que o container PostgreSQL está rodando
echo "[1/3] Subindo PostgreSQL DW..."
# Tentando com docker-compose (hífen) que foi instalado via apt
docker-compose -f deployment/docker-compose.yml up -d || sudo docker-compose -f deployment/docker-compose.yml up -d
sleep 3

# Parar qualquer instância anterior do supervisord
echo "[2/3] Parando processos anteriores..."
if [ -f logs/supervisord.pid ]; then
  PID=$(cat logs/supervisord.pid)
  kill $PID 2>/dev/null && echo "Instância anterior encerrada (PID $PID)"
  rm -f logs/supervisord.pid logs/supervisor.sock
fi

# Iniciar supervisord com toda a stack
echo "[3/3] Iniciando Gunicorn + ETL via supervisord..."
/home/sup/dash_ticket_vendedor/venv/bin/supervisord -c deployment/supervisord.conf

sleep 3
echo ""
echo "==========================================="
echo " ✅ Aplicação rodando em: http://192.168.0.110:8050"
echo "==========================================="
echo ""
echo "Logs disponíveis em:"
echo "  App:  tail -f /home/sup/dash_ticket_vendedor/gunicorn_err.log"
echo "  ETL:  tail -f /home/sup/dash_ticket_vendedor/etl_out.log"
