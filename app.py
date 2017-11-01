import os
from ciscosparkbot import SparkBot
import cico_meraki
import cico_spark_call
import cico_combined
import cico_common
import cico_umbrella
import sys
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import umbrella_log_collector
import meraki_dashboard_link_parser

# Retrieve required details from environment variables
app_port = os.getenv("PORT")
if not app_port:
    app_port = 5000
else:
    app_port = int(app_port)

bot_email = os.getenv("SPARK_BOT_EMAIL")
spark_token = os.getenv("SPARK_BOT_TOKEN")
bot_url = os.getenv("SPARK_BOT_URL")
bot_app_name = os.getenv("SPARK_BOT_APP_NAME")

if not bot_email or not spark_token or not bot_url or not bot_app_name:
    print("app.py - Missing Environment Variable.")
    sys.exit()


def job_function():
    umbrella_log_collector.get_logs()


if cico_common.meraki_dashboard_support():
    print("Attempting to resolve Dashboard references...")
    cico_meraki.meraki_dashboard_map = meraki_dashboard_link_parser.get_meraki_http_info()
else:
    cico_meraki.meraki_dashboard_map = None


if cico_common.umbrella_support():
    cron = BackgroundScheduler()

    # Explicitly kick off the background thread
    cron.start()
    job = cron.add_job(job_function, 'interval', minutes=5)
    print("Beginning Umbrella Log Collection...")
    job_function()

    # Shutdown your cron thread if the web process is stopped
    atexit.register(lambda: cron.shutdown(wait=False))

# Create a new bot
bot = SparkBot(bot_app_name, spark_bot_token=spark_token,
               spark_bot_url=bot_url, spark_bot_email=bot_email, debug=True)

# Add new command
if cico_common.meraki_support():
    bot.add_command('/meraki-health', 'Get health of Meraki environment.', cico_meraki.get_meraki_health_html)
    bot.add_command('/meraki-check', 'Check Meraki user status.', cico_meraki.get_meraki_clients_html)
if cico_common.spark_call_support():
    bot.add_command('/spark-health', 'Get health of Spark environment.', cico_spark_call.get_spark_call_health_html)
    bot.add_command('/spark-check', 'Check Spark user status.', cico_spark_call.get_spark_call_clients_html)
if cico_common.umbrella_support():
    bot.add_command('/umbrella-health', 'Get health of Umbrella envrionment.', cico_umbrella.get_umbrella_health_html)
    bot.add_command('/umbrella-check', 'Check Umbrella user status.', cico_umbrella.get_umbrella_clients_html)
bot.add_command('/health', 'Get health of entire environment.', cico_combined.get_health)
bot.add_command('/check', 'Get user status.', cico_combined.get_clients)

# Run Bot
bot.run(host='0.0.0.0', port=app_port)