# coding=utf-8

"""
AsteriskCollector uses the Asterisk Management Interface (AMI) to retrieve
channel and peer statistics.

#### Configuration

```
    # Options for AsteriskCollector
    host = localhost
    username = admin
    secret = adminsecret
    port = 5038
```

Example metrics:
```
    server.host.asterisk.iax_peers_total 234
    server.host.asterisk.sip_peers_total 3
    server.host.asterisk.sip_peers_connected 43
    server.host.asterisk.iax_peers_connected 42

```
"""
__author__ = 'unreality'

import diamond.collector
import ami


class AsteriskCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(AsteriskCollector, self).get_default_config_help()
        config_help.update({
            'host': 'Asterisk AMI Host',
            'username': 'Asterisk AMI Username',
            'secret': 'Asterisk AMI Secret',
            'port': 'Asterisk AMI Port'
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(AsteriskCollector, self).get_default_config()
        config.update({
            'host': 'localhost',
            'port': 5038,
            'username': None,
            'secret': None,
            'path': 'asterisk',
        })
        return config

    def collect(self):

        asterisk_ami = ami.AsteriskAMI(host=self.config['host'], port=self.config['port'],
                                       username=self.config['username'], secret=self.config['secret'])

        asterisk_ami.login()
        iax_peers = asterisk_ami.iax_peers()
        self.publish("iax_peers_total", len(iax_peers))

        sip_peers = asterisk_ami.sip_peers()
        self.publish("sip_peers_total", len(sip_peers))

        iax_connected = 0
        sip_connected = 0

        for iax_peer in iax_peers:
            if iax_peer.get('IPaddress', '(null)') != '(null)':
                iax_connected += 1

        for sip_peer in sip_peers:
            if 'OK' in sip_peer.get('Status', ''):
                sip_connected += 1

        self.publish("sip_peers_connected", sip_connected)
        self.publish("iax_peers_connected", iax_connected)

        channel_stats = asterisk_ami.channel_stats()

        for key,val in channel_stats.items():
            self.publish(key, val)

        asterisk_ami.disconnect()


