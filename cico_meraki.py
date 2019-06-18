'''
    This module is specifically for Meraki-related operations. This is for the Meraki Dashboard API
'''

import requests
# There are some complications with Python 3.6 and various modules. We will need to monkey-patch some stuff to make
# it work. Details were found here: https://github.com/kennethreitz/grequests/issues/103
from gevent import monkey
def stub(*args, **kwargs):  # pylint: disable=unused-argument
    pass
monkey.patch_all = stub
import grequests
import os
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========================================================
# Load required parameters from environment variables
# ========================================================

meraki_client_to = os.getenv("MERAKI_CLIENT_TIMESPAN")
if not meraki_client_to:
    meraki_client_to = "86400"
meraki_api_token = os.getenv("MERAKI_API_TOKEN")
meraki_over_dash = os.getenv("MERAKI_OVERRIDE_DASHBOARD")
#meraki_dashboard_map = os.getenv("MERAKI_DASHBOARD_MAP")       -- removed: enabled link generation at run-time --
header = {"X-Cisco-Meraki-API-Key": meraki_api_token}

# ========================================================
# Initialize Program - Function Definitions
# ========================================================


def get_meraki_orgs():
    '''
    Get a list of all organizations the user has access to

    :return: a list of dictionaries with all organizations
    '''
    url = "https://dashboard.meraki.com/api/v0/organizations"
    netlist = requests.get(url, headers=header)
    netstr = netlist.content.decode("utf-8")
    if netstr.strip() != "":
        orgjson = json.loads(netstr)
    else:
        orgjson = {}
    return orgjson


def get_meraki_one_org():
    '''
    Pick specific organization id if one is not provided. If only one organization is associated with the API key, it
    will be selected. If multiple organizations are present, alphabetically the first organization will be returned.

    :return: a string with the organization id, or 'none' if there was a problem
    '''
    olist = get_meraki_orgs()
    newodict = {}
    newolist = []
    # If there are 1 or more organizations are present, then parse the list to determine what to return
    if len(olist) >= 1:
        # Iterate the list of dictionaries
        for ol in range(0, len(olist)):
            # Build a dictionary that we can use to cross-reference back to the list of dictionaries. We need this for
            # accurate sorting
            newodict[olist[ol]["name"]] = ol
            print(olist[ol]["name"], olist[ol]["id"])
        # Now, we sort the dictionary (case-insensitive)
        newolist = sorted(newodict, key=str.lower)
        # And we return a string of the ID for the first organization in the list
        thisorg = str(olist[newodict[newolist[0]]]["id"])
        print("Selecting alphabetically first organization (" + newolist[0] + "), id #", thisorg)
        return thisorg
    else:
        # If no organizations were present, return 'none'
        print("Unable to select Organization")
        return "none"


# ========================================================
# Delayed parameter load for the organization
# ========================================================
meraki_org = os.getenv("MERAKI_ORG")
if not meraki_org:
    meraki_org = get_meraki_one_org()
# ========================================================


def get_meraki_networks():
    '''
    Get a list of all networks associated with the specified organization. Watch for 200 OK, because an organization
    can have 0 networks, which will generate a 404 instead.

    :return: a dictionary with all networks that are part of the specified/derived organization
    '''
    url = "https://dashboard.meraki.com/api/v0/organizations/" + meraki_org + "/networks"
    netlist = requests.get(url, headers=header)
    if netlist.status_code == 200:
        netjson = json.loads(netlist.content.decode("utf-8"))
    else:
        netjson = {}
        print("Error retrieving Meraki networks:", netlist.status_code)
    return netjson


def get_org_devices(netinfo):
    '''
    Get a list of all devices in a given organization

    :return: a list with all devices that are part of the specified/derived organization
    '''
    url = "https://dashboard.meraki.com/api/v0/organizations/" + meraki_org + "/devices"
    netlist = requests.get(url, headers=header)
    if netlist.status_code == 200:
        netjson = json.loads(netlist.content.decode("utf-8"))
    else:
        netjson = {}
        print("Error retrieving Meraki devices:", netlist.status_code)
    return netjson


