# Outbound SSH Server for use with Junos PyEZ

Provides the server for use with the Junos outbound ssh feature.

# About Outbound SSH

Junos based networking systems support a feature called "outbound ssh".  This feature instructs
the Junos device to create an SSH session to a remote server.  For example, the following Junos
configuration will instruct the Junos device to create an outbound SSH connection to a server
at IP address 192.168.229.1 on port 9000

````
system {
    services {
        outbound-ssh {
            client netnoob {
                device-id netnoob;
                services netconf;
                192.168.229.1 port 9000;
            }
        }
}
````

The purpose of the OSSH server is to accept this outbound connection and allow then perform
NETCONF commands.

# Example Usage

## Create the Server

The following creates a server that listens to any IP interface on the host (0.0.0.0) on port 9000.
When the inbound connection is made, the server will then establish a NETCONF session with the
device using the login user 'admin' and the password 'juniper123'.  

````python
from junospyez_ossh_server import OutboundSSHServer

server = OutboundSSHServer('0.0.0.0', port=9000, login_user='admin', login_password='juniper123')
````

## Starting the Server

When the server establishes the NETCONF session a user-provided callback will be invoked with
the Junos PyEZ device object and a dictionary of basic facts.  For example:

````python

import json

def dump_device_facts(device, facts):
    print("GOT FACTS: ", json.dumps(facts, indent=3))


server.start(on_device=dump_device_facts)
````

The following is example output to illustrate the facts that are gathered as part of the server
functionality.

```text
GOT FACTS:  {
   "os_version": "15.1X53-D59.3",
   "hostname": "JX0218140351",
   "device_sn": "JX0218140351",
   "device_model": "EX2300-48T",
   "mgmt_interface": "vme",
   "mgmt_ipaddr": "192.168.230.13",
   "mgmt_macaddr": "f0:4b:3a:fe:4a:22"
}
```

As a developer, you can create an `on_device` callback function that performs any NETCONF RPC that
the login_user is allowed to do.

## Logging

The server package includes a `log` module so you can easily control the aspects of logging.  The
logger is a property of the server instance.  For example, you could output all INFO level
logs to stdout using the following:

```python
import logging

server.logger.setLevel(logging.INFO)
server.logger.addHandler(logging.StreamHandler())

server.start(on_device=dump_device_facts)
```

Would result in the following stdout:

```text
outbound-ssh-server: starting on 0.0.0.0:9000
outbound-ssh-server: started
outbound-ssh-server: accepted connection from 192.168.230.13:62572
establishing netconf to device via: 192.168.230.13:62572
gathering basic facts from device via: 192.168.230.13:62572
{
   "os_version": "15.1X53-D59.3",
   "hostname": "JX0218140351",
   "device_sn": "JX0218140351",
   "device_model": "EX2300-48T",
   "mgmt_interface": "vme",
   "mgmt_ipaddr": "192.168.230.13",
   "mgmt_macaddr": "f0:4b:3a:fe:4a:22"
}
completed device with management IP address: 192.168.230.13
GOT FACTS:  {
   "os_version": "15.1X53-D59.3",
   "hostname": "JX0218140351",
   "device_sn": "JX0218140351",
   "device_model": "EX2300-48T",
   "mgmt_interface": "vme",
   "mgmt_ipaddr": "192.168.230.13",
   "mgmt_macaddr": "f0:4b:3a:fe:4a:22"
}
```

## Stopping the Server

To shutdown the server use the `stop` method:

````python
server.stop()
````


