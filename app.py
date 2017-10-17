import os
from ciscosparkbot import SparkBot
import cico_meraki
import cico_spark_call
import cico_combined
import cico_common
import cico_umbrella
import sys

# Retrieve required details from environment variables
bot_email = os.getenv("SPARK_BOT_EMAIL")
spark_token = os.getenv("SPARK_BOT_TOKEN")
bot_url = os.getenv("SPARK_BOT_URL")
bot_app_name = os.getenv("SPARK_BOT_APP_NAME")

if not bot_email or not spark_token or not bot_url or not bot_app_name:
    print("Missing Environment Variable.")
    sys.exit()

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
bot.run(host='0.0.0.0', port=5000)