def get_org_device_statuses(netinfo):
    '''
    Get a list of all devices/statuses in a given organization

    :return: a list with all devices that are part of the specified/derived organization
    '''
    dev_list = get_org_devices(netinfo)
    out_netjson = {}
    url = "https://dashboard.meraki.com/api/v0/organizations/" + meraki_org + "/deviceStatuses"
    netlist = requests.get(url, headers=header)
    if netlist.status_code == 200:
        netjson = json.loads(netlist.content.decode("utf-8"))
        for n in netjson:
            dev_info = {}
            for d in dev_list:
                if d["serial"] == n["serial"]:
                    dev_info = d
                    break
            n_info = n
            n_info["info"] = dev_info
            if n["networkId"] in out_netjson:
                out_netjson[n["networkId"]]["devices"][n["serial"]] = n_info
            else:
                out_netjson[n["networkId"]] = {"devices": {n["serial"]: n_info}}

        for n in out_netjson:
            for m in netinfo:
                if m["id"] == n:
                    out_netjson[n]["info"] = m
    else:
        print("Error retrieving Meraki devices:", netlist.status_code)
    return out_netjson


def meraki_create_dashboard_link(linktype, linkname, displayval, urlappend, linknameid):
    '''
    This function is used to create the dashboard cross-launch links for clients, networks and devices. For devices,
    it can also create a generic cross-launch link if the dashboard username/password were not provided, but that is
    not nearly as reliable.

    :param linktype: String. 'devices' or 'networks'
    :param linkname: String. for a device, this is the mac address. for a network, this is the name of the network
    :param displayval: String. the displayed portion of the hyerlink.
    :param urlappend: String. Anything that needs to be added to the end of the URL
    :param linknameid: Integer. 0 = Network / Device base link only. 1 = Device link including Port data (used when
            forming generic links; there is no generic link to the port level)
    :return: String. A hyperlink (<a>) linking to the dashboard if possible
    '''

    shownet = displayval

    # Only run if we were able to get a dashboard map using the username password of the user
    if meraki_dashboard_map:
        # Used to work differently... just remapping the variable now.
        mapjson = meraki_dashboard_map          #json.loads(meraki_dashboard_map.replace("'", '"'))
        # If 'devices' or 'networks' is present in the map (it should be)
        if linktype in mapjson:
            # If the given mac address or network name is present in the map (it should be)
            if linkname in mapjson[linktype]:
                # Create the hyperlink
                if not displayval:
                    displayval = linkname
                shownet = "<a href='" + mapjson[linktype][linkname]["baseurl"] + urlappend + "'>" + displayval + "</a>"

    # If shownet is the same as displayval, it means there was a problem above. Try to add generic link... if this is
    # a device, and doesn't include port-level detail
    if shownet == displayval and linktype == "devices" and linknameid == 0:
        # Create the generic hyperlink
        shownet = "<a href='https://dashboard.meraki.com/manage/nodes/show/" + linkname + "'>" + displayval + "</a>"

    return shownet


def meraki_dashboard_client_mod(netlink, cliid, clidesc):
    '''
    This function is used as an extension of the meraki_create_dashboard_link function, and used to generate the
    client-specific cross-launch links. It can also create a generic cross-launch link if the dashboard
    username/password were not provided, but that is not nearly as reliable.

    :param netlink: String. The hyperlink from a 'network' call to the meraki_create_dashboard_link function.
    :param cliid: String. The unique ID of the client.
    :param clidesc: String. The name of the client. This is what gets displayed for the hyperlink.
    :return:
    '''

    showcli = clidesc

    # If the meraki_create_dashboard_link function generated a hyperlink, and it was passed to this function, then
    # we will attempt to modify
    if netlink:
        # We are searching the string for /manage, and will strip everything after that and reconstruct
        if netlink.find("/manage") >= 0:
            # Create the hyperlink
            showcli = netlink.split("/manage")[0] + "/manage/usage/list#c=" + cliid + "'>" + clidesc + "</a>"
    else:
        # Create the generic hyperlink
        showcli = "<a href='https://dashboard.meraki.com/manage/usage/list#c=" + cliid + "'>" + clidesc + "</a>"

    return showcli


