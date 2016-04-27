#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Virtual Device

Implements
==========

- VDeviceManager

@author: domos  (domos dt vesta at gmail dt com)
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.common.plugin import Plugin
from domogikmq.message import MQMessage
from domogikmq.reqrep.client import MQSyncReq

import json


class VDeviceManager(Plugin):
    """
    """

    def __init__(self):
        """ Init plugin
        """
        Plugin.__init__(self, name='vdevice')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        # if not self.check_configured():
        #	return

        # get the devices list
        self.devices = self.get_device_list(quit_if_no_device=True)
        # self.log.info(u"==> device:   %s" % format(self.devices))

        # get the sensors id per device:
        self.sensors = self.get_sensors(self.devices)
        # self.log.info(u"==> sensors:   %s" % format(self.sensors))	
        # INFO ==> sensors:   {66: {u'virtual_number': 159}}  =>  ('device id': {'sensor name': 'sensor id'})

        # for each device ...
        self.vdevice_namelist = {}
        for a_device in self.devices:
            device_name = a_device["name"]					                # Ex.: "Max Temp Ext." ...
            device_id = a_device["id"]						                # Ex.: "128"
            device_typeid = a_device["device_type_id"]		                # Ex.: "vdevice.number" | "vdevice.binary" | "vdevice.string" | ...
            sensor_name = device_typeid.replace("vdevice.","virtual_")      # Ex.: "virtual_number" | "virtual_binary" | "virtual_string" | ...
            sensor_id = self.sensors[device_id][sensor_name]
            self.log.info(u"==> Device '%s' (id:%s / %s), Sensor: '%s'" % (device_name, device_id, device_typeid, self.sensors[device_id]))
            # INFO ==> Device 'VDevice Number 1' (id:113 / vdevice.number), Sensor: '{u'virtual_number': 217}'
            self.vdevice_namelist[device_id] = device_name

            # Update device's sensor with device's parammeter if it's not set
            if not self.sensorMQValueIsSet(sensor_id):
                value = self.get_parameter(a_device, "value")
                if device_typeid in ["vdevice.binary", "vdevice.switch", "vdevice.openclose", "vdevice.startstop", "vdevice.motion"]:
                    if value == "y": value = 1
                    else: value = 0
                elif device_typeid == "vdevice.number":
                    if not self.is_number(value):
                        value = 0
                self.log.info(u"==> Device '%s' (id:%s / %s), Update Sensor (id:%s) with initial device parameter value '%s'" % (device_name, device_id, device_typeid, sensor_id, value))
                self.send_data(device_id, value)
            
        # Subscribte to MQ message "device-new et device.update"
        self.log.info(u"==> Add listener for new or changed devices.")
        self.add_mq_sub("device.update")
        
        self.ready()



    def sensorMQValueIsSet(self, id):
        """  REQ/REP message to get sensor value
        """
        msg = MQMessage()
        msg.set_action('sensor_history.get')
        msg.add_data('sensor_id', id)
        msg.add_data('mode', 'last')
        mq_client = MQSyncReq(self.zmq)
        try:
            sensor_history = mq_client.request('dbmgr', msg.get(), timeout=10).get()
            # ['sensor_history.result', '{"status": true, "reason": "", "sensor_id": 242, "values": [{"timestamp": 1456221006, "value_str": "2797", "value_num": 2797.0}], "mode": "last"}']
            # ['sensor_history.result', '{"status": true, "reason": "", "sensor_id": 300, "values": null, "mode": "last"}']
            sensor_last = json.loads(sensor_history[1])
            if sensor_last['status'] == True and sensor_last['values']:
                sensor_value = sensor_last['values'][0]['value_str']
                self.log.info(u"==> 0MQ REQ/REP: Last sensor value: %s" % sensor_value)
                return True
            else:
                self.log.info(u"==> 0MQ REQ/REP: Last sensor status: null")
                return False
        except AttributeError:
            self.log.error(u"### 0MQ REQ/REP: '%s'", format(traceback.format_exc()))
            return False
        

    def send_data(self, device_id, value):
        """ Send the value sensors values over MQ
        """
        data = {}
        if device_id not in self.vdevice_namelist:
            self.log.error("### Device ID '%s' unknown, have you restarted the plugin after device creation ?" % (device_id))
            return False, "Plugin vdevice: Unknown device ID %d" % device_id
            
        for sensor in self.sensors[device_id]:
            self.log.info("==> Update Sensor '%s' / id '%s' with value '%s' for device '%s'" % (sensor, self.sensors[device_id][sensor], value, self.vdevice_namelist[device_id]))
            # INFO ==> Update Sensor 'get_info_number' / id '217' with value '132' for device 'VDevice Number 1'
            data[self.sensors[device_id][sensor]] = value

        try:
            self._pub.send_event('client.sensor', data)
            self.log.info("==> 0MQ PUB sended = %s" % format(data))			# {u'id_sensor': u'value'} => {217: u'132'}
        except:
            # We ignore the message if some values are not correct ...
            self.log.debug(u"Bad MQ message to send. This may happen due to some invalid sensor data. MQ data is : {0}".format(data))
            return (False, "Vdevice, Bad MQ message to update sensor")

        return (True, None)


    def on_mdp_request(self, msg):
        """ Called when a MQ req/rep message is received
        """
        Plugin.on_mdp_request(self, msg)
        # self.log.info(u"==> Received 0MQ messages: %s" % format(msg))
        if msg.get_action() == "client.cmd":
            data = msg.get_data()
            self.log.info(u"==> Received 0MQ messages data: %s" % format(data))
            # ==> Received 0MQ messages data: {u'command_id': 35, u'value': u'1', u'device_id': 112}
            # ==> Received 0MQ messages data: {u'command_id': 36, u'value': u'128', u'device_id': 113}
            # ==> Received 0MQ messages data: {u'command_id': 37, u'value': u'Bonjour', u'device_id': 114}

            status, reason = self.send_data(data["device_id"], data["value"])

            self.log.info("Reply to command 0MQ")
            reply_msg = MQMessage()
            reply_msg.set_action('client.cmd.result')
            reply_msg.add_data('status', status)
            reply_msg.add_data('reason', reason)
            self.reply(reply_msg.get())


    def on_message(self, msgid, content):
        self.log.info(u"==> New pub message '{0}'".format(msgid))   # 'device.update'
        self.log.info(u"Message content : {0}".format(content))
        # {u'client_id': u'plugin-vdevice.hades', u'device_id': 59}
        # {u'client_id': u'plugin-script.hades', u'device_id': 64}
        if  content['client_id'] != 'plugin-vdevice.hades':         # hostname à supprimer
            self.log.debug("PUB message 'device.update' not for vdevice plugin.")
            return
        


    def is_number(self, s):
        ''' Return 'True' if s is a number
        '''
        try:
            float(s)
            return True
        except ValueError:
            return False


if __name__ == "__main__":
    VDeviceManager()

