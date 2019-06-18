'''
    This module is specifically for interoperability between the various individual modules. Any generic product code
    should be placed into a product specific module, and any relevant integration should be added here.
'''
import os
import cico_meraki
import cico_spark_call
import cico_umbrella
import cico_a4e
import cico_common

# ========================================================
# Load required parameters from environment variables
# ========================================================

meraki_client_to = os.getenv("MERAKI_CLIENT_TIMESPAN")
if not meraki_client_to:
    meraki_client_to = "86400"


# ========================================================
# Initialize Program - Function Definitions
# ========================================================


def get_health(incoming_msg):
    '''
    This function is used to consolidate Health information from all of the individual product modules

    :param incoming_msg: String. this is the message that is posted in Spark
    :return: String. this is a fully formatted string that will be sent back to Spark
    '''
    retval = ""

    # If Meraki environment variables have been enabled, retrieve Meraki health information
    if cico_common.meraki_support():
        print("Meraki Support Enabled")
        retval += cico_meraki.get_meraki_health(incoming_msg, "html")
    # If Spark Call environment variables have been enabled, retrieve Spark Call health information
    if cico_common.spark_call_support():
        print("Spark Call Support Enabled")
        if retval != "":
            retval += "<br><br>"
        retval += cico_spark_call.get_spark_call_health(incoming_msg, "html")
    # If Umbrella (S3) environment variables have been enabled, retrieve Umbrella health information
    if cico_common.umbrella_support():
        print("Umbrella Support Enabled")
        if retval != "":
            retval += "<br><br>"
        retval += cico_umbrella.get_umbrella_health(incoming_msg, "html")
    if cico_common.a4e_support():
        if retval != "":
            retval += ""
        retval += cico_a4e.get_a4e_health(incoming_msg, "html")

    return retval