def collect_url_list(jsondata, baseurl, attr1, attr2, battr1, battr2):
    '''
    Iterates the jsondata list/dictionary and pulls out attributes to generate a list of URLs

    :param jsondata: list of dictionaries or dictionary of lists
    :param baseurl: String. base url to use. place a $1 to show where to substitute
    :param attr1: String. when using a list of dictionaries, this is the key that will be retrieved from each dict in
                    the list when using a dictionary of lists, this is the key where all of the lists will be found
    :param attr2: String. (optional) pass "" to disable
                    when using a dictionary of lists, this is the key that will be retrieved from each dict in each list

    These are both optional, and used if a second substitution is needed ($2)
    :param battr1: String. (optional) when using a list of dictionaries, this is the key that will be retrieved from
                    each dict in the list when using a dictionary of lists, this is the key where all of the lists will
                    be found
    :param battr2: String. (optional) pass "" to disable
                    when using a dictionary of lists, this is the key that will be retrieved from each dict in each list
    :return: List. A list of all URLs derived from the base URL and the data source.

    urlnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$1/devices", "id", "", "", "")
    urlnetup = collect_url_list(netlist, "https://dashboard.meraki.com/api/v0/networks/$1/devices/$2/uplink", "info", "id", "devices", "serial")
    urlnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$1/devices", "id", "", "", "")
    smnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$1/sm/devices/", "id", "", "", "")
    urldev = collect_url_list(netlist, "https://dashboard.meraki.com/api/v0/devices/$1/clients?timespan=86400", "devices", "serial", "", "")
    '''

    urllist = []
    sub1 = ""
    # Iterate the data source
    for jsonitem in jsondata:
        # If attr2 is blank, we should have a list of dictionaries. We will search the current dictionary in the list
        # being iterated to see if it matches what was supplied in attr1
        if attr2 == "":
            if attr1 in jsonitem:
                # Found a match, add the URL to the list
                urllist.append(baseurl.replace("$1", jsonitem[attr1]))
        # If attr2 is present, we should have a dictionary of lists. We will see if the current dictionary entry has
        # a value for the key specified by attr1.
        else:
            if attr1 in jsondata[jsonitem]:
                # The key is present. The values should be in a list, so we will iterate them now.
                for jsonitem2 in jsondata[jsonitem][attr1]:
                    # Check to see if the entry in the iterated list is a string or not.
                    if isinstance(jsonitem2, str):
                        # If it's a string, we will check to see if it matches what was specified by attr2.
                        if jsonitem2 == attr2:
                            # If battr1 has been specified, it means a second substitution will be needed. We will
                            # handle that later
                            if battr1 == "":
                                # Found a match, add the URL to the list
                                urllist.append(baseurl.replace("$1", jsondata[jsonitem][attr1][jsonitem2]))
                            else:
                                sub1 = jsondata[jsonitem][attr1][jsonitem2]
                    else:
                        # If it's not a string, it should be a dictionary. We will pull the value found in the key
                        # specified in attr2.

                        # If battr1 has been specified, it means a second substitution will be needed. We will handle
                        # that later
                        if battr1 == "":
                            # Found a match, add the URL to the list
                            urllist.append(baseurl.replace("$1", jsonitem2[attr2]))
                        else:
                            sub1 = jsonitem2[attr2]

            # We need a second substitution. Check our currently iterated dictionary entry to find the value specified
            # with battr1.
            if battr1 in jsondata[jsonitem]:
                # This should be tied to a list of items. Iterate that list
                for jsonitem2 in jsondata[jsonitem][battr1]:
                    # Check to see if the currently iterated list item is a String or not
                    if isinstance(jsonitem2, str):
                        # If it's a string, we want to see whether the iterated list item matches what was searched
                        # for with battr2
                        if jsonitem2 == battr2:
                            # Found a match, add the URL to the list
                            urllist.append(baseurl.replace("$1", sub1).replace("$2", jsondata[jsonitem][battr1][jsonitem2]))
                    else:
                        # If it's not a string, it should be a dictionary, so we want to retrieve the value found in
                        # the key specified by battr2 and use the value to substitute

                        # Found a match, add the URL to the list
                        urllist.append(baseurl.replace("$1", sub1).replace("$2", jsonitem2[battr2]))
    return urllist


