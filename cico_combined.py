import cico_meraki
import cico_spark_call
import cico_umbrella
import cico_common


def get_health(incoming_msg):
    retval = ""
    if cico_common.meraki_support():
        print("Meraki Support Enabled")
        retval += cico_meraki.get_meraki_health(incoming_msg, "html")
    if cico_common.spark_call_support():
        print("Spark Call Support Enabled")
        if retval != "":
            retval += "<br><br>"
        retval += cico_spark_call.get_spark_call_health(incoming_msg, "html")
    if cico_common.umbrella_support():
        print("Umbrella Support Enabled")
        if retval != "":
            retval += "<br><br>"
        retval += cico_umbrella.get_umbrella_health(incoming_msg, "html")

    return retval


def get_clients(incoming_msg):
    retm = ""
    retsc = ""
    retscn = ""
    retu = ""
    retmsg = ""
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    sclients = {}
    mclients = {}
    uclients = {}
    netlist = []
    newsmlist = []

    if cico_common.meraki_support():
        print("Meraki Support Enabled")
        # cico_spark_call.get_spark_call_clients_html(incoming_msg)
        mclients = cico_meraki.get_meraki_clients(incoming_msg, "json")
        netlist = mclients["client"]
        newsmlist = mclients["sm"]
    if cico_common.spark_call_support():
        print("Spark Call Support Enabled")
        # cico_meraki.get_meraki_clients_html(incoming_msg)
        sclients = cico_spark_call.get_spark_call_clients(incoming_msg, "json")
    if cico_common.umbrella_support():
        print("Umbrella Support Enabled")
        uclients = cico_umbrella.get_umbrella_clients(incoming_msg, "json")

    retm = "<h3>Associated Clients:</h3>"
    retsc = "<h3>Collaboration:</h3>"
    retsc += "<b>Phones:</b><br>"
    for net in sorted(netlist):
        for dev in netlist[net]["devices"]:
            for cli in netlist[net]["devices"][dev]["clients"]:
                if not isinstance(cli, str):
                    if cli["description"] == client_id and "switchport" in cli:
                        devbase = netlist[net]["devices"][dev]["info"]
                        showdev = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], devbase["name"], "?timespan=86400", 0)
                        showport = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], str(cli["switchport"]), "/ports/" + str(cli["switchport"]) + "?timespan=86400", 1)
                        showcli = cico_meraki.meraki_dashboard_client_mod(showdev, cli["id"], cli["dhcpHostname"])
                        retm += "<i>Computer Name:</i> " + showcli + "<br>"

                        if net in newsmlist:
                            if "devices" in newsmlist[net]:
                                if cli["mac"] in newsmlist[net]["devices"]:
                                    smbase = newsmlist[net]["devices"][cli["mac"]]
                                    retm += "<i>Model:</i> " + smbase["systemModel"] + "<br>"
                                    retm += "<i>OS:</i> " + smbase["osName"] + "<br>"

                        retm += "<i>IP:</i> " + cli["ip"] + "<br>"
                        retm += "<i>MAC:</i> " + cli["mac"] + "<br>"
                        retm += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                        devbase = netlist[net]["devices"][dev]["info"]
                        retm += "<i>Connected To:</i> " + showdev + " (" + devbase["model"] + "), Port " + showport + "<br>"
                    elif "phones" in sclients and cli["mac"] in sclients["phones"] and "switchport" in cli:
                        devbase = netlist[net]["devices"][dev]["info"]
                        showdev = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], devbase["name"], "?timespan=86400", 0)
                        showport = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], str(cli["switchport"]), "/ports/" + str(cli["switchport"]) + "?timespan=86400", 1)
                        showcli = cico_meraki.meraki_dashboard_client_mod(showdev, cli["id"], cli["dhcpHostname"])

                        scbase = sclients["phones"][cli["mac"]]
                        retsc += scbase["description"] + " (<i>" + scbase["registrationStatus"] + "</i>)<br>"
                        retsc += "<i>Device Name:</i> " + showcli + "<br>"
                        retsc += "<i>IP:</i> " + cli["ip"] + "<br>"
                        retsc += "<i>MAC:</i> " + cli["mac"] + "<br>"
                        retsc += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                        retsc += "<i>Connected To:</i> " + showdev + " (" + devbase["model"] + "), Port " + showport + "<br>"

    retscn = ""
    if "numbers" in sclients:
        for n in sclients["numbers"]:
            num = sclients["numbers"][n]
            retscn = "<b>Numbers:</b><br>"
            if "external" in num:
                retscn += num["external"] + " (x" + num["internal"] + ")\n"
            else:
                retscn += "Extension " + num["internal"] + "<br>"

    retu = "<h3>Umbrella Client Stats (Last 24 hours):</h3><ul>"
    if "Aggregate" in uclients:
        retu += "<li>Total Requests: " + str(uclients["Aggregate"]["Total"]) + "</li>"
        for x in uclients["Aggregate"]:
            if x != "Total":
                retu += "<li>" + x + ": " + str(uclients["Aggregate"][x]) + " (" + str(round(uclients["Aggregate"][x] / uclients["Aggregate"]["Total"] * 100, 2)) + "%)</li>"
        retu += "</ul></b>"

        if len(uclients["Blocked"]) > 0:
            retu += "<h4>Last 5 Blocked Requests:</h4><ul>"

            for x in uclients["Blocked"]:
                retu += "<li>" + x["Timestamp"] + " " + x["Domain"] + " " + x["Categories"] + "</li>"

            retu += "</ul>"
    else:
        retu += "<li>No stats available for this user.</li></ul>"

    if cico_common.meraki_support():
        retmsg += retm
        if cico_common.umbrella_support() or cico_common.spark_call_support():
            retmsg += "<hr>"
    if cico_common.umbrella_support():
        retmsg += retu
        if cico_common.spark_call_support():
            retmsg += "<hr>"
    if cico_common.spark_call_support():
        retmsg += retsc + "<br>" + retscn

    return retmsg
