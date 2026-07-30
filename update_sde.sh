#!/bin/bash
# EVE SDE Update Script
# Ensure we are in the script's directory
cd "$(dirname "$0")" || exit

echo "Activating virtual environment..."
source venv/bin/activate

echo "Updating EVE Online SDE..."
cd munbabb || exit
python manage.py eve_sde_update

echo "Done."
