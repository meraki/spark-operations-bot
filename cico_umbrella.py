import os
import gzip
import io
from stat import S_ISREG, S_ISDIR, ST_CTIME, ST_MODE


def parse_umbrella_logs():
    frstats = {"Aggregate": {"Total": 0}, "Users": {}}
    local = "/tmp"
    dist = "dnslogs/"
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
            with open(fn, 'rb') as fin:
                data = io.BytesIO(fin.read())

                data.seek(0)
                decompressedFile = gzip.GzipFile(fileobj=data, mode='rb')
                filedata = decompressedFile.read().decode("utf-8")
                # "2017-10-07 00:41:56","hankaaron@ciscodcloudpov.com","hankaaron@ciscodcloudpov.com","108.221.201.58","108.221.201.58","Blocked","1 (A)","NOERROR","internetbadguys.com.","Phishing"
                filelist = filedata.split("\n")
                for f in reversed(filelist):
                    if f:
                        fr = f[1:-1].split('","')
                        urec = {"Timestamp": fr[0], "InternalIp": fr[3], "Domain": fr[8], "Categories": fr[9]}

                        if fr[1] not in frstats["Users"]:
                            frstats["Users"][fr[1]] = {}
                            frstats["Users"][fr[1]]["Blocked"] = []
                            frstats["Users"][fr[1]]["Aggregate"] = {}
                            frstats["Users"][fr[1]]["Aggregate"]["Total"] = 0

                        if fr[5] == "Blocked":
                            if fr[9] in frstats["Aggregate"]:
                                frstats["Aggregate"][fr[9]] += 1
                            else:
                                frstats["Aggregate"][fr[9]] = 1

                            if len(frstats["Users"][fr[1]]["Blocked"]) < 5:
                                frstats["Users"][fr[1]]["Blocked"].append(urec)

                            if fr[9] in frstats["Users"][fr[1]]["Aggregate"]:
                                frstats["Users"][fr[1]]["Aggregate"][fr[9]] += 1
                            else:
                                frstats["Users"][fr[1]]["Aggregate"][fr[9]] = 1

                        frstats["Aggregate"]["Total"] += 1
                        frstats["Users"][fr[1]]["Aggregate"]["Total"] += 1

    #print(frstats)
    return frstats


def get_umbrella_health(incoming_msg, rettype):
    logdata = parse_umbrella_logs()

    retmsg = "<h3>Umbrella Details (Last 24 hours):</h3>"
    retmsg += "<a href='https://login.umbrella.com/'>Umbrella Dashboard</a><br><ul>"
    if "Aggregate" in logdata:
        retmsg += "<li>Total Requests: " + str(logdata["Aggregate"]["Total"]) + "</li>"
        for x in logdata["Aggregate"]:
            if x != "Total":
                retmsg += "<li>" + x + ": " + str(logdata["Aggregate"][x]) + " (" + str(round(logdata["Aggregate"][x] / logdata["Aggregate"]["Total"] * 100, 2)) + "%)</li>"
        retmsg += "</ul></b>"

        return retmsg
    else:
        return ""


def get_umbrella_clients(incoming_msg, rettype):
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    logdata = parse_umbrella_logs()
    if "Users" in logdata:
        if client_id in logdata["Users"]:
            userbase = logdata["Users"][client_id]
        else:
            userbase = {}

    if rettype == "json":
        return userbase
    else:
        retmsg = "<h3>Umbrella Client Stats (Last 24 hours):</h3>"
        #retmsg += "<a href='https://login.umbrella.com/'>Umbrella Dashboard</a><br><ul>"
        retmsg += "<li>Total Requests: " + str(userbase["Aggregate"]["Total"]) + "</li>"
        for x in userbase["Aggregate"]:
            if x != "Total":
                retmsg += "<li>" + x + ": " + str(userbase["Aggregate"][x]) + " (" + str(round(userbase["Aggregate"][x] / userbase["Aggregate"]["Total"] * 100, 2)) + "%)</li>"
        retmsg += "</ul></b>"

        if len(userbase["Blocked"]) > 0:
            retmsg += "<h4>Last 5 Blocked Requests:</h4>"
            for x in userbase["Blocked"]:
                retmsg += "<li>" + x["Timestamp"] + " " + x["Domain"] + " " + x["Categories"] + "</li>"

        return retmsg


def get_umbrella_health_html(incoming_msg):
    return get_umbrella_health(incoming_msg, "html")


def get_umbrella_clients_html(incoming_msg):
    return get_umbrella_clients(incoming_msg, "html")