def get_clients(incoming_msg):
    '''
    This function is used to consolidate Client information from all of the individual product modules

    :param incoming_msg: this is the message that is posted in Spark
    :return: this is a fully formatted string that will be sent back to Spark
    '''

    # initialize variables
    retm = ""
    retsc = ""
    retscn = ""
    retu = ""
    retmsg = ""
    devcount = 0

    sclients = {}
    mclients = {}
    uclients = {}
    aclients = {}
    netlist = []
    newsmlist = []
    smnetid = ""

    # Parse incoming message in order to retrieve the username of the client
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    # If Meraki environment variables have been enabled, retrieve Meraki client information
    if cico_common.meraki_support():
        print("Meraki Support Enabled")
        # cico_spark_call.get_spark_call_clients_html(incoming_msg)
        mclients = cico_meraki.get_meraki_clients(incoming_msg, "json")
        netlist = mclients["client"]            # Dashboard Clients
        newsmlist = mclients["sm"]              # Systems Manager Clients
        smnetid = mclients["smnetid"]        # Systems Manager Clients
    # If Spark Call environment variables have been enabled, retrieve Spark Call client information
    if cico_common.spark_call_support():
        print("Spark Call Support Enabled")
        # cico_meraki.get_meraki_clients_html(incoming_msg)
        sclients = cico_spark_call.get_spark_call_clients(incoming_msg, "json")
    # If Umbrella (S3) environment variables have been enabled, retrieve Umbrella client information
    if cico_common.umbrella_support():
        print("Umbrella Support Enabled")
        uclients = cico_umbrella.get_umbrella_clients(incoming_msg, "json")
    # If Amp for Endpoints environment variables have been enabled, retrieve A4E client information
    if cico_common.a4e_support():
        print("Amp for Endpoints Support Enabled")
        aclients = cico_a4e.get_a4e_clients(incoming_msg, "json")

    # Initialize individual product return strings
    retm = "<h3>Associated Clients:</h3>"
    retsc = "<h3>Collaboration:</h3>"
    retsc += "<b>Phones:</b>"

    if netlist:
        # netlist is a list of all Meraki Networks in the supplied or derived organization. Iterate these, sorted by name.
        for net in sorted(netlist):
            # netlist[net]["devices"] represents a list of devices in the individual network that is being iterated.
            for dev in netlist[net]["devices"]:
                # netlist[net]["devices"][dev]["clients"] represents a list of clients attached to a specific device that
                # is being iterated.
                for cli in netlist[net]["devices"][dev]["clients"]:
                    # The client should not be a string. If it is for some reason, do not process it.
                    if not isinstance(cli, str):
                        # If the description of the client matches the username specified in Spark, and if this specific
                        # client has a switchport mapping, then continue (duplicate clients from MX security appliances
                        # will also be in this list, the switchport check is used to exclude those)
                        if cli["description"] == client_id and "switchport" in cli and cli["switchport"] is not None:
                            devbase = netlist[net]["devices"][dev]["info"]
                            # These functions generate the cross-launch links (if available) for the given
                            # client/device/port
                            showdev = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], devbase["name"], "?timespan=" + meraki_client_to, 0)
                            showport = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], str(cli["switchport"]), "/ports/" + str(cli["switchport"]) + "?timespan=" + meraki_client_to, 1)
                            showcli = cico_meraki.meraki_dashboard_client_mod(showdev, cli["id"], cli["dhcpHostname"])
                            if devcount > 0:
                                retm += "<br>"
                            devcount += 1
                            retm += "<i>Computer Name:</i> " + showcli + "<br>"

                            # Iterate the Systems Manager list to see if the client exists there. Iterate through networks.
                            if net in newsmlist:
                                # If this network has any devices, then we will attempt to cross reference the client data
                                if "devices" in newsmlist[net]:
                                    # Our cross-reference point is mac address, as it will exist in both the dashboard
                                    # clients list as well as the systems manager clients list.
                                    if cli["mac"] in newsmlist[net]["devices"]:
                                        # If we are able to cross-reference, we will add some system-specific and
                                        # OS-specific details from SM
                                        smbase = newsmlist[net]["devices"][cli["mac"]]
                                        retm += "<i>Model:</i> " + smbase["systemModel"] + "<br>"
                                        retm += "<i>OS:</i> " + smbase["osName"] + "<br>"

                            # Once we've checked for Systems Manager cross references, we will display the rest of the
                            # client details
                            retm += "<i>IP:</i> " + cli["ip"] + "<br>"
                            retm += "<i>MAC:</i> " + cli["mac"] + "<br>"
                            retm += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                            # This creates the description of the switch / port the client is connected to
                            # --duplicate-- devbase = netlist[net]["devices"][dev]["info"]
                            retm += "<i>Connected To:</i> " + showdev + " (" + devbase["model"] + "), Port " + showport + "<br>"

                            # Now, check to see if there is cooresponding Amp for Endpoints data...
                            if cico_common.a4e_support():
                                if any(cli["dhcpHostname"] in s for s in aclients["clients"]):
                                    retm += "<h3>AMP for Endpoints Stats:</h3><ul>"
                                    for acli in aclients["clients"]:
                                        if "." in acli:
                                            ahostname = acli.split(".")[0]
                                        else:
                                            ahostname = acli

                                        if ahostname == cli["dhcpHostname"]:
                                            retm += "<li><b>" + str(aclients["clients"][acli]["threat_detected_count"]) + " threat(s) detected. (" + str(aclients["clients"][acli]["threat_detected_excluded_count"]) + " in excluded locations.)</b></li>"
                                            retm += "<li><b>" + str(aclients["clients"][acli]["threat_quarantined_count"]) + " threat(s) quarantined.</b></li>"
                                            if aclients["clients"][acli]["threat_quarantine_failed_count"] > 0:
                                                erricon = chr(0x2757) + chr(0xFE0F)
                                            else:
                                                erricon = ""
                                            retm += "<li><b>" + str(aclients["clients"][acli]["threat_quarantine_failed_count"]) + " threat(s) quarantine failed." + erricon + "</b></li>"
                                        retm += "</ul>Processed " + str(aclients["aggregate"]["processed_events"]) + " of " + str(aclients["aggregate"]["total_events"]) + " threat event(s)."
                                else:
                                    retmsg += "<h3>AMP for Endpoints Stats:</h3><ul>"
                                    retmsg += "<li>No stats available for this user.</li></ul>"

                        # Here, we will also check to see if there is a phone associated to this user. If so, we will
                        # follow a similar process to determine where the phone is connected and get client details for it.
                        # If there are phones available, and if the mac address of the client being reviewed currently is
                        # one of the devices in that list, and if there is a switchport field (again to eliminate
                        # duplicate MX entries), then we will provide additional information for the phone.
                        elif "phones" in sclients and cli["mac"] in sclients["phones"] and "switchport" in cli and cli["switchport"] is not None:
                            devbase = netlist[net]["devices"][dev]["info"]
                            # These functions generate the cross-launch links (if available) for the given
                            # client/device/port
                            showdev = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], devbase["name"], "?timespan=" + meraki_client_to, 0)
                            showport = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], str(cli["switchport"]), "/ports/" + str(cli["switchport"]) + "?timespan=" + meraki_client_to, 1)
                            showcli = cico_meraki.meraki_dashboard_client_mod(showdev, cli["id"], cli["dhcpHostname"])

                            # No Systems Manager references here, but we will add the cross-referened data for the phone
                            # itself, like it's mac address, description, and whether it is registered.
                            scbase = sclients["phones"][cli["mac"]]
                            retsc += "<br>" + scbase["description"] + " (<i>" + scbase["registrationStatus"] + "</i>)<br>"
                            retsc += "<i>Device Name:</i> " + showcli + "<br>"
                            retsc += "<i>IP:</i> " + cli["ip"] + "<br>"
                            retsc += "<i>MAC:</i> " + cli["mac"] + "<br>"
                            retsc += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                            # This creates the description of the switch / port the client is connected to
                            retsc += "<i>Connected To:</i> " + showdev + " (" + devbase["model"] + "), Port " + showport + "<br>"
    elif newsmlist:
        for cli in newsmlist[smnetid]["devices"]:
            smbase = newsmlist[smnetid]["devices"][cli]
            if client_id.lower() in smbase["name"].lower() or client_id.lower() in [x.lower() for x in smbase["tags"]]:
                if devcount > 0:
                    retm += "<br>"
                devcount += 1
                retm += "<i>Client Name:</i> " + smbase["name"] + "<br>"
                retm += "<i>Model:</i> " + smbase["systemModel"] + "<br>"
                retm += "<i>OS:</i> " + smbase["osName"] + "<br>"
                retm += "<i>MAC:</i> " + smbase["wifiMac"] + "<br>"
                smssid = smbase["ssid"]
                if smssid is None:
                    smssid = "N/A"
                retm += "<i>Wireless SSID:</i> " + smssid + "<br>"

    # If there are phone numbers defined in the Spark Call clients list, we want to add that to the output as well.
    if "numbers" in sclients:
        # There could potentially be multiple numbers, so iterate the list...
        for n in sclients["numbers"]:
            num = sclients["numbers"][n]
            retscn = "<b>Numbers:</b><br>"
            # There are also internal and external numbers. Format this data for output based on what is available...
            if "external" in num:
                retscn += num["external"] + " (x" + num["internal"] + ")\n"
            else:
                retscn += "Extension " + num["internal"] + "<br>"

    # If there are stats in the Umbrella data, we want to add that to the output
    retu = "<h3>Umbrella Client Stats (Last 24 hours):</h3><ul>"
    if "Aggregate" in uclients:
        # This prints the aggregate statistics for this specific client
        retu += "<li>Total Requests: " + str(uclients["Aggregate"]["Total"]) + "</li>"
        # This prints the malicious and non-malicious stats for the traffic for this client
        for x in uclients["Aggregate"]:
            if x != "Total":
                retu += "<li>" + x + ": " + str(uclients["Aggregate"][x]) + " (" + str(round(uclients["Aggregate"][x] / uclients["Aggregate"]["Total"] * 100, 2)) + "%)</li>"
        retu += "</ul></b>"

        # If there is malicious traffic, we want to display the last 5 blocked requests
        if len(uclients["Blocked"]) > 0:
            retu += "<h4>Last 5 Blocked Requests:</h4><ul>"

            # Iterate the list of blocked sites, and add that to the output
            for x in uclients["Blocked"]:
                retu += "<li>" + x["Timestamp"] + " " + x["Domain"] + " " + x["Categories"] + "</li>"

            retu += "</ul>"
    else:
        retu += "<li>No stats available for this user.</li></ul>"

    # If Meraki environment variables have been enabled, add Meraki client information to the output
    if cico_common.meraki_support():
        retmsg += retm
        # If we expect more data, add a line (<hr>) to the output to make it more readable
        if cico_common.umbrella_support() or cico_common.spark_call_support():
            retmsg += "<hr>"
    # If Umbrella (S3) environment variables have been enabled, add Umbrella client information to the output
    if cico_common.umbrella_support():
        retmsg += retu
        # If we expect more data, add a line (<hr>) to the output to make it more readable
        if cico_common.spark_call_support():
            retmsg += "<hr>"
    # If Spark Call environment variables have been enabled, add Spark Call client information to the output
    if cico_common.spark_call_support():
        retmsg += retsc + "<br>" + retscn

    return retmsg
