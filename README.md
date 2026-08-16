### DSM KMIP client logs

If DSM reports that it cannot connect, SSH into the Synology NAS as an
administrator, become root (`sudo -i`), and follow the complete system journal:

```bash
journalctl -xef
```

Leave the command running while reproducing the failure in Control Panel.