def do_multi_get(url_list, comp_list, comp_id1, comp_id2, comp_url_idx, comp_key, content_key):
    '''
    Issues multiple GET requests to a list of URLs. Also will join dictionaries together based on returned content.

    :param url_list: List. list of URLs to issue GET requests to
    :param comp_list: List. (optional) pass [] to disable
                        used to join the results of the GET operations to an existing dictionary
    :param comp_id1: String. when using a list of dictionaries, this is the key to retrieve from each dict in the list
                        when using a dictionary of lists, this is the key where all of the lists will be found
    :param comp_id2: String. (optional) pass "" to disable
                        when using a dictionary of lists, this is key that will be retrieved from each dict in each list
    :param comp_url_idx: Integer. (optional) pass -1 to disable
                        when merging dictionaries, they can be merged either on a URL comparision or a matching key. Use
                        this to specify that they be merged based on this specific index in the URL. So to match
                        'b' in http://a.com/b, you would specify 3 here, as that is the 3rd // section in the URL
    :param comp_key: String. (optional) pass "" to disable
                        when merging dictionaries, they can be merged either on a URL comparision or a matching key. Use
                        this to specify that they be merged based on this key found in the content coming back from the
                        GET requests
    :param content_key: String. (optional when not merging, required when merging) pass "" to disable
                        this is the base key added to the merged dictionary for the merged data
    :return:
    '''

    # Create a session that can automatically retry when an error condition is encountered.
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.2, status_forcelist=[403, 500, 502, 503, 504], raise_on_redirect=True,
                    raise_on_status=True)
    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.mount('https://', HTTPAdapter(max_retries=retries))

    # Execute all GET requests
    rs = (grequests.get(u, headers=header, session=s) for u in url_list)

    content_dict = {}
    # Parse request responses
    for itemlist in grequests.imap(rs, stream=False):
        # Pull out the content and convert into JSON
        icontent = itemlist.content.decode("utf-8")
        inlist = json.loads(icontent)
        # Only proceed if data is present
        if len(inlist) > 0:
            # Use the URL index if it was specified, otherwise use the comparision key
            if comp_url_idx >= 0:
                urllist = itemlist.url.split("/")
                matchval = urllist[comp_url_idx]
            else:
                matchval = inlist[0][comp_key]

            # Check to see if a comparision list was provided
            if len(comp_list) > 0:
                # comp_list was passed, iterate and merge dictionaries
                for net in comp_list:
                    if comp_id2 == "":
                        # This is a list of dictionaries. if this matches the search, add it to the content dict
                        if matchval == net[comp_id1]:
                            kid1 = net["id"]

                            if kid1 not in content_dict:
                                content_dict[kid1] = {}
                            content_dict[kid1]["info"] = net
                            content_dict[kid1][content_key] = inlist
                            break
                    else:
                        # This is a dictionary of lists. if the match is present in this dictionary, continue parsing
                        if matchval in json.dumps(comp_list[net][comp_id1]):
                            kid1 = comp_list[net]["info"]["id"]

                            for net2 in comp_list[net][comp_id1]:
                                kid2 = net2["serial"]

                                if comp_id2 in net2:
                                    if matchval == net2[comp_id2]:
                                        if kid1 not in content_dict:
                                            content_dict[kid1] = {}
                                        if comp_id1 not in content_dict[kid1]:
                                            content_dict[kid1][comp_id1] = {}
                                        if kid2 not in content_dict[kid1][comp_id1]:
                                            content_dict[kid1][comp_id1][kid2] = {}

                                        content_dict[kid1]["info"] = comp_list[net]
                                        content_dict[kid1][comp_id1][kid2]["info"] = net2
                                        content_dict[kid1][comp_id1][kid2][content_key] = inlist
                                        break
            else:
                # No comp_list was passed.
                if matchval not in content_dict:
                    content_dict[matchval] = {}
                if content_key != "":
                    if content_key not in content_dict[matchval]:
                        content_dict[matchval][content_key] = {}
                    content_dict[matchval][content_key] = inlist
                else:
                    content_dict[matchval] = inlist

    return content_dict


def decode_model(strmodel):
    '''
    Decodes the Meraki model number into it's general type.

    :param strmodel: String. Model number of the product.
    :return: String. Return the Meraki device type based on the model.
    '''
    outmodel = ""
    if "MX" in strmodel:
        outmodel = "appliance"
    if "MS" in strmodel:
        outmodel = "switch"
    if "MR" in strmodel:
        outmodel = "wireless"
    if "MV" in strmodel:
        outmodel = "camera"
    if "MC" in strmodel:
        outmodel = "phone"

    if outmodel == "":
        outmodel = strmodel[0:2]

    return outmodel


