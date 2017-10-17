import base64
import requests
import json
import os
import sys


spark_api_token = os.getenv("SPARK_API_TOKEN")
if not spark_api_token:
    print("Missing Environment Variable.")
    sys.exit()

header = {
    'Authorization': "Bearer " + spark_api_token
}


def decode_base64(data):
    """Decode base64, padding being optional.
    http://stackoverflow.com/questions/2941995/python-ignore-incorrect-padding-error-when-base64-decoding

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += b'=' * (4 - missing_padding)
    return base64.b64decode(data)


def spark_call_get_org():
    url = "https://api.ciscospark.com/v1/people/me"

    r = requests.request("GET", url, headers=header)
    try:
        rjson = json.loads(r.content.decode("utf-8"))
        if "error" in rjson:
            return "Error. Server returned message with error code '" + rjson['error']['key'] + " - " + rjson['error']['message']
    except:
        return "Error. Server returned '" + str(r.status_code) + " - " + r.reason

    if "orgId" in rjson:
        orgid = rjson["orgId"]
        orguuid = decode_base64(orgid.encode("utf-8")).decode("utf-8")
        orguuid = orguuid.replace("ciscospark://us/ORGANIZATION/", "")
    else:
        orguuid = ""

    return orguuid


def spark_api_get_dev_status_report():
    orgid = spark_call_get_org()
    if orgid == "":
        return ["Error. No orgid found."]

    url = "https://cmi.huron-dev.com/api/v2/customers/" + orgid + "/users?wide=true"

    r = requests.request("GET", url, headers=header)
    try:
        rjson = json.loads(r.content.decode("utf-8"))
        if "error" in rjson:
            return "Error. Server returned message with error code '" + rjson['error']['key'] + " - " + rjson['error']['message']
    except:
        return "Error. Server returned '" + str(r.status_code) + " - " + r.reason

    dev_mod_arr = {}
    dev_tot = 0
    dev_off = 0

    for u in rjson["users"]:
        if "phones" in u:
            for d in u["phones"]:
                dev_tot += 1
                dev_model = d["description"]
                dev_reg = d["registrationStatus"]
                if dev_reg != "Registered":
                    dev_offline = 1
                    dev_off += 1
                else:
                    dev_offline = 0

                if dev_model in dev_mod_arr:
                    dev_mod_arr[dev_model]["num"] += 1
                    if dev_offline == 1:
                        dev_mod_arr[dev_model]["offline"] += 1
                else:
                    dev_mod_arr[dev_model] = {"num": 1, "offline": dev_offline}

    dev_mod_arr["Total"] = {"offline": dev_off, "num": dev_tot}

    return dev_mod_arr


def spark_call_search_user(username):
    orgid = spark_call_get_org()
    if orgid == "":
        return ["Error. No orgid found."]

    url = "https://identity.webex.com/identity/scim/" + orgid + "/v1/Users?filter=active%20eq%20true%20and%20(userName%20sw%20%22" + username + "%22%20or%20name.givenName%20sw%20%22" + username + "%22%20or%20name.familyName%20sw%20%22" + username + "%22%20or%20displayName%20sw%20%22" + username + "%22)&attributes=name,userName,userStatus,entitlements,displayName,photos,roles,active,trainSiteNames,licenseID,userSettings&count=100&sortBy=name&sortOrder=ascending"

    r = requests.request("GET", url, headers=header)
    try:
        rjson = json.loads(r.content.decode("utf-8"))
        if "error" in rjson:
            return ["Error. Server returned message with error code '" + rjson['error']['key'] + " - " + rjson['error']['message']]
    except:
        return ["Error. Server returned '" + str(r.status_code) + " - " + r.reason]

    uidlist = []
    if "Resources" in rjson:
        tr = rjson["Resources"]
        for rj in tr:
            uidlist.append(rj["id"])

    return uidlist


def spark_call_get_user_info(userid):
    orgid = spark_call_get_org()
    if orgid == "":
        return ["Error. No orgid found."]

    url = "https://cmi.huron-dev.com/api/v2/customers/" + orgid + "/users/" + userid + "?wide=true"

    r = requests.request("GET", url, headers=header)
    try:
        rjson = json.loads(r.content.decode("utf-8"))
        if "error" in rjson:
            return {"html": "", "text": "", "error": "Error. Server returned message with error code '" + rjson['error']['key'] + " - " + rjson['error']['message']}
    except:
        return {"html": "", "text": "", "error": "Error. Server returned '" + str(r.status_code) + " - " + r.reason}

    numlist = []
    devlist = []
    retjson = {}

    if "phones" in rjson:
        retjson["phones"] = {}
        for dev in rjson["phones"]:
            devlist.append(dev["description"] + " [" + dev["registrationStatus"] + "]")

            if dev["mac"] not in retjson["phones"]:
                retjson["phones"][dev["mac"]] = {}
            retjson["phones"][dev["mac"]]["description"] = dev["description"]
            retjson["phones"][dev["mac"]]["registrationStatus"] = dev["registrationStatus"]
            retjson["phones"][dev["mac"]]["ipAddress"] = dev.get("ipAddress", "N/A")
            retjson["phones"][dev["mac"]]["mac"] = dev["mac"]

    if "numbers" in rjson:
        retjson["numbers"] = {}
        for num in rjson["numbers"]:
            if num["internal"] not in retjson["numbers"]:
                retjson["numbers"][num["internal"]] = {}
            retjson["numbers"][num["internal"]]["internal"] = num["internal"]

            if num["external"] is None:
                numlist.append("Extension " + num["internal"])
            else:
                numlist.append(num["external"] + " (x" + num["internal"] + ")")
                retjson["numbers"][num["internal"]]["external"] = num["external"]

    return retjson


def get_spark_call_health(incoming_msg, rettype):
    spark_data = spark_api_get_dev_status_report()

    if rettype == "json":
        return spark_data
    else:
        retstr = "<h3>Spark Details:</h3>"
        retstr += "<a href='https://admin.ciscospark.com'>Spark Dashboard</a><br><ul>"

        for d in sorted(spark_data):
            if d.find("Cisco") >= 0:
                if spark_data[d]["offline"] > 0:
                    devicon = chr(0x2757) + chr(0xFE0F)
                else:
                    devicon = ""

                retstr += "<li>" + str(spark_data[d]["offline"]) + " offline out of " + str(spark_data[d]["num"]) + " " + d + "(s)." + devicon + "</li>"
        retstr += "</ul><strong>" + str(spark_data["Total"]["offline"]) + " phone(s) offline out of a total of " + str(spark_data["Total"]["num"]) + " phone(s).</strong>"

        return retstr


def get_spark_call_clients(incoming_msg, rettype):
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    userdata = {"html": "", "json": {}}
    userinfo = spark_call_search_user(client_id)
    for u in userinfo:
        userdata = spark_call_get_user_info(u)

    if rettype == "json":
        return userdata
    else:
        retval = "<h3>Collaboration:</h3>"
        retval += "<strong>Phones:</strong><br>"
        for d in userdata["phones"]:
            dev = userdata["phones"][d]
            retval += dev["description"] + " [<em>" + dev["registrationStatus"] + "</em>]<br>"
            retval += "<i>IP:</i> " + dev.get("ipAddress", "N/A") + "<br>"
            retval += "<i>MAC:</i> " + dev["mac"] + "<br>"

        for n in userdata["numbers"]:
            num = userdata["numbers"][n]
            retval += "<br><strong>Numbers:</strong><br>"
            if "external" in num:
                retval += num["external"] + " (x" + num["internal"] + ")\n"
            else:
                retval += "Extension " + num["internal"] + "<br>"

        return retval


def get_spark_call_health_html(incoming_msg):
    return get_spark_call_health(incoming_msg, "html")


def get_spark_call_clients_html(incoming_msg):
    return get_spark_call_clients(incoming_msg, "html")
