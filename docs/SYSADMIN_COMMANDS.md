# Sysadmin Command Allowlist

This document preserves the sysadmin command list that was provided for Apmatia's read-only system audit tool.

Important:

- These commands are intended for inspection and diagnosis only.
- They are not a general shell-execution interface.
- Shell redirection, pipes, chaining, and `sudo` are intentionally out of scope for the safe audit provider.
- Some entries below use placeholders like `[service]`, `[host]`, or `[path]` to show how the command is meant to be used.

## Essential Commands

### System Information and Uptime

- `uname -a`
- `hostname`
- `uptime`
- `cat /etc/os-release`
- `df -h`
- `df -i`
- `free -h`
- `cat /proc/meminfo`
- `lscpu`

### Process Monitoring

- `ps aux`
- `ps -ef`
- `top -b -n 1`
- `pgrep [pattern]`
- `pgrep -a [pattern]`

### Network Configuration

- `ip addr`
- `ip route`
- `netstat -tulpn`
- `ss -tulpn`
- `ping -c 3 [host]`
- `curl -I [url]`

### Service Management

- `systemctl status [service]`
- `systemctl list-units --type=service`
- `systemctl is-active [service]`

### User and Authentication

- `whoami`
- `id`
- `who`
- `last -5`
- `groups`

### File System and Configuration

- `ls -la [path]`
- `stat [file]`
- `find /path -name [pattern]`
- `cat [config_file]`
- `head -20 [file]`
- `tail -20 [file]`

### Logs

- `journalctl -n 50`
- `journalctl -u [service] -n 50`
- `cat /var/log/auth.log`
- `cat /var/log/syslog`
- `dmesg`
- `tail -20` on `dmesg` output is a useful read-only pattern, but it should be performed as separate commands in a safe tool rather than as a shell pipeline.

### Package Management

- `dpkg -l`
- `apt list --installed`
- `pip list`

## High-Value Commands

- `lsof -i`
- `du -sh [path]`
- `find /path -mtime +30`
- `grep -r [pattern] /path`
- `crontab -l`
- `ls /etc/cron.d/`
- `iptables -L`
- `ufw status`
- `ssl-cert-check`
- `openssl x509 -in [cert] -noout -dates`

## Uncertain But Potentially Useful

- `tcpdump -c 10`
- `nmap -sP 192.168.1.0/24`
- `fail2ban-client status`
- `logrotate -d /etc/logrotate.conf`
- `auditctl -l`
- `selinuxenabled`
- `getenforce`
- `ss -s`
- `nstat`
- `ip -s link`
- `ethtool [interface]`
- `lspci`
- `lsblk`
- `blkid`

## Commands To Avoid

These were explicitly called out as out of scope for read-only audit work:

- Any `sudo` command
- `rm`, `mv`, `cp`
- `chmod`, `chown`
- `apt install`, `apt remove`
- `systemctl start`, `systemctl stop`, `systemctl restart`
- `useradd`, `userdel`
- `passwd`
- `iptables -A`, `iptables -D`
- `echo > /etc/...`

## Notes

The current Apmatia safe system-audit tool uses an allowlist that covers the read-only inspection commands above. If you want a new command added later, it should be implemented as a deliberate backend change rather than exposed as arbitrary shell access.