def do_sort_smclients(in_smlist):
    '''
    Rearranges the SM Dictionary to group clients by MAC address rather than a single list

    :param in_smlist: List. List of non-organized SM clients
    :return: Dictionary. Dictionary of SM clients organized by MAC address
    '''
    out_smlist = {}

    # Iterate list of networks
    for net in in_smlist:
        # If there are devices in the network, iterate the list of networks
        if "devices" in in_smlist[net]:
            for cli in in_smlist[net]["devices"]:
                # If the network is not already in the return dictionary, add it now
                if net not in out_smlist:
                    out_smlist[net] = {"devices": {}}
                # Add this client to a dictionary key cooresponding to the mac address of the client
                out_smlist[net]["devices"][cli["wifiMac"]] = cli

    return out_smlist


def do_split_networks(in_netlist):
    '''
    Splits out combined Meraki networks into individual device networks. The API will only provide combined networks.
    In order to build Dashboard cross-launch links, we will need to carve these combined networks up into the
    cooresponding individual networks.

    :param in_netlist: Dictionary. Dict of all networks for the provided/derived organization.
    :return: Dictionary. Updated to break out devices into their individual networks.
    '''
    devdict = {}

    # Iterate dictionary of networks
    for net in in_netlist:
        base_name = in_netlist[net]["info"]["name"]
        # Iterate dictionary of devices in the currently iterated network
        for devsn in in_netlist[net]["devices"]:
            dev = in_netlist[net]["devices"][devsn]
            thisstat = {"status": in_netlist[net]["devices"][dev["serial"]]["status"]}
            # Don't try to un-combine already non-combined networks...
            if in_netlist[net]["info"]["type"] != "combined":
                newname = base_name
                newdev = {**dev, **thisstat}
            else:
                # Look up the Model number to determine what the dashboard name will be
                thisdevtype = decode_model(dev["info"]["model"])
                # Also, retain uplink data for output dict
                # This is the format of the output network. 'Network Name - device type"
                newname = base_name + " - " + thisdevtype
                newdev = {**dev, **thisstat}

            # Append or create this entry in the output dict
            if newname in devdict:
                devdict[newname].append(newdev)
            else:
                devdict[newname] = [newdev]

    return devdict


def get_meraki_health(incoming_msg, rettype):
    '''
    This function will return health data for the Meraki networks that are part of the provided/derived organization

    :param incoming_msg: String. this is the message that is posted in Spark
    :param rettype: String. this is a fully formatted string that will be sent back to Spark
    :return:
    '''

    # Get a list of all networks associated with the specified organization
    netjson = get_meraki_networks()

    # Get a list of all devices in the organization
    statlist = get_org_device_statuses(netjson)
    # Split network lists up by device type
    newnetlist = do_split_networks(statlist)

    totaldev = 0
    offdev = 0
    totaloffdev = 0
    devicon = ""
    retmsg = "<h3>Meraki Details:</h3>"
    if meraki_over_dash:
        retmsg += "<a href='" + meraki_over_dash + "'>Meraki Dashboard</a><br><ul>"
    else:
        retmsg += "<a href='https://dashboard.meraki.com/'>Meraki Dashboard</a><br><ul>"
    # Iterate through all of the networks, sorted by name
    for net in sorted(newnetlist):
        # Iterate through all devices in the currently iterated network
        for dev in newnetlist[net]:
            # Check status of the device
            if dev["status"] != "online":
                offdev += 1
                totaloffdev += 1
                devicon = chr(0x2757) + chr(0xFE0F)

        # Increment the total number of devices
        totaldev += len(newnetlist[net])
        # Attempt to create a dashboard cross-launch link (no generic link available), then append data for this network
        shownet = meraki_create_dashboard_link("networks", net, net, "", 0)
        retmsg += "<li>Network '" + shownet + "' has " + str(offdev) + " device(s) offline out of " + str(len(newnetlist[net])) + " device(s)." + devicon + "</li>"
        offdev = 0
        devicon = ""
    # Append summary data
    retmsg += "</ul><b>" + str(totaloffdev) + " device(s) offline out of a total of " + str(totaldev) + " device(s).</b>"

    return retmsg


