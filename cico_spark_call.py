'''
    This module is specifically for Spark Call-related operations. This is for the Spark Call API.
'''

import base64
import requests
import json
import os

# ========================================================
# Load required parameters from environment variables
# ========================================================

spark_api_token = os.getenv("SPARK_API_TOKEN")
spark_over_dash = os.getenv("SPARK_OVERRIDE_DASHBOARD")
if not spark_api_token:
    print("cico_spark_call.py - Missing Environment Variable.")
    if not spark_api_token:
        print("SPARK_API_TOKEN")
    header = {}
else:
    header = {
        'Authorization': "Bearer " + spark_api_token
    }

# ========================================================
# Initialize Program - Function Definitions
# ========================================================


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
    '''
    This function will retrieve the user details for the specified user's token. The Organization that the user belongs
    to is part of what is returned. This is returned as a encoded value, so we will base64 decode that and extract the
    UUID as well.

    :return: UUID of the organization associated with the specified user's token.
    '''

    url = "https://api.ciscospark.com/v1/people/me"

    r = requests.request("GET", url, headers=header)
    try:
        rjson = json.loads(r.content.decode("utf-8"))
        if "error" in rjson:
            return "Error. Server returned message with error code '" + rjson['error']['key'] + " - " + rjson['error']['message']
    except:
        return "Error. Server returned '" + str(r.status_code) + " - " + r.reason

    # Retrieve orgId from Dictionary
    if "orgId" in rjson:
        orgid = rjson["orgId"]
        # Base64 Decode and strip the header to get the UUID
        orguuid = decode_base64(orgid.encode("utf-8")).decode("utf-8")
        orguuid = orguuid.replace("ciscospark://us/ORGANIZATION/", "")
    else:
        orguuid = ""

    return orguuid


def spark_api_get_dev_status_report():
    '''
    This function calls an undocumented API to get a list of all devices in the Organization.

    :return: Dictionary. Dict of all devices in the org.
    '''

    # Start by getting the organization UUID
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

    # rjson["users"] is a list of all users in the organization. Iterate the users
    for u in rjson["users"]:
        # Make sure the user has one or more phones.
        if "phones" in u:
            # u["phones"] is a list of all phones for the user. Iterate the phones.
            for d in u["phones"]:
                # Increment total number of phones and get information for this phone
                dev_tot += 1
                dev_desc = d["description"]
                if dev_desc.find("(") >= 0:
                    dev_model = dev_desc[dev_desc.find("(")+1:dev_desc.find(")")]
                    dev_model = dev_model.replace(" SIP", "")
                else:
                    dev_model = dev_desc
                dev_reg = d["registrationStatus"]
                # If the phone isn't registered, tag the offline attribute, and increment the offline counter as well
                if dev_reg != "Registered":
                    dev_offline = 1
                    dev_off += 1
                else:
                    dev_offline = 0

                # We will also create a catalog of devices, and how many total / offline devices of that type are
                # present
                if dev_model in dev_mod_arr:
                    dev_mod_arr[dev_model]["num"] += 1
                    if dev_offline == 1:
                        dev_mod_arr[dev_model]["offline"] += 1
                else:
                    dev_mod_arr[dev_model] = {"num": 1, "offline": dev_offline}

    dev_mod_arr["Total"] = {"offline": dev_off, "num": dev_tot}

    return dev_mod_arr


def spark_call_search_user(username):
    '''
    This function calls an undocumented API to search for a specific user in the organization

    :param username: String. The username to search for
    :return: List. List of all user IDs that match the search.
    '''

    # Start by getting the organization UUID
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
    # rjson["Resources"] is a list of results from the search
    if "Resources" in rjson:
        tr = rjson["Resources"]
        # Iterate list of results, and append the userid to the output list.
        for rj in tr:
            uidlist.append(rj["id"])

    return uidlist


def spark_call_get_user_info(userid):
    '''
    This function calls an undocumented API to get details about a specific userid in an organization

    :param userid: String. Userid to get information about.
    :return: Dictionary. List of all phones/numbers assigned to the provided user.
    '''

    # Start by getting the organization UUID
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

    # Make sure the user has 1 or more phones assigned to them
    if "phones" in rjson:
        retjson["phones"] = {}
        # rjson["phones"] is a list of all phones for a user. Iterate the list
        for dev in rjson["phones"]:
            # Add this device to the device list
            devlist.append(dev["description"] + " [" + dev["registrationStatus"] + "]")

            # Add device information to output dictionary
            if dev["mac"] not in retjson["phones"]:
                retjson["phones"][dev["mac"]] = {}
            retjson["phones"][dev["mac"]]["description"] = dev["description"]
            retjson["phones"][dev["mac"]]["registrationStatus"] = dev["registrationStatus"]
            retjson["phones"][dev["mac"]]["ipAddress"] = dev.get("ipAddress", "N/A")
            retjson["phones"][dev["mac"]]["mac"] = dev["mac"]

    # Make sure the user has 1 or more numbers assigned to them
    if "numbers" in rjson:
        retjson["numbers"] = {}
        # rjson["numbers"] is a list of all numbers for a user. Iterate the list
        for num in rjson["numbers"]:
            # Add internal number information to output dictionary
            if num["internal"] not in retjson["numbers"]:
                retjson["numbers"][num["internal"]] = {}
            retjson["numbers"][num["internal"]]["internal"] = num["internal"]

            # Add external number information to output dictionary
            if num["external"] is None:
                numlist.append("Extension " + num["internal"])
            else:
                numlist.append(num["external"] + " (x" + num["internal"] + ")")
                retjson["numbers"][num["internal"]]["external"] = num["external"]

    return retjson


