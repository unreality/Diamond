# coding=utf-8

"""
Collect icmp round trip times
Only valid for ipv4 hosts currently

#### Dependencies

 * ping

#### Configuration

Configuration is done by adding in extra keys like this

 * target_1=example.org
 * target_fw=192.168.0.1
 * target_localhost=localhost

Results in metrics:
 * server.hostname.ping.example_org 11
 * server.hostname.ping.192_168_0_1 34
 * server.hostname.ping.localhost 66

Option use_target_names changes it to:
 * server.hostname.ping.1 11
 * server.hostname.ping.fw 34
 * server.hostname.ping.localhost 66

"""

import subprocess
import diamond.collector
import os
from diamond.collector import str_to_bool


class PingCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(PingCollector, self).get_default_config_help()
        config_help.update({
            'bin':         'The path to the ping binary',
            'use_sudo':    'Use sudo?',
            'sudo_cmd':    'Path to sudo',
            'use_target_names': 'Use target suffixes as metric names'
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(PingCollector, self).get_default_config()
        config.update({
            'path':             'ping',
            'bin':              '/bin/ping',
            'use_sudo':         False,
            'sudo_cmd':         '/usr/bin/sudo',
            'use_target_names': False
        })
        return config

    def collect(self):
        for key in self.config.keys():
            if key[:7] == "target_":
                host = self.config[key]

                if self.config['use_target_names']:
                    metric_name = key[7:].replace('.', '_')
                else:
                    metric_name = host.replace('.', '_')

                if not os.access(self.config['bin'], os.X_OK):
                    self.log.error("Path %s does not exist or is not executable"
                                   % self.config['bin'])
                    return

                command = [self.config['bin'], '-nq', '-c 1', host]

                if str_to_bool(self.config['use_sudo']):
                    command.insert(0, self.config['sudo_cmd'])

                ping = subprocess.Popen(
                    command, stdout=subprocess.PIPE).communicate()[0].strip(
                    ).split("\n")[-1]

                # Linux
                if ping.startswith('rtt'):
                    ping = ping.split()[3].split('/')[0]
                    metric_value = float(ping)
                # OS X
                elif ping.startswith('round-trip '):
                    ping = ping.split()[3].split('/')[0]
                    metric_value = float(ping)
                # Unknown
                else:
                    metric_value = 10000

                self.publish(metric_name, metric_value)