def get_meraki_clients(incoming_msg, rettype):
    '''
    This function will return client data for the Meraki networks that are part of the provided/derived organization

    :param incoming_msg: String. this is the message that is posted in Spark. The client's username will be parsed
                        out from this.
    :param rettype: String. html or json
    :return: String (if rettype = html). This is a fully formatted string that will be sent back to Spark
             Dictionary (if rettype = json). Raw data that is expected to be consumed in cico_combined
    '''

    devcount = 0
    # Get client username
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]
    # Get a list of all networks associated with the specified organization
    netjson = get_meraki_networks()
    # Parse list of networks to extract/create URLs needed to get list of devices
    urlnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$1/devices", "id", "", "", "")
    smnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$1/sm/devices/", "id", "", "", "")
    # Get a list of all devices associated with the networks associated to the organization
    netlist = do_multi_get(urlnet, netjson, "id", "", -1, "networkId", "devices")
    smlist = do_multi_get(smnet, [], "id", "", 6, "", "")
    newsmlist = do_sort_smclients(smlist)
    smnetid = smnet[0].split("/")[6]
    # Parse list of devices to extract/create URLs needed to get list of clients
    urldev = collect_url_list(netlist, "https://dashboard.meraki.com/api/v0/devices/$1/clients?timespan=" + meraki_client_to, "devices", "serial", "", "")
    # Get a list of all clients associated with the devices associated to the networks associated to the organization
    netlist = do_multi_get(urldev, netlist, "devices", "serial", 6, "", "clients")

    # If returning json, don't do any processing, just return raw data
    if rettype == "json":
        return {"client": netlist, "sm": newsmlist, "smnetid": smnetid}
    else:
        retmsg = "<h3>Associated Clients:</h3>"
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
                            if cli["description"] == client_id and "switchport" in cli:
                                devbase = netlist[net]["devices"][dev]["info"]
                                # These functions generate the cross-launch links (if available) for the given
                                # client/device/port
                                showdev = meraki_create_dashboard_link("devices", devbase["mac"], devbase["name"], "?timespan=" + meraki_client_to, 0)
                                showport = meraki_create_dashboard_link("devices", devbase["mac"], str(cli["switchport"]), "/ports/" + str(cli["switchport"]) + "?timespan=" + meraki_client_to, 1)
                                showcli = meraki_dashboard_client_mod(showdev, cli["id"], cli["dhcpHostname"])
                                if devcount > 0:
                                    retmsg += "<br>"
                                devcount += 1
                                retmsg += "<i>Computer Name:</i> " + showcli + "<br>"

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
                                            retmsg += "<i>Model:</i> " + smbase["systemModel"] + "<br>"
                                            retmsg += "<i>OS:</i> " + smbase["osName"] + "<br>"

                                # Once we've checked for Systems Manager cross references, we will display the rest of the
                                # client details
                                retmsg += "<i>IP:</i> " + cli["ip"] + "<br>"
                                retmsg += "<i>MAC:</i> " + cli["mac"] + "<br>"
                                retmsg += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                                # This creates the description of the switch / port the client is connected to
                                retmsg += "<i>Connected To:</i> " + showdev + " (" + devbase["model"] + "), Port " + showport + "<br>"
        elif newsmlist:
            for cli in newsmlist[smnetid]["devices"]:
                smbase = newsmlist[smnetid]["devices"][cli]
                if client_id.lower() in smbase["name"].lower() or client_id.lower() in [x.lower() for x in smbase["tags"]]:
                    if devcount > 0:
                        retmsg += "<br>"
                    devcount += 1
                    retmsg += "<i>Client Name:</i> " + smbase["name"] + "<br>"
                    retmsg += "<i>Model:</i> " + smbase["systemModel"] + "<br>"
                    retmsg += "<i>OS:</i> " + smbase["osName"] + "<br>"
                    retmsg += "<i>MAC:</i> " + smbase["wifiMac"] + "<br>"
                    smssid = smbase["ssid"]
                    if smssid is None:
                        smssid = "N/A"
                    retmsg += "<i>Wireless SSID:</i> " + smssid + "<br>"

        return retmsg


def get_meraki_health_html(incoming_msg):
    '''
    Shortcut for bot health command, for html

    :param incoming_msg: this is the message that is posted in Spark
    :return: this is a fully formatted string that will be sent back to Spark
    '''
    return get_meraki_health(incoming_msg, "html")


def get_meraki_clients_html(incoming_msg):
    '''
    Shortcut for bot check command, for html

    :param incoming_msg: this is the message that is posted in Spark
    :return: this is a fully formatted string that will be sent back to Spark
    '''
    return get_meraki_clients(incoming_msg, "html")
