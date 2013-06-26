import socket

__author__ = 'unreality'


class AsteriskAMI(object):

    def __init__(self, host='127.0.0.1', port=5038, username=None, secret=None):

        self._host = host
        self._username = username
        self._secret = secret
        self._port = port

        self._events = 'off'
        self._logged_in = False

    def login(self):

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2.0)
        self._sock.connect((self._host, self._port))

        welcome_banner = self._sock.recv(1024)

        login_str = "Action: login\r\nUsername: %s\r\nSecret: %s\r\nEvents: %s\r\n\r\n" % (self._username,
                                                                                           self._secret,
                                                                                           self._events)

        self._sock.sendall(login_str)

        try:
            complete = False
            data = ""

            while not complete:
                data += self._sock.recv(4096)

                if '\r\n\r\n' in data:
                    complete = True

            lines = data.replace('\r', '').split('\n')
            for line in lines:
                if line.strip() != '':
                    (key, val) = line.lower().split(': ')

                    if key == 'response':
                        if val.strip() == 'success':
                            self._logged_in = True
                        else:
                            self._logged_in = False

        except socket.timeout, timeout_exception:
            pass

        return self._logged_in

    def iax_peers(self):
        return self._get_peer_list(action='IAXpeerlist')

    def sip_peers(self):
        return self._get_peer_list(action='SIPPeers')

    def channel_stats(self):
        cmd_output = self._run_command('core show channels')
        lines = cmd_output.split('\n')

        sip_channels = 0
        iax_channels = 0
        active_calls = 0
        active_channels = 0
        calls_processed = 0

        for line in lines:
            if 'active channels' in line:
                elems = line.split(' ')
                active_channels = int(elems[0])
            elif 'active calls' in line:
                elems = line.split(' ')
                active_calls = int(elems[0])
            elif 'calls processed' in line:
                elems = line.split(' ')
                calls_processed = int(elems[0])
            elif line.startswith('SIP/'):
                sip_channels += 1
            elif line.startswith('IAX2/'):
                iax_channels += 1

        return {'sip_channels': sip_channels,
                'iax_channels': iax_channels,
                'active_calls': active_calls,
                'active_channels': active_channels,
                'calls_processed': calls_processed}

    def _run_command(self, command):
        if self._logged_in:
            ami_command = "Action: Command\r\ncommand: %s\r\n\r\n" % command

            self._sock.sendall(ami_command)

            complete = False
            response = ""
            while not complete:
                response += self._sock.recv(1024)

                if '--END COMMAND--' in response:
                    complete = True

            elems = response.split('\r\n')

            return elems[2]

    def _get_peer_list(self, action):
        if self._logged_in:
            iaxpeers_cmd = "Action: %s\r\n\r\n" % action

            self._sock.sendall(iaxpeers_cmd)

            complete = False
            response = ""

            while not complete:
                response += self._sock.recv(1024)

                if 'PeerlistComplete' in response:
                    complete = True

            events = response.replace('\r', '').split('\n\n')

            peers = []
            for event in events:
                lines = event.strip().split('\n')

                peer_info = {}
                for line in lines:
                    if line.strip() != '':
                        try:
                            (key, val) = line.split(': ')
                            peer_info[key] = val.strip()
                        except ValueError:
                            print line

                try:
                    if peer_info['Event'] == 'PeerEntry':
                        peers.append(peer_info)
                except KeyError:
                    pass

            return peers

        return []

    def disconnect(self):
        self._sock.close()