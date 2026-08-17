# Charon

Charon is a small, portable KMIP server for Synology DSM, built with Bash, Python, and PyKMIP.
Its Python virtual environment is disposable and kept separate from the persistent certificates and KMIP state.

The idea is to keep it handy and run in foreground on-demand, as opposed to an always-on service.

### Credit
Based on [kmip-server-dsm](https://github.com/rnurgaliyev/kmip-server-dsm/tree/master) by rnurgaliyev.

### Usage
Run `./charon.sh` to view the available commands.

### Troubleshooting

If DSM reports that it cannot connect, SSH into the Synology NAS as an
administrator, become root (`sudo -i`), and follow the complete system journal:

```bash
journalctl -xef
```

Leave the command running while reproducing the failure in Control Panel.
