# coding=utf-8

"""
The GenericSNMPCollector is for collecting SNMP data from multiple hosts easily.

#### Configuration

Below is an example configuration for the GenericSNMPCollector. The collector
can collect data any number of devices by adding configuration sections
under the *devices* header.

```
    # Options for GenericSNMPCollector
    path = snmp
    interval = 60

    [devices]

    [[router1]]
    url=snmp://host_address/community_string
    hostname=com.example.router
    path=path_override
    [[[oids]]]
    1.3.6.1.4.1.20632.2.2=oid_metric_name
    1.3.6.1.4.1.20632.2.3=outQueueSize


    [[router2]]
    url=snmp://host_address/community_string
    hostname=com.example.router2
    path=path_override
    [[[oids]]]
    1.3.6.1.4.1.20632.2.2=oid_metric_name
    1.3.6.1.4.1.20632.2.3=outQueueSize
```

This configuration results in the metrics:
```
    server.com.example.router.path_override.oid_metric_name 453
    server.com.example.router.path_override.outQueueSize 455
    server.com.example.router2.path_override.oid_metric_name 453
    server.com.example.router2.path_override.outQueueSize 455
```

hostname and path can be defined per-device, which allows you to place the
result values into any path you wish.

#### Dependencies

 * pysmnp

"""
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi.error import WrongValueError
from socket import gaierror
import diamond.collector
from urlparse import urlparse

__author__ = 'unreality'


class GenericSNMPCollector(diamond.collector.Collector):
    saved_hostname = None
    saved_path = None

    def collect(self):
        devices = self.config.get('devices', [])

        self.saved_hostname = self.config.get('hostname', None)
        self.saved_path = self.config.get('path', None)

        for device in devices:
            device_url = self.config['devices'][device].get('url', None)
            parsed_url = urlparse(device_url)

            parsed_host = parsed_url.netloc or parsed_url.path
            parsed_port = parsed_url.port or 161
            parsed_community = parsed_url.path or 'public'
            if parsed_community[0] == '/':
                parsed_community = parsed_community[1:]

            self.log.debug("Trying %s@%s:%s" % (parsed_community, parsed_host, parsed_port))

            if 'hostname' in self.config['devices'][device]:
                host_override = self.config['devices'][device]['hostname']
            else:
                host_override = None

            if 'path' in self.config['devices'][device]:
                path_override = self.config['devices'][device]['path']
            else:
                path_override = None

            try:
                if 'timeout' in self.config['devices'][device]:
                    timeout = int(self.config['devices'][device]['timeout'])
                elif 'timeout' in self.config:
                    timeout = int(self.config['timeout'])
                else:
                    timeout = 2
            except ValueError:
                timeout = 2

            if 'oids' in self.config['devices'][device]:
                for oid in self.config['devices'][device]['oids']:
                    self.log.debug("Getting %s (%s)" % (self.config['devices'][device]['oids'][oid], oid))

                    try:
                        metric_val = self._snmp_get_val(host=parsed_host, port=parsed_port,
                                                        community=parsed_community, oid_str=oid, timeout=timeout)
                    except WrongValueError, e:
                        self.log.error("Could not get %s from %s:" % (oid, parsed_host))
                        self.log.error(e)
                        continue

                    #get out if we couldnt get the value for whatever reason, usually means timeout or something
                    if metric_val is None:
                        break

                    if host_override:
                        self.config['hostname'] = host_override

                    if path_override:
                        self.config['path'] = path_override

                    self.publish(name=self.config['devices'][device]['oids'][oid], value=metric_val)

                    if self.saved_hostname is not None:
                        self.config['hostname'] = self.saved_hostname
                    if self.saved_path is not None:
                        self.config['path'] = self.saved_path

            if 'hostname' in self.config:
                if self.config['hostname'] is None or self.config['hostname'] == host_override:
                    del(self.config['hostname'])
            if 'path' in self.config:
                if self.config['path'] is None or self.config['path'] == path_override:
                    del(self.config['path'])

    def get_default_config_help(self):
        config_help = super(GenericSNMPCollector, self).get_default_config_help()
        config_help.update({
            'timeout': 'Time to wait before SNMP Agent gives up',
        })
        return config_help

    def get_default_config(self):
        """
        Return default config

        :rtype: dict

        """
        config = super(GenericSNMPCollector, self).get_default_config()
        config.update({
            'path': 'genericsnmp',
            'timeout': 2,
        })
        return config

    def _convert_oid(self, oid):
        oid_split = oid.split('.')
        oid_n = []
        for i in oid_split:
            oid_n.append(int(i))

        oid_tuple = tuple(oid_n)

        return oid_tuple

    def _snmp_get_val(self, host, port, community, oid_str, timeout=2):
        try:
            oid = self._convert_oid(oid_str)
            udp_transport_target = cmdgen.UdpTransportTarget((host, port), timeout)
            community_data = cmdgen.CommunityData('diamond-agent', community, 0)
            errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(community_data,
                                                                                                  udp_transport_target,
                                                                                                  oid
                                                                                                  )

            if errorIndication:
                self.log.error(errorIndication)
            else:
                if errorStatus:
                    self.log.error('%s at %s\n' % (errorStatus.prettyPrint(),
                                                   errorIndex and varBinds[int(errorIndex)-1] or '?'))

                else:
                    for name, val in varBinds:
                        return val.prettyPrint()
        except gaierror:
            return None

        return None