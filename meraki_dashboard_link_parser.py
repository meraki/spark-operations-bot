'''
    This module is specifically for Meraki Dashboard related operations. This code is responsible for screen scraping
    the HTTP Dashboard interface to get the necessary data. It is an optional step, and what it provides is the
    ability to cross-launch directly to a device, network, or client from the bot.
'''

import cico_meraki
import requests
import os
import json
import sys
import urllib
import time

# ========================================================
# Load required parameters from environment variables
# ========================================================

meraki_http_un = os.getenv("MERAKI_HTTP_USERNAME")
meraki_http_pw = os.getenv("MERAKI_HTTP_PASSWORD")
meraki_api_token = os.getenv("MERAKI_API_TOKEN")
meraki_org = os.getenv("MERAKI_ORG")
if not meraki_org:
    meraki_org = cico_meraki.get_meraki_one_org()

if not meraki_http_un or not meraki_http_pw or not meraki_api_token or not meraki_org:
    print("meraki_dashboard_link_parser.py - Missing Environment Variable.")
    if not meraki_http_un:
        print("MERAKI_HTTP_USERNAME")
    if not meraki_http_pw:
        print("MERAKI_HTTP_PASSWORD")
    if not meraki_api_token:
        print("MERAKI_API_TOKEN")
    if not meraki_org:
        print("MERAKI_ORG")

header = {"X-Cisco-Meraki-API-Key": meraki_api_token}

# ========================================================
# Initialize Program - Function Definitions
# ========================================================


def meraki_www_get_token(strcontent):
    '''
    When logging into the dashboard, there is an "authenticity_token" hidden field. If this field is not included in
    the login POST, login will fail. Scrape this from the HTML and return so it can be POST'ed to login.

    :param strcontent: String. Raw HTML of base login page.
    :return: String. Authenticity Token.
    '''

    tokenident = '<input name="authenticity_token" type="hidden" value="'
    tokenstart = strcontent.find(tokenident)
    tokenval = strcontent[tokenstart + len(tokenident):]

    tokenend = tokenval.find('" />')
    tokenval = tokenval[:tokenend]
    return tokenval


def meraki_www_get_settings(strcontent, settingval, settingfull):
    '''
    In the dashboard, there are a large number of settings hidden in the code. This function will parse and retrieve
    the value of a specific setting

    :param strcontent: String. Raw HTML of the page.
    :param settingval: String. If the setting is in the "Mkiconf.setting = " format, pass "setting" here. Otherwise...
    :param settingfull: String. If the setting is named or punctuated differently, pass the exact string here.
    :return: String. The value of the requested setting
    '''

    # Determine whether this is a standard setting or not, and set tokenident to the exact name of the setting
    if settingfull != "":
        tokenident = settingfull
    else:
        tokenident = 'Mkiconf.' + settingval + ' = "'
    tokenstart = strcontent.find(tokenident)
    if tokenstart < 0:
        return ""
    tokenval = strcontent[tokenstart + len(tokenident):]

    if settingfull == "":
        tokenend = tokenval.find('";')
    else:
        tokenend = tokenval.find(';')
    tokenval = tokenval[:tokenend]
    return tokenval


def meraki_www_get_path(devtype, devid):
    '''
    In the dashboard HTTP interface, different device paths have different URL construction. This function will parse
    the device type in order to generate the appropriate URL construction.

    :param devtype: String. Device type. eg, switch, wireless
    :param devid: String. Device ID that will be part of the path.
    :return: String. Relevant constructed URL.
    '''

    if devid != "":
        newdevid = "/" + devid
    else:
        newdevid = ""
    retparm = "/manage/nodes/new_list" + newdevid
    if devtype == "switch":
        retparm = "/manage/nodes/new_list" + newdevid
    if devtype == "wired":
        retparm = "/manage/nodes/new_wired_status"
    if devtype == "camera":
        retparm = "/manage/nodes/new_list" + newdevid
    if devtype == "wireless":
        retparm = "/manage/nodes/new_list" + newdevid
    if devtype == "systems_manager":
        retparm = "/manage/pcc/list" + newdevid

    return retparm