def get_spark_call_health(incoming_msg, rettype):
    '''
    Get health status from Spark Call.

    :param incoming_msg: String. this is the message that is posted in Spark. The client's username will be parsed
                        out from this.
    :param rettype: String. html or json
    :return: String (if rettype = html). This is a fully formatted string that will be sent back to Spark
             Dictionary (if rettype = json). Raw data that is expected to be consumed in cico_combined
    '''

    # Get report of all devices in organization
    sparkerror = 0
    spark_data = spark_api_get_dev_status_report()
    if isinstance(spark_data, str):
        if spark_data.find("Error") >= 0:
            print("Spark reported an error. Unable to show Spark Call Data.")
            sparkerror = 1
    # This is probably non-functional...
    if len(spark_data) == 1:
        if spark_data[0].find("Error") >= 0:
            print("Spark reported an error. Unable to show Spark Call Data.")
            sparkerror = 1

    # If returning json, don't do any processing, just return raw data

    if sparkerror == 0:
        if rettype == "json":
            return spark_data
        else:
            retmsg = "<h3>Spark Details:</h3>"
            if spark_over_dash:
                retmsg += "<a href='" + spark_over_dash + "'>Spark Dashboard</a><br><ul>"
            else:
                retmsg += "<a href='https://admin.ciscospark.com'>Spark Dashboard</a><br><ul>"

            print(spark_data)
            # Iterate the list of all phones, which will be sorted by model
            for d in sorted(spark_data):
                # Templates and other things can show up in this list. Ensure that the device model includes "Cisco"
                if d.find("Cisco") >= 0:
                    # If there are one or more offline devices, toggle the warning indicator
                    if spark_data[d]["offline"] > 0:
                        devicon = chr(0x2757) + chr(0xFE0F)
                    else:
                        devicon = ""

                    retmsg += "<li>" + str(spark_data[d]["offline"]) + " offline out of " + str(spark_data[d]["num"]) + " " + d + "(s)." + devicon + "</li>"
            retmsg += "</ul><strong>" + str(spark_data["Total"]["offline"]) + " phone(s) offline out of a total of " + str(spark_data["Total"]["num"]) + " phone(s).</strong>"

            return retmsg
    else:
        return ""


def get_spark_call_clients(incoming_msg, rettype):
    '''
    Get client details from Spark Call.

    :param incoming_msg: String. this is the message that is posted in Spark. The client's username will be parsed
                        out from this.
    :param rettype: String. html or json
    :return: String (if rettype = html). This is a fully formatted string that will be sent back to Spark
             Dictionary (if rettype = json). Raw data that is expected to be consumed in cico_combined
    '''

    # Get client username
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    # Search for user in Spark Call
    userdata = {"html": "", "json": {}}
    userinfo = spark_call_search_user(client_id)
    # Iterate list of found users, getting details about each
    for u in userinfo:
        userdata = spark_call_get_user_info(u)

    # If returning json, don't do any processing, just return raw data
    if rettype == "json":
        return userdata
    else:
        retmsg = "<h3>Collaboration:</h3>"
        retmsg += "<strong>Phones:</strong><br>"
        # Iterate list of phones to create output
        if "phones" in userdata:
            for d in userdata["phones"]:
                dev = userdata["phones"][d]
                retmsg += dev["description"] + " [<em>" + dev["registrationStatus"] + "</em>]<br>"
                retmsg += "<i>IP:</i> " + dev.get("ipAddress", "N/A") + "<br>"
                retmsg += "<i>MAC:</i> " + dev["mac"] + "<br>"

        # Iterate list of numbers to create output
        if "numbers" in userdata:
            for n in userdata["numbers"]:
                num = userdata["numbers"][n]
                retmsg += "<br><strong>Numbers:</strong><br>"
                if "external" in num:
                    retmsg += num["external"] + " (x" + num["internal"] + ")\n"
                else:
                    retmsg += "Extension " + num["internal"] + "<br>"

        return retmsg


def get_spark_call_health_html(incoming_msg):
    '''
    Shortcut for bot health command, for html

    :param incoming_msg: this is the message that is posted in Spark
    :return: this is a fully formatted string that will be sent back to Spark
    '''
    return get_spark_call_health(incoming_msg, "html")


def get_spark_call_clients_html(incoming_msg):
    '''
    Shortcut for bot check command, for html

    :param incoming_msg: this is the message that is posted in Spark
    :return: this is a fully formatted string that will be sent back to Spark
    '''
    return get_spark_call_clients(incoming_msg, "html")
