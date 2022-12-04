#!/usr/bin/env python3

import os
import re
import sys
import json
import subprocess
from tempfile import gettempdir

# Constants
SNAPPER_CONF = "root" # snapper config name
APT_LEN = 72 # snapper description apt command max length
TMP_FILE = f"{gettempdir()}/snap-apt.json" # file to store temp data

# Function to get output of shell command
def shell_exec(command):
    res = subprocess.run(command, shell=True, capture_output=True, encoding="utf8", errors="replace")
    if res.stderr:
        print(res.stderr)    
    return res.stdout

# Get action arg
action = sys.argv.pop()
if action not in ["pre", "post"]:
    print("Error: Invalid argument, must be either pre or post")
    sys.exit(1)

# Get path to apt
apt_path = shell_exec("command -v apt").strip()

# Get path to snapper
snapper_path = shell_exec("command -v snapper").strip()

if not (apt_path or snapper_path):
    print(f"Error: Unable to find apt and/or snapper installed for user {os.environ.get('USER')}")
    sys.exit(2)

# Process pre hook
if action == "pre":
    # get apt call
    apt_call = shell_exec(f"ps aux | grep -v grep | grep '{apt_path}' | head -n1").strip()
    # parse apt command
    match = re.search(r"^.+(apt.+$)", apt_call)
    if match:
        apt_cmd = match.group(1)
    else:
        print("Error: Could not parse apt command")
        sys.exit(3)
    # take snapper pre snapshot
    snapper_description = f"Before APT: {apt_cmd[:APT_LEN] if len(apt_cmd) <= APT_LEN else apt_cmd[:APT_LEN-3] + '...'}"
    command = f"{snapper_path} -c {SNAPPER_CONF} create -t pre -c number -p -d '{snapper_description}'"
    pre_num = shell_exec(command).strip()
    with open(TMP_FILE, "w") as fh:
        json.dump(
            {
                "pre_num": pre_num,
                "apt_cmd": apt_cmd,
            },
            fh,
            indent=3,
        )
    print(f"Successfully created pre APT snapshot with ID {pre_num}")
    sys.exit()

# Process post hook
elif action == "post":
    try:
        with open(TMP_FILE, "r") as fh:
            saved_obj = json.load(fh)
    except FileNotFoundError:
        print(f"Error: Could not obtain saved pre snapshot details from temp file {TMP_FILE}")
        sys.exit(4)
    except json.JSONDecodeError:
        print(f"Error: Could not load valid JSON data from saved pre snapshot temp file {TMP_FILE}")
        sys.exit(5)
    pre_num = saved_obj["pre_num"]
    apt_cmd = saved_obj["apt_cmd"]
    # take snapper post snapshot
    snapper_description = f"After APT: {apt_cmd[:APT_LEN] if len(apt_cmd) <= APT_LEN else apt_cmd[:APT_LEN-3] + '...'}"
    command = f"{snapper_path} -c {SNAPPER_CONF} create -t post -c number --pre-number {pre_num} -p -d '{snapper_description}'"
    post_num = shell_exec(command).strip()
    os.remove(TMP_FILE)
    print(f"Successfully created post APT snapshot with ID {post_num} in reference to pre snapshot {pre_num}")
    sys.exit()
    