def meraki_www_get_org_list(strcontent):
    '''
    When logging in, there is a page that lists the organizations that you have access to. This function will parse
    this page and return a dictionary of the organizations.

    :param strcontent: String. Raw HTML content of the org selection page
    :return: Dictionary. All of the organizations including id and name.
    '''

    orgident = '<a href="/login/org_choose?eid='
    orgarr = strcontent.split(orgident)
    retarr = {}

    for x in range(1, len(orgarr)):
        orgend = orgarr[x].find('</a>')
        orgdata = orgarr[x][:orgend]
        orgdarr = orgdata.split('">')
        xst = str(x)
        retarr[xst] = {"id": orgdarr[0], "name": orgdarr[1]}
    return json.dumps(retarr)


def get_meraki_org_name():
    '''
    This is an API call that will get a list of all organizations that the API key has access to. It will then search
    the list of organizations for the ID matching the orgid that was specified/derived for the bot, and then return
    the name of that organization.

    :return: String. The organization name for the specified/derived organization.
    '''

    # Get a list of all networks associated with the specified organization
    orgname = ""
    url = "https://dashboard.meraki.com/api/v0/organizations"
    netlist = requests.get(url, headers=header)
    netjson = json.loads(netlist.content.decode("utf-8"))
    for n in netjson:
        if str(n["id"]) == str(meraki_org):
            orgname = n["name"]

    return orgname


def get_meraki_org_url(pagecontent):
    '''
    This function will take the Dictionary of organizations coming from meraki_www_get_org_list, and search that for
    the name of the organization from get_meraki_org_name. When it has found a match, it will return the full URL
    for that organization.

    :param pagecontent: String. Raw HTML of the organization page.
    :return: String. URL of the organization to load.
    '''

    orgurl = ""
    olist = json.loads(meraki_www_get_org_list(pagecontent))
    org_name_find = get_meraki_org_name()
    for onum in olist:
        if olist[onum]["name"] == org_name_find:
            orgurl = "https://dashboard.meraki.com/login/org_choose?eid=" + olist[onum]["id"]

    return orgurl


def get_meraki_api_info():
    '''
    Unused?

    :return:
    '''

    # Get a list of all networks associated with the specified organization
    netjson = cico_meraki.get_meraki_networks()
    # Parse list of networks to extract/create URLs needed to get list of devices
    urlnet = cico_meraki.collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$1/devices", "id", "", "", "")
    # Get a list of all devices associated with the networks associated to the organization
    netlist = cico_meraki.do_multi_get(urlnet, netjson, "id", "", -1, "networkId", "devices")
    # Get uplink status of devices
    urlnetup = cico_meraki.collect_url_list(netlist, "https://dashboard.meraki.com/api/v0/networks/$1/devices/$2/uplink", "info", "id", "devices", "serial")
    netlistup = cico_meraki.do_multi_get(urlnetup, netlist, "devices", "serial", 8, "", "uplinks")
    # Split network lists up by device type
    newnetlist = cico_meraki.do_split_networks(netlistup)

    return newnetlist


