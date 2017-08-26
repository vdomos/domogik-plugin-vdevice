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
import traceback

class VDeviceManager(Plugin):
    """
    """

    # -------------------------------------------------------------------------------------------------
    def __init__(self):
        """ Init plugin
        """
        Plugin.__init__(self, name='vdevice')

        # Check if the plugin is configured. If not, this will stop the plugin and log an error
        # if not self.check_configured():
        #	return

        # Get the devices list
        self.devices = self.get_device_list(quit_if_no_device=True)
        #self.log.info(u"==> device:   %s" % format(self.devices))

        self.sensors = {}
        self.vdevice_list = {}
        
        # Set vdevices list
        self.initDeviceList(self.devices)

        self.log.info(u"==> Add callback for new or changed devices.")
        self.register_cb_update_devices(self.myHandleDeviceUpdate)
        
        self.ready()

     
    # -------------------------------------------------------------------------------------------------
    def initDeviceList(self, devices):
        # Get the sensors id per device:
        self.sensors = self.get_sensors(devices)
        #self.log.info(u"==> sensors: %s" % format(self.sensors))	    # INFO ==> sensors: {66: {u'virtual_number': 159}, ...}  =>  ('device id': {'sensor name': 'sensor id'})
        
        self.log.info(u"==> Set vdevices list ...")
        for a_device in devices:                                            # for each device ...
            device_name = a_device["name"]					                # Ex.: "Max Temp Ext." ...
            device_id = a_device["id"]						                # Ex.: "128"
            sensor_type = self.sensors[device_id].keys()[0]                 # Ex.: "virtual_number" | "virtual_binary" | "virtual_string" | ...
            self.log.debug(u"==> Device '%s' (id:%s), Sensor: '%s'" % (device_name, device_id, self.sensors[device_id]))    # DEBUG ==> Device 'Max Temp Ext' (id:6), Sensor: '{u'virtual_number': 86}'
            self.vdevice_list[device_id] = device_name

            # Update device's sensor with device's parammeter if it's not set
            last_value = a_device['sensors'][sensor_type]['last_value']
            self.log.info(u"==> Last value for sensor's device '%s': %s" % (device_name, last_value))
            if last_value == None:
                value = self.get_parameter(a_device, "value")
                if sensor_type in ["virtual_binary", "virtual_switch", "virtual_openclose", "virtual_startstop", "virtual_motion"]:
                    value = '1' if value == "y" else '0'
                elif sensor_type in ["virtual_number"]:
                    if not self.is_number(value):
                        value = 0
                self.log.info(u"==> Device '%s' (id:%s), Update Sensor (%s) with initial device parameter value '%s'" % (device_name, device_id, self.sensors[device_id], value))
                # INFO ==> Device 'VNumber 1' (id:136), Update Sensor ({u'virtual_number': 445}) with initial device parameter value '0.0'
                self.send_data(device_id, value)
        
       

    # -------------------------------------------------------------------------------------------------
    def send_data(self, device_id, value):
        """ Send the value sensors values over MQ
        """
        data = {}
        if device_id not in self.vdevice_list:
            self.log.error("### Device ID '%s' unknown, have you restarted the plugin after device creation ?" % (device_id))
            return False, "Plugin vdevice: Unknown device ID %d" % device_id
         
        sensor_type = self.sensors[device_id].keys()[0]
        if sensor_type in ["virtual_number"]:
            if not self.is_number(value):
                errorstr = u"### Updating Sensor '%s' / id '%s' with value '%s' for device '%s': Not a number !" % (sensor_type, self.sensors[device_id][sensor_type], value, self.vdevice_list[device_id])
                self.log.error(errorstr)
                return False, errorstr
        elif sensor_type in ["virtual_binary", "virtual_switch", "virtual_openclose", "virtual_startstop", "virtual_motion"]:
            if value not in ['0', '1', 0, 1]:
                errorstr = u"### Updating Sensor '%s' / id '%s' with value '%s' for device '%s': Not a boolean !" % (sensor_type, self.sensors[device_id][sensor_type], value, self.vdevice_list[device_id])
                self.log.error(errorstr)
                return False, errorstr
        self.log.info("==> Update Sensor '%s' / id '%s' with value '%s' for device '%s'" % (sensor_type, self.sensors[device_id][sensor_type], value, self.vdevice_list[device_id]))
        # INFO ==> Update Sensor 'virtual_number' / id '445' with value '1' for device 'VNumber 1'
        data[self.sensors[device_id][sensor_type]] = value

        try:
            self._pub.send_event('client.sensor', data)
            self.log.info("==> 0MQ PUB sended = %s" % format(data))			# {u'id_sensor': u'value'} => {217: u'132'}
        except:
            # We ignore the message if some values are not correct ...
            self.log.debug(u"Bad MQ message to update sensor : {0}".format(data))
            return (False, "Vdevice, Bad MQ message to update sensor")

        return (True, None)


    # -------------------------------------------------------------------------------------------------
    def on_mdp_request(self, msg):
        """ Called when a MQ req/rep message is received
        """
        Plugin.on_mdp_request(self, msg)
        # self.log.info(u"==> Received 0MQ messages: %s" % format(msg))
        if msg.get_action() == "client.cmd":
            data = msg.get_data()
            self.log.info(u"==> Received 0MQ messages data: %s" % format(data))
            # INFO ==> Received 0MQ messages data: {u'command_id': 1, u'value': u'-17.9', u'device_id': 6}

            status, reason = self.send_data(data["device_id"], data["value"])

            self.log.info("Reply to command 0MQ")
            reply_msg = MQMessage()
            reply_msg.set_action('client.cmd.result')
            reply_msg.add_data('status', status)
            reply_msg.add_data('reason', reason)
            self.reply(reply_msg.get())


    # -------------------------------------------------------------------------------------------------
    #def on_message(self, msgid, content):
    #    Plugin.on_message(self, msgid, content)        # Transmit mq message to manager    
        
        
    # -------------------------------------------------------------------------------------------------
    def myHandleDeviceUpdate(self, devices):            # A methode to handle updated devices by callback
        self.log.info(u"==> DeviceUpdate called")
        #for device in devices:
        #    self.log.info(u" %s: '%s'" % (device['id'], device['name']))
        self.vdevice_list = {}
        self.initDeviceList(self.devices)


    # -------------------------------------------------------------------------------------------------
    def is_number(self, s):
        ''' Return 'True' if s is a number
        '''
        try:
            float(s)
            return True
        except ValueError:
            return False
        except TypeError:
            return False


if __name__ == "__main__":
    VDeviceManager()

