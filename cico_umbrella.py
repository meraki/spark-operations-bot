'''
    This module is specifically for Umbrella-related operations. This is for parsing S3 logs as there isn't a
    relevant Umbrella API.
'''
import os
import gzip
import io
from stat import S_ISREG, S_ISDIR, ST_CTIME, ST_MODE

# ========================================================
# Load required parameters from environment variables
# ========================================================

umbrella_over_dash = os.getenv("UMBRELLA_OVERRIDE_DASHBOARD")

# ========================================================
# Initialize Program - Function Definitions
# ========================================================


def parse_umbrella_logs():
    '''
    This function will parse the local Umbrella logs to generate aggregate and user-specific stats

    :return: Dictionary. Dict of all stats found in logs.
    '''

    frstats = {"Aggregate": {"Total": 0}, "Users": {}}
    local = "/tmp"
    dist = "dnslogs/"

    # Load data from log files. We are sorting from newest to oldest, looking for files in specific directories
    try:
        entries = (os.path.join(local + os.sep + dist, fn) for fn in os.listdir(local + os.sep + dist))
    except:
        return {"Error": "Unable to load Umbrella data from Log Files."}
    entries = ((os.stat(path), path) for path in entries)
    entries = ((stat[ST_CTIME], path)
                for stat, path in entries if S_ISDIR(stat[ST_MODE]))
    for cdate, fdir in sorted(entries, reverse=True):
        #print(fdir, cdate)
        entries2 = (os.path.join(fdir, fn) for fn in os.listdir(fdir))
        entries2 = ((os.stat(path), path) for path in entries2)
        entries2 = ((stat[ST_CTIME], path)
                   for stat, path in entries2 if S_ISREG(stat[ST_MODE]))
        for cdate, fn in sorted(entries2, reverse=True):
            #print(fn, cdate)
            # We have now iterated to a specific file. Open it and read the data in.
            with open(fn, 'rb') as fin:
                data = io.BytesIO(fin.read())

                # These files are gzipped, so we will need to decompress
                data.seek(0)
                decompressedFile = gzip.GzipFile(fileobj=data, mode='rb')
                # Read the file data and parse
                filedata = decompressedFile.read().decode("utf-8")
                # "2017-10-07 00:41:56","hankaaron@ciscodcloudpov.com","hankaaron@ciscodcloudpov.com","108.221.201.58","108.221.201.58","Blocked","1 (A)","NOERROR","internetbadguys.com.","Phishing"
                filelist = filedata.split("\n")
                # Iterate lines in the file, from bottom to top. We are doing this since we want to collect the 5 most
                # recent threats for a given client, and most recent threats will be at the bottom
                for f in reversed(filelist):
                    # We should have a file. Make sure.
                    if f:
                        # Parse data and split, then create dictionary for record
                        fr = f[1:-1].split('","')
                        urec = {"Timestamp": fr[0], "InternalIp": fr[3], "Domain": fr[8], "Categories": fr[9]}

                        # New user. Initialize basic constructs for them. fr[1] represents a device name.
                        if fr[1] not in frstats["Users"]:
                            frstats["Users"][fr[1]] = {}
                            frstats["Users"][fr[1]]["Blocked"] = []
                            frstats["Users"][fr[1]]["Aggregate"] = {}
                            frstats["Users"][fr[1]]["Aggregate"]["Total"] = 0

                        # If this entry is for a Blocked record, capture additional stats for that
                        if fr[5] == "Blocked":
                            # We will capture the aggregate number of blocks for this type of event. fr[9] represents
                            # the category of the block. If this is a new category, set to 1, otherwise increment
                            if fr[9] in frstats["Aggregate"]:
                                frstats["Aggregate"][fr[9]] += 1
                            else:
                                frstats["Aggregate"][fr[9]] = 1

                            # If we have fewer than 5 Blocked events already tagged, we want to append any Blocked
                            # events to the blocked list for the user.
                            if len(frstats["Users"][fr[1]]["Blocked"]) < 5:
                                frstats["Users"][fr[1]]["Blocked"].append(urec)

                            # We will capture the user-specific number of blocks for this type of event. fr[9]
                            # represents the category of the block. If this is a new category, set to 1, otherwise
                            # increment
                            if fr[9] in frstats["Users"][fr[1]]["Aggregate"]:
                                frstats["Users"][fr[1]]["Aggregate"][fr[9]] += 1
                            else:
                                frstats["Users"][fr[1]]["Aggregate"][fr[9]] = 1

                        # Add aggregate total and user-specific total
                        frstats["Aggregate"]["Total"] += 1
                        frstats["Users"][fr[1]]["Aggregate"]["Total"] += 1

    #print(frstats)
    return frstats


