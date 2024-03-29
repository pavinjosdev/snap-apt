# snap-apt
Based on [snap-pac](https://github.com/wesbarnett/snap-pac) by Wes Barnett and [apt-btrfs-snapper](https://github.com/xhess/apt-btrfs-snapper) by xhess.

## Synopsis
This is a set of [APT](https://en.wikipedia.org/wiki/APT_(software)) hook and script
that automatically causes [snapper](http://snapper.io/) to perform a pre and post
snapshot before and after APT transactions, similar to how YaST does with OpenSuse.
This provides a simple way to undo changes to a system after an APT transaction.

## Installation
```
git clone https://github.com/pavinjosdev/snap-apt.git
chmod 755 snap-apt/scripts/snap_apt.py
cp snap-apt/scripts/snap_apt.py /usr/bin/snap-apt
cp snap-apt/hooks/80snap-apt /etc/apt/apt.conf.d/
cp snap-apt/logrotate/snap-apt /etc/logrotate.d/
rm -f /etc/apt/apt.conf.d/80snapper
sed -i 's/DISABLE_APT_SNAPSHOT="no"/DISABLE_APT_SNAPSHOT="yes"/g' /etc/default/snapper
```

## Uninstallation
```
rm -f /usr/bin/snap-apt
rm -f /etc/apt/apt.conf.d/80snap-apt
rm -f /etc/logrotate.d/snap-apt
sed -i 's/DISABLE_APT_SNAPSHOT="yes"/DISABLE_APT_SNAPSHOT="no"/g' /etc/default/snapper
```

## Configuration
Most likely, configuration is not needed.
By default, the snapper configuration named
`root` will have pre/post snapshots taken for every APT transaction.

## Troubleshooting
By default, the log is written to `/var/log/snap-apt.log`.
To enable debug output, set constant `DEBUG = True` in `/usr/bin/snap-apt`.
