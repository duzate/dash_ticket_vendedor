#!/bin/bash
# Script de Deploy para Dash Ticket Vendedor

echo "Configurando serviços systemd..."
systemctl daemon-reload

echo "Habilitando e iniciando Dashboard..."
systemctl enable dash-ticket.service
systemctl start dash-ticket.service

echo "Habilitando e iniciando Timer de ETL..."
systemctl enable dash-ticket-etl.timer
systemctl start dash-ticket-etl.timer

echo "Verificando status..."
systemctl is-active dash-ticket.service
systemctl list-timers dash-ticket-etl.timer

echo "✅ Deploy concluído!"
