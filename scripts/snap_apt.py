#!/usr/bin/env python3

import os
import re
import sys
import json
import logging
import subprocess
from tempfile import gettempdir

# Constants
SNAPPER_CONF = "root" # snapper config name
APT_LEN = 72 # snapper description apt command max length
TMP_FILE = f"{gettempdir()}/snap-apt.json" # file to store temp data

# Setup logging
logging.basicConfig(filename=f"{gettempdir()}/snap-apt.log", format="%(asctime)s: %(levelname)s: %(filename)s: %(module)s: %(funcName)s: %(message)s", level=logging.INFO)

# Function to get output of shell command
def shell_exec(command):
    res = subprocess.run(command, shell=True, capture_output=True, encoding="utf8", errors="replace")
    if res.stderr:
        msg = f"Error occurred on executing shell command {command} :: {res.stderr.strip()}"
        print(msg)
        logging.error(msg)
    return res.stdout.strip()

# Get action arg
action = sys.argv.pop()
if action not in ["pre", "post"]:
    msg = "Error: Invalid argument, must be either pre or post"
    print(msg)
    logging.warning(msg)
    sys.exit(1)

# Get path to apt
apt_path = shell_exec("command -v apt")

# Get path to apt-get
aptget_path = shell_exec("command -v apt-get")

# Get path to snapper
snapper_path = shell_exec("command -v snapper")

if not (apt_path or snapper_path):
    msg = f"Error: Unable to find apt and/or snapper installed for user {os.environ.get('USER')}"
    print(msg)
    logging.error(msg)
    sys.exit(2)

# Process pre hook
if action == "pre":
    # get packages to be installed from stdin
    pkg_files = sys.stdin.readlines()
    pkgs = [x.split("/").pop().rstrip() for x in pkg_files]
    pkg_names = [x.split("_").pop(0) for x in pkgs]
    if pkg_names:
        apt_action = f"Install {','.join(pkg_names)}"
    else:
        # check if there was an apt call
        apt_call = shell_exec(f"ps aux | grep -v grep | grep -E '{apt_path}|{aptget_path}' | head -n1")
        # parse apt command
        match = re.search(r"^.+(apt.+$)", apt_call)
        if match:
            apt_action = match.group(1)
        else:
            apt_action = "Unknown invocation"
    # take snapper pre snapshot
    snapper_description = f"Before APT: {apt_action[:APT_LEN] if len(apt_action) <= APT_LEN else apt_action[:APT_LEN-3] + '...'}"
    command = f"{snapper_path} -c {SNAPPER_CONF} create -t pre -c number -p -d '{snapper_description}'"
    pre_num = shell_exec(command)
    with open(TMP_FILE, "w") as fh:
        json.dump(
            {
                "pre_num": pre_num,
                "apt_action": apt_action,
            },
            fh,
            indent=3,
        )
    msg = f"Successfully created pre APT snapshot with ID {pre_num}"
    print(msg)
    logging.info(msg)
    sys.exit()

# Process post hook
elif action == "post":
    try:
        with open(TMP_FILE, "r") as fh:
            saved_obj = json.load(fh)
    except FileNotFoundError:
        msg = f"Error: Could not obtain saved pre snapshot details from temp file {TMP_FILE}"
        print(msg)
        logging.error(msg)
        sys.exit(3)
    except json.JSONDecodeError:
        msg = f"Error: Could not load valid JSON data from saved pre snapshot temp file {TMP_FILE}"
        print(msg)
        logging.error(msg)
        sys.exit(4)
    pre_num = saved_obj["pre_num"]
    apt_action = saved_obj["apt_action"]
    # take snapper post snapshot
    snapper_description = f"After APT: {apt_action[:APT_LEN] if len(apt_action) <= APT_LEN else apt_action[:APT_LEN-3] + '...'}"
    command = f"{snapper_path} -c {SNAPPER_CONF} create -t post -c number --pre-number {pre_num} -p -d '{snapper_description}'"
    post_num = shell_exec(command)
    os.remove(TMP_FILE)
    msg = f"Successfully created post APT snapshot with ID {post_num} in reference to pre snapshot {pre_num}"
    print(msg)
    logging.info(msg)
    sys.exit()

