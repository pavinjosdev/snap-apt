#!/usr/bin/env python3

import os
import sys
import json
import logging
import subprocess

# Constants
SNAPPER_CONF = "root" # snapper config name
DESC_LEN = 72 # snapshot description max length
TMP_FILE = "/tmp/snap-apt.json" # file to store temp data
LOG_FILE = "/tmp/snap-apt.log" # file to log events

# Setup logging
logging.basicConfig(filename=LOG_FILE, format="%(asctime)s: %(levelname)s: %(message)s", level=logging.INFO)

# Function to get output of shell command
def shell_exec(command):
    res = subprocess.run(command, shell=True, capture_output=True, encoding="utf8", errors="replace")
    if res.stderr:
        msg = f"Probable issue executing shell command {command} :: {res.stderr.strip()}"
        logging.warning(msg)
    return res.stdout.strip()

# Function to generate snapper description
def gen_desc(prefix, action, packages):
    description = f"{prefix}: {action} {','.join(packages)}"
    if len(description) > DESC_LEN:
        short_pkg_name = f"{packages[0]}" if len(packages[0]) <= 32 else f"{packages[0][:30]}.."
        description = f"{prefix}: {action} {short_pkg_name} plus {len(packages) -1} packages"
    return description

# Get action arg
action = sys.argv.pop()
if action not in ["pre", "post"]:
    msg = "Error: Invalid argument, must be either pre or post"
    print(msg)
    logging.warning(msg)
    sys.exit(1)

# Get path to apt
apt_path = shell_exec("command -v apt")

# Get path to snapper
snapper_path = shell_exec("command -v snapper")

if not (apt_path or snapper_path):
    msg = f"Error: Cannot find apt and/or snapper in PATH ({os.environ.get('PATH')}) for user {os.environ.get('USER')}"
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
    apt_action = "install" if pkg_names else None
    # get all package names for comparison later
    if not apt_action:
        pkg_names = shell_exec("apt list --installed | cut -d '/' -f 1").split()
    # take snapper pre snapshot
    snapper_description = gen_desc("Before apt", apt_action, pkg_names)
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
    pkg_names = saved_obj["pkg_names"]
    snapper_description = gen_desc("After apt", apt_action, pkg_names)
    if not apt_action:
        old_packages = pkg_names
        new_packages = shell_exec("apt list --installed | cut -d '/' -f 1").split()
        removed_packages = list( set(old_packages) - set(new_packages) )
        # update description of pre snapshot
        apt_action = "remove"
        snapper_description = gen_desc("Before apt", apt_action, removed_packages)
        command = f"{snapper_path} -c {SNAPPER_CONF} modify -d '{snapper_description}' {pre_num}"
        shell_exec(command)
        snapper_description = gen_desc("After apt", apt_action, removed_packages)
    # take snapper post snapshot
    command = f"{snapper_path} -c {SNAPPER_CONF} create -t post -c number --pre-number {pre_num} -p -d '{snapper_description}'"
    post_num = shell_exec(command)
    os.remove(TMP_FILE)
    msg = f"Successfully created post APT snapshot with ID {post_num} in reference to pre snapshot {pre_num}"
    print(msg)
    logging.info(msg)
    sys.exit()

