#!/command/with-contenv sh
set -eu

echo "=================================="
echo "SchadenDienst24 - Trocknungsbericht"
echo "=================================="
echo "Berichtsanwendung wird gestartet..."

cd /app

exec python3 -u report.py
