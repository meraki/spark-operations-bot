import requests
import os
import json


a4e_client_id = os.getenv("A4E_CLIENT_ID")
a4e_client_secret = os.getenv("A4E_CLIENT_SECRET")
header = {"Accept-Encoding": "gzip"}


def get_a4e_events():
    # Get a list of all A4E events
    url = "https://api.amp.cisco.com/v1/events?event_type[]=1090519054&event_type[]=553648143&event_type[]=2164260880&event_type[]=553648145"
    evlist = requests.get(url, headers=header, auth=(a4e_client_id, a4e_client_secret))
    evjson = json.loads(evlist.content.decode("utf-8"))
    return evjson


def get_a4e_health(incoming_msg, rettype):
    # Get a list of all events
    evjson = get_a4e_events()
    totalevents = evjson["metadata"]["results"]["current_item_count"]

    processed_events = 0
    threat_detected_count = 0
    threat_quarantined_count = 0
    threat_quarantine_failed_count = 0
    threat_detected_excluded_count = 0
    erricon = ""

    retmsg = "<h3>AMP for Endpoints Details:</h3>"
    retmsg += "<a href='https://console.amp.cisco.com'>AMP for Endpoints Dashboard</a><br><ul>"
    for ev in evjson["data"]:
        if ev["event_type_id"] == 1090519054:
            threat_detected_count += 1
        elif ev["event_type_id"] == 553648143:
            threat_quarantined_count += 1
        elif ev["event_type_id"] == 2164260880:
            threat_quarantine_failed_count += 1
            erricon = chr(0x2757) + chr(0xFE0F)
        elif ev["event_type_id"] == 553648145:
            threat_detected_excluded_count += 1

        processed_events += 1
    retmsg += "<li><b>" + str(threat_detected_count) + " threat(s) detected. (" + str(threat_detected_excluded_count) + " in excluded locations.)</b></li>"
    # retmsg += "<li><b>" + str(threat_detected_excluded_count) + " threat(s) detected in excluded locations.</b></li>"
    retmsg += "<li><b>" + str(threat_quarantined_count) + " threat(s) quarantined.</b></li>"
    retmsg += "<li><b>" + str(threat_quarantine_failed_count) + " threat(s) quarantine failed.</b>" + erricon + "</li>"
    retmsg += "</ul>Processed " + str(processed_events) + " of " + str(totalevents) + " threat event(s)."

    return retmsg


def get_a4e_clients(incoming_msg, rettype):
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    evjson = get_a4e_events()
    totalevents = evjson["metadata"]["results"]["current_item_count"]

    processed_events = 0
    hostarr = {}
    erricon = ""

    for ev in evjson["data"]:
        compname = ev["computer"]["hostname"].upper()
        if compname not in hostarr:
            hostarr[compname] = {"threat_detected_count": 0, "threat_quarantined_count": 0, "threat_quarantine_failed_count": 0, "threat_detected_excluded_count": 0}

        if ev["event_type_id"] == 1090519054:
            hostarr[compname]["threat_detected_count"] += 1
        elif ev["event_type_id"] == 553648143:
            hostarr[compname]["threat_quarantined_count"] += 1
        elif ev["event_type_id"] == 2164260880:
            hostarr[compname]["threat_quarantine_failed_count"] += 1
            erricon = chr(0x2757) + chr(0xFE0F)
        elif ev["event_type_id"] == 553648145:
            hostarr[compname]["threat_detected_excluded_count"] += 1

        processed_events += 1

    if rettype == "json":
        return {"aggregate": {"total_events": totalevents, "processed_events": processed_events}, "clients": hostarr}
    else:
        retmsg = "<h3>AMP for Endpoints Stats:</h3><ul>"
        for cli in hostarr:
            if cli == client_id:
                retmsg += "<li><b>" + str(hostarr[cli]["threat_detected_count"]) + " threat(s) detected. (" + str(hostarr[cli]["threat_detected_excluded_count"]) + " in excluded locations.)</b></li>"
                retmsg += "<li><b>" + str(hostarr[cli]["threat_quarantined_count"]) + " threat(s) quarantined.</b></li>"
                retmsg += "<li><b>" + str(hostarr[cli]["threat_quarantine_failed_count"]) + " threat(s) quarantine failed." + erricon + "</b></li>"
        retmsg += "</ul>Processed " + str(processed_events) + " of " + str(totalevents) + " threat event(s)."

    return retmsg


def get_a4e_health_html(incoming_msg):
    return get_a4e_health(incoming_msg, "html")


def get_a4e_clients_html(incoming_msg):
    return get_a4e_clients(incoming_msg, "html")