def get_umbrella_health(incoming_msg, rettype):
    '''
    This function will return health data for the Umbrella network (based on local logs)

    :param incoming_msg: String. this is the message that is posted in Spark. The client's username will be parsed
                        out from this.
    :param rettype: String. html or json
    :return: String (if rettype = html). This is a fully formatted string that will be sent back to Spark
             Dictionary (if rettype = json). Raw data that is expected to be consumed in cico_combined
    '''

    # Parse logs to get relevant data
    logdata = parse_umbrella_logs()

    retmsg = "<h3>Umbrella Details (Last 24 hours):</h3>"
    if umbrella_over_dash:
        retmsg += "<a href='" + umbrella_over_dash + "'>Umbrella Dashboard</a><br><ul>"
    else:
        retmsg += "<a href='https://login.umbrella.com/'>Umbrella Dashboard</a><br><ul>"
    # From a health perspective, we are interested in aggregate data. Make sure this data exists
    if "Aggregate" in logdata:
        retmsg += "<li>Total Requests: " + str(logdata["Aggregate"]["Total"]) + "</li>"
        # In addition to Total overall stats, we want to display totals for any blocked categories that is present
        # as well
        for x in logdata["Aggregate"]:
            # We have already added Total above, so we will ignore it here
            if x != "Total":
                retmsg += "<li>" + x + ": " + str(logdata["Aggregate"][x]) + " (" + str(round(logdata["Aggregate"][x] / logdata["Aggregate"]["Total"] * 100, 2)) + "%)</li>"
        retmsg += "</ul></b>"

        return retmsg
    else:
        return ""


def get_umbrella_clients(incoming_msg, rettype):
    '''
    This function will return client data for the Umbrella network (based on local logs)

    :param incoming_msg: String. this is the message that is posted in Spark. The client's username will be parsed
                        out from this.
    :param rettype: String. html or json
    :return: String (if rettype = html). This is a fully formatted string that will be sent back to Spark
             Dictionary (if rettype = json). Raw data that is expected to be consumed in cico_combined
    '''

    # Get client username
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    # Parse logs to get relevant data
    logdata = parse_umbrella_logs()

    # From a client perspective, we are interested in user-specific data. Make sure this data exists
    if "Users" in logdata:
        # If the specified user exists in the logged data, we will select that for analysis. If it does not exist,
        # we will return an empty dictionary
        if client_id in logdata["Users"]:
            userbase = logdata["Users"][client_id]
        else:
            userbase = {}

    # If returning json, don't do any processing, just return raw data
    if rettype == "json":
        return userbase
    else:
        retmsg = "<h3>Umbrella Client Stats (Last 24 hours):</h3>"
        #retmsg += "<a href='https://login.umbrella.com/'>Umbrella Dashboard</a><br><ul>"
        retmsg += "<li>Total Requests: " + str(userbase["Aggregate"]["Total"]) + "</li>"
        # In addition to Total overall stats, we want to display totals for any blocked categories that is present
        # as well
        for x in userbase["Aggregate"]:
            # We have already added Total above, so we will ignore it here
            if x != "Total":
                retmsg += "<li>" + x + ": " + str(userbase["Aggregate"][x]) + " (" + str(round(userbase["Aggregate"][x] / userbase["Aggregate"]["Total"] * 100, 2)) + "%)</li>"
        retmsg += "</ul></b>"

        # In addition to overall stats, if there are blocked requests, we want to show the most recent 5 (up to).
        if len(userbase["Blocked"]) > 0:
            retmsg += "<h4>Last 5 Blocked Requests:</h4>"
            # Iterate list of blocked requests, and add to output
            for x in userbase["Blocked"]:
                retmsg += "<li>" + x["Timestamp"] + " " + x["Domain"] + " " + x["Categories"] + "</li>"

        return retmsg


def get_umbrella_health_html(incoming_msg):
    '''
    Shortcut for bot health command, for html

    :param incoming_msg: this is the message that is posted in Spark
    :return: this is a fully formatted string that will be sent back to Spark
    '''
    return get_umbrella_health(incoming_msg, "html")


def get_umbrella_clients_html(incoming_msg):
    '''
    Shortcut for bot check command, for html

    :param incoming_msg: this is the message that is posted in Spark
    :return: this is a fully formatted string that will be sent back to Spark
    '''
    return get_umbrella_clients(incoming_msg, "html")
