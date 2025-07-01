#!/bin/bash

# Kill any existing instances
pkill -f "python.*server_fixed.py" || true
pkill -f "cloudflared.*troupexbot-config.yml" || true

sleep 2

# Start the server
echo "Starting Gemma 2 server..."
cd /home/hardik/test/TroupeBot-v3
source venv/bin/activate
nohup python server_fixed.py > /home/hardik/test/TroupeBot-v3/server_production.log 2>&1 &

echo "Waiting for server to start..."
sleep 5

# Start the cloudflare tunnel
echo "Starting Cloudflare tunnel..."
nohup /usr/local/bin/cloudflared tunnel --config /home/hardik/.cloudflared/troupexbot-config.yml run > /home/hardik/test/TroupeBot-v3/tunnel_production.log 2>&1 &

echo "Services started!"
echo "Server log: /home/hardik/test/TroupeBot-v3/server_production.log"
echo "Tunnel log: /home/hardik/test/TroupeBot-v3/tunnel_production.log"
echo ""
echo "After adding the DNS CNAME record, access at: https://troupexbot.materiallab.io"
echo ""
echo "DNS Record needed:"
echo "  Type: CNAME"
echo "  Name: troupexbot"
echo "  Target: 36277c2b-3618-4413-9e15-a4bf75ee251f.cfargotunnel.com"