def get_meraki_http_info():
    '''
    Main entry point for function. This function handles the login process, the org redirection, parsing the page
    content, and returning/parsing the XHR data.

    :return: Dictionary. Dict of relevant mapping data to create cross-launch links.
    '''

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:51.0) Gecko/20100101 Firefox/51.0'}
    loginurl = "https://dashboard.meraki.com/login/login"
    session = requests.Session()

    # Get initial login page
    r = session.get(loginurl, headers=headers)
    cookies = requests.utils.cookiejar_from_dict(requests.utils.dict_from_cookiejar(session.cookies))
    rcontent = r.content.decode("UTF-8")
    tokenval = meraki_www_get_token(rcontent)
    print("HTTP Token=", tokenval)

    # Post Login data
    dataval = {'utf8': '&#x2713;', 'email': meraki_http_un, 'password': meraki_http_pw, 'authenticity_token': tokenval, 'commit': 'Log+in', 'goto': 'manage'}
    r = session.post(loginurl, headers=headers, data=dataval, cookies=cookies)
    rcontent = r.content.decode("UTF-8")
    cookies = requests.utils.cookiejar_from_dict(requests.utils.dict_from_cookiejar(session.cookies))

    # Check to see if the org selection page has loaded. I've heard that this doesn't always happen, but I've not yet
    # found a user to test with that does not hit this page.
    if rcontent.lower().find("accounts for " + meraki_http_un.lower()):
        orgurl = get_meraki_org_url(rcontent)
        print(orgurl)
    else:
        print("No Account Selection found. Unable to proceed.")
        sys.exit()

    if orgurl:
        # Load redirect page
        r = session.get(orgurl, headers=headers, cookies=cookies)
        rcontent = r.content.decode("UTF-8")

        # Parse content to get auth token and base url. auth token is required for XHR requests, and Base URL is...
        # possibly the last network loaded when the user last logged out?
        xhrtoken = meraki_www_get_settings(rcontent, "authenticity_token", "")
        baseurl = meraki_www_get_settings(rcontent, "base_url", "")

        # Search the history to get the most recent FQDN so we can link directly to the appropriate shard.
        for resp in r.history:
            o = urllib.parse.urlparse(resp.url)
            mhost = o.netloc

        #"https://%2%%3%manage/organization/overview#t=network"

        # Load administered orgs XHR Data
        #xhrurl = "https://" + mhost + baseurl + "manage/organization/administered_orgs"
        xhrurl = "https://" + mhost + baseurl + "manage/organization/org_json?jsonp=jQuery18307230485578098947_" + str(int(time.time() * 1000)) + "&t0=" + str(int(time.time())) + ".000" + "&t1=" + str(int(time.time())) + ".000" + "&primary_load=true&_=" + str(int(time.time() * 1000))
        xhrheader = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:51.0) Gecko/20100101 Firefox/51.0',"X-CSRF-Token": xhrtoken,"X-Requested-With": "XMLHttpRequest"}
        r = session.get(xhrurl, headers=xhrheader, cookies=cookies)
        rcontent = r.content.decode("UTF-8")
        rjson = json.loads(rcontent[rcontent.find("({")+1:-1])
        #print(rjson)

        outjson = {}
        mbase = rjson["networks"]
        outjson = {"networks": {}, "devices": {}}
        # Now, we will iterate the data loaded from the XHR request to generate the mapping data that we need.
        for jitem in mbase:
            # This generates the link to the network
            outjson["networks"][mbase[jitem]["name"]] = {"baseurl": "https://" + mhost + "/" + mbase[jitem]["tag"] + "/n/" + mbase[jitem]["eid"] + meraki_www_get_path(mbase[jitem]["type"], "")}           #, "id": mbase[jitem]["id"]

            # This generates the link to the device
            for jdev in rjson["nodes"]:
                if rjson["nodes"][jdev]["ng_id"] == mbase[jitem]["id"]:
                    outjson["devices"][rjson["nodes"][jdev]["mac"]] = {"baseurl": "https://" + mhost + "/" + mbase[jitem]["tag"] + "/n/" + mbase[jitem]["eid"] + meraki_www_get_path(mbase[jitem]["type"], rjson["nodes"][jdev]["id"]), "desc": rjson["nodes"][jdev]["name"]}              #mbase[jitem]["id"]          #rjson["nodes"][jdev]["serial"]

        return outjson
    else:
        print("Unable to get org url. Check username and password...")
        return {}


#dbjson = get_meraki_http_info()
#print(json.dumps(dbjson))
#os.environ["MERAKI_DASHBOARD_MAP"] = str(dbjson)
#print(str(dbjson))
#print("=======")
#print("MERAKI_DASHBOARD_MAP environment variable set.")
#for n in sorted(get_meraki_api_info()):
#    print(n)