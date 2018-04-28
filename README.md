# linuxmuster-mail

Scripts and configuration files to setup a full featured docker mailcontainer for linuxmuster.net.

Skripte und Konfigurationsdateien für linuxmuster.net zur Einrichtung eines voll ausgestatteten Docker-Mailservers.

- Verwendet das [Dockerimage](https://hub.docker.com/r/tvial/docker-mailserver/) von [Thomas Vial](https://hub.docker.com/r/tvial).

- Legt unterhalb von _/srv/docker/linuxmuster-mail_
  - die Docker-Steuerdatei  [docker-compose.yml](https://github.com/linuxmuster/linuxmuster-mail/blob/master/share/templates/docker/docker-compose.yml) und diverse Bashskripte an.
  - Die Start- und Stopskripte werden von Systemd zur Steuerung des Dienstes verwendet.
  - Das Skript _exec.sh_ dient zur Ausführung von Shell-Befehlen innerhalb des laufenden Containers:
    `./exec.sh /bin/bash`  
    Startet eine Shell innerhalb des Containers.
