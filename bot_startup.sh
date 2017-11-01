echo "Attempting to resolve Dashboard references..."
export MERAKI_DASHBOARD_MAP="`python3 meraki_dashboard_link_parser.py`"
echo "Beginning Umbrella Log Collection..."
python3 umbrella_log_collector.py &
echo "Launching Bot..."
python3 app.py