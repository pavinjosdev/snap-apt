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
TMP_FILE = f"{gettempdir()}/snap-apt.json" # file to store temp data

# Setup logging
logging.basicConfig(filename=f"{gettempdir()}/snap-apt.log", format="%(asctime)s: %(levelname)s: %(message)s", level=logging.INFO)

# Function to get output of shell command
def shell_exec(command):
    res = subprocess.run(command, shell=True, capture_output=True, encoding="utf8", errors="replace")
    if res.stderr:
        msg = f"Probable issue executing shell command {command} :: {res.stderr.strip()}"
        logging.warning(msg)
    return res.stdout.strip()

# Get action arg
action = sys.argv.pop()
if action not in ["pre", "post"]:
    msg = "Error: Invalid argument, must be either pre or post"
    print(msg)
    logging.warning(msg)
    sys.exit(1)

# Get path to snapper
snapper_path = shell_exec("command -v snapper")

if not snapper_path:
    msg = f"Error: Cannot find snapper for user {os.environ.get('USER')}"
    print(msg)
    logging.error(msg)
    sys.exit(2)

# Process pre hook
if action == "pre":
    # do nothing on double invocation by external programs
    if os.path.isfile(TMP_FILE):
        msg = "Not processing pre snapshot as this is a double (back-to-back) invocation"
        print(msg)
        logging.warning(msg)
        sys.exit()
    # get packages to be installed from stdin
    pkg_files = sys.stdin.readlines()
    pkgs = [x.split("/").pop().rstrip() for x in pkg_files]
    pkg_names = [x.split("_").pop(0) for x in pkgs]
    if pkg_names:
        apt_action = f"Install {', '.join(pkg_names)}"
    else:
        apt_action = "unknown"
        # get all package names for comparison later
        pkg_names = shell_exec("apt list --installed | cut -d '/' -f 1").split()
    # take snapper pre snapshot
    snapper_description = f"Before apt: {apt_action}"
    command = f"{snapper_path} -c {SNAPPER_CONF} create -t pre -c number -p -d '{snapper_description}'"
    pre_num = shell_exec(command)
    with open(TMP_FILE, "w") as fh:
        json.dump(
            {
                "pre_num": pre_num,
                "apt_action": apt_action,
                "pkg_names": pkg_names,
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
    # do nothing on double invocation by external programs
    if not os.path.isfile(TMP_FILE):
        msg = "Not processing post snapshot as this is a double (back-to-back) invocation"
        print(msg)
        logging.warning(msg)
        sys.exit()
    try:
        with open(TMP_FILE, "r") as fh:
            saved_obj = json.load(fh)
    except json.JSONDecodeError:
        msg = f"Error: Could not load valid JSON data from saved pre snapshot temp file {TMP_FILE}"
        print(msg)
        logging.error(msg)
        sys.exit(3)
    pre_num = saved_obj["pre_num"]
    apt_action = saved_obj["apt_action"]
    if apt_action == "unknown":
        old_packages = saved_obj["pkg_names"]
        new_packages = shell_exec("apt list --installed | cut -d '/' -f 1").split()
        removed_packages_num = len(old_packages) - len(new_packages)
        removed_packages = list( set(old_packages) - set(new_packages) )
        # update description of pre snapshot
        if removed_packages:
            apt_action = f"Remove {', '.join(removed_packages)}"
        else:
            apt_action = f"Remove {removed_packages_num} packages"
        snapper_description = f"Before apt: {apt_action}"
        command = f"{snapper_path} -c {SNAPPER_CONF} modify -d '{snapper_description}' {pre_num}"
        shell_exec(command)
    # take snapper post snapshot
    snapper_description = f"After apt: {apt_action}"
    command = f"{snapper_path} -c {SNAPPER_CONF} create -t post -c number --pre-number {pre_num} -p -d '{snapper_description}'"
    post_num = shell_exec(command)
    os.remove(TMP_FILE)
    msg = f"Successfully created post APT snapshot with ID {post_num} in reference to pre snapshot {pre_num}"
    print(msg)
    logging.info(msg)
    sys.exit()

