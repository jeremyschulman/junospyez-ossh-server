from threading import Thread
import socket
import json

from jnpr.junos import Device
from jnpr.junos.exception import ConnectError
from junospyez_ossh_server.log import log


def gather_basic_facts(device):
    """
    Using the provide Junos Device object, retrieve basic facts about the device.

    Parameters
    ----------
    device : Device
        The Junos device instance

    Returns
    -------
    dict
        A collection of basic facts about the device that will be stored in the database.
    """
    # -----------------------------------------------------
    # get information from the provided device facts object
    # -----------------------------------------------------

    basic_facts = dict()
    basic_facts['os_version'] = device.facts['version']
    basic_facts['hostname'] = device.facts['hostname']
    basic_facts['device_sn'] = device.facts['serialnumber']
    basic_facts['device_model'] = device.facts['model']

    # -------------------------------------------------------------------------------
    # need to do a route lookup using the outbound ssh config to determine the actual
    # management interface used to reach this service.  For now, use the first
    # server ip-address (name).  It is possible that the device could be configured
    # with multiple ossh clients.  If we need to support this use-case, then we will
    # need to add additional checks for specific client name.
    # -------------------------------------------------------------------------------

    config = device.rpc.get_config(filter_xml='system/services/outbound-ssh')
    servers = config.xpath('.//servers/name')
    server_ipaddr = servers[0].text

    # -----------------------------------------------------------------------------------
    # get mgmt_interface value from the route lookup.  The route lookup will give use the
    # logical interface name, which we will also need for finding the assigned ip-address
    # -----------------------------------------------------------------------------------

    resp = device.rpc.get_route_information(destination=server_ipaddr)
    if_name = resp.xpath('.//via | .//nh-local-interface')[0].text
    basic_facts['mgmt_interface'] = if_name.partition('.')[0]   # physical interface

    # -------------------------------------------------------------
    # get mgmt_ipaddr from the if_name obtained by the route lookup
    # -------------------------------------------------------------

    if_info = device.rpc.get_interface_information(interface_name=if_name, terse=True)
    basic_facts['mgmt_ipaddr'] = if_info.findtext('.//ifa-local').partition('/')[0].strip()

    # ----------------------------------------------------------
    # get mgmt_macaddr value assigned to the management interface
    # ----------------------------------------------------------

    resp = device.rpc.get_interface_information(interface_name=basic_facts['mgmt_interface'], media=True)
    found = resp.findtext('.//current-physical-address').strip()
    basic_facts['mgmt_macaddr'] = found

    return basic_facts


class OutboundSSHServer(object):
    NAME = 'outbound-ssh-server'
    DEFAULT_LISTEN_BACKLOG = 10

    def __init__(self, ipaddr, port, login_user, login_password):
        """
        Parameters
        ----------
        ipaddr : str
            The server IP address

        port : int
            The server port to accept requests

        login_user : str
            The device login user name

        login_password : str
            The device login password
        """

        self.thread = None
        self.socket = None
        self.login_user = login_user
        self.login_password = login_password
        self.bind_ipaddr = ipaddr
        self.bind_port = int(port)
        self.listen_backlog = OutboundSSHServer.DEFAULT_LISTEN_BACKLOG

        self.on_device = None     # callable provided at :meth:`start`
        self.on_error = None      # callable provided at :meth:`start`

    @property
    def name(self):
        return self.__class__.NAME

    def _setup_server_socket(self):
        s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_sock.bind((self.bind_ipaddr, self.bind_port))
        s_sock.listen(self.listen_backlog)
        self.socket = s_sock

    def _server_thread(self):
        """
        This is the running thread target for the outbound-ssh server.  The purpose of this thread
        is to await inbound connections from the Junos devices and then spawn a specific thread for that device
        for future processing.
        """

        try:
            self._setup_server_socket()

        except Exception as exc:
            log.error(f'{self.name}: failed to setup socket: %s' % str(exc))
            return

        while True:

            # await a device to make an outbound connection.  The socket accept() returns a tuple
            # (socket, (device ipaddr, device port)).  create a new thread to process the inbound with
            # this information

            try:

                in_sock, (in_addr, in_port) = self.socket.accept()

            except ConnectionAbortedError:
                # this triggers when the server socket is closed by the shutdown() method
                log.info(f'{self.name} shutting down')
                return

            in_str = f'{in_addr}:{in_port}'
            dev_name = f'device-{in_str}'
            log.info(f'{self.name}: accepted connection from {in_str}')

            # spawn a device-specific thread for further processing

            try:
                Thread(name=dev_name, target=self._device_thread,
                       kwargs=dict(in_sock=in_sock, in_addr=in_addr, in_port=in_port)).start()

            except RuntimeError as exc:
                log.err(f'{self.name}: ERROR: failed to start processing {in_addr}: %s' % str(exc))
                in_sock.close()
                continue

        # NOT REACHABLE
        log.critical('Unreachable code reached')

    def _device_thread(self, in_sock, in_addr, in_port):
        """
        This is a thread target function that is launched by the OSSH service.  The purpose of this function
        is to make a NETCONF connection back to the device, gather basic facts, and store them into the database.

        If all goes well, the `facts` field in the database will contain the information about the device.  If
        all does not go well, then there is an "error" field within the facts that the caller can example.  The
        most likely error reason is the provided user name and password values are not correct.

        Parameters
        ----------------
        in_addr: str
            the Junos device management IP address that connected to the OSSH service

        in_sock: socket
            the socket instance from the outbound connection.
        """

        via_str = f'{in_addr}:{in_port}'

        sock_fd = in_sock.fileno()

        # attempt to add this device entry to the database; the unique ID is the IP address.
        # it is AOK if the entry already exists as the device-thread will simply update the record with the
        # information retrieved

        try:
            log.info(f"establishing netconf to device via: {via_str}")
            dev = Device(sock_fd=sock_fd, user=self.login_user, password=self.login_password)
            dev.open()

        except ConnectError as exc:
            log.error(f'Connection error to device via {via_str}: {exc.msg}')
            in_sock.close()
            return

        except Exception as exc:
            log.error(f'unable to establish netconf to device via {via_str}: {str(exc)}')
            in_sock.close()

        try:
            log.info(f"gathering basic facts from device via: {via_str}")
            facts = gather_basic_facts(dev)
            log.info(json.dumps(facts, indent=3))

            # call user on-device callback
            self.on_device(device=dev, facts=facts)

            log.info(f"completed device with management IP address: {facts['mgmt_ipaddr']}")
            dev.close()

        except Exception as exc:
            error = f"ERROR: unable to process device {in_addr}:{in_port}: %s" % str(exc)
            log.error(error)
            if self.on_error:
                self.on_error(dev, exc)

        finally:
            in_sock.close()

    def start(self, on_device, on_error=None):
        if self.socket:
            log.error(f'{self.name} already running')
            return False

        if not callable(on_device):
            raise ValueError(f'on_device is not callable')

        if on_error and not callable(on_error):
            raise ValueError(f'on_error is not callable')

        log.info(f'{self.name}: starting on {self.bind_ipaddr}:{self.bind_port}')

        self.on_device = on_device
        self.on_error = on_error

        try:
            self.thread = Thread(name=self.name, target=self._server_thread)
            self.thread.start()

        except Exception as exc:
            log.error(f'{self.name} unable to start: %s' % str(exc))
            return False

        log.info(f'{self.name}: started')
        return True

    def stop(self):
        self.socket.close()
        self.thread = None
        self.socket = None
