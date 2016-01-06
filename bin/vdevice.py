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

$ curl -s 'http://hermes:40406/rest/cmd/id/36?value=260' ; sleep 1; curl -s 'http://hermes:40406/rest/sensorhistory/id/217/last/1'; echo

@author: domos  (domos dt vesta at gmail dt com)
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.common.plugin import Plugin
from domogikmq.message import MQMessage


class VDeviceManager(Plugin):
	"""
	"""

	def __init__(self):
		""" Init plugin
		"""
		Plugin.__init__(self, name='vdevice')

		# check if the plugin is configured. If not, this will stop the plugin and log an error
		#if not self.check_configured():
		#	return

		# get the devices list
		self.devices = self.get_device_list(quit_if_no_device = True)
		#self.log.info(u"==> device:   %s" % format(self.devices))

		# get the sensors id per device : 
		self.sensors = self.get_sensors(self.devices)
		#self.log.info(u"==> sensors:   %s" % format(self.sensors))		# INFO ==> sensors:   {66: {u'set_info_number': 159}}  ('device id': 'sensor name': 'sensor id')

		# for each device ...
		self.vdevice_namelist = {}
		for a_device in self.devices:
			# global device parameters
			device_name = a_device["name"]										# Ex.: "Conso Elec Jour"
			device_id = a_device["id"]											# Ex.: "128"
			device_typeid = a_device["device_type_id"]							# Ex.: "vdevice.info_number | vdevice.info_binary | vdevice.info_string"
			self.log.info(u"==> Device '%s' (id:%s / %s), Sensor: '%s'" % (device_name, device_id, device_typeid, self.sensors[device_id]))
			# INFO ==> Device 'VDevice Binary 1' (id:112 / vdevice.info_binary), Sensor: '{u'get_info_binary': 216}'
			# INFO ==> Device 'VDevice Number 1' (id:113 / vdevice.info_number), Sensor: '{u'get_info_number': 217}'
			# INFO ==> Device 'VDevice String 1' (id:114 / vdevice.info_string), Sensor: '{u'get_info_string': 218}'
			self.vdevice_namelist[device_id] = device_name ;

		self.ready()




	def send_data(self, device_id, value):
		""" Send the value sensors values over MQ
		"""
		data = {}
		try:
			device_name = self.vdevice_namelist[device_id]
		except KeyError:
			self.log.error("### Device ID '%s' unknown, have you restarted the plugin after device creation ?" %  device_id)
			return

		for sensor in self.sensors[device_id]:
			self.log.info("==> Update Sensor '%s' / id '%s' with value '%s' for device '%s'" % (sensor, self.sensors[device_id][sensor], value, device_name))
			# INFO ==> Update Sensor 'get_info_number' / id '217' with value '132' for device 'VDevice Number 1'
			data[self.sensors[device_id][sensor]] = value
		self.log.info("==> 0MQ PUB sended = %s" % format(data))			#  {u'id_sensor': u'value'} => {217: u'132'}

		try:
			self._pub.send_event('client.sensor', data)
		except:
			# We ignore the message if some values are not correct ...
			self.log.debug(u"Bad MQ message to send. This may happen due to some invalid sensor data. MQ data is : {0}".format(data))
			pass



	def on_mdp_request(self, msg):
		""" Called when a MQ req/rep message is received
		"""
		Plugin.on_mdp_request(self, msg)
		#self.log.info(u"==> Received 0MQ messages: %s" % format(msg))
		if msg.get_action() == "client.cmd":
			data = msg.get_data()
			self.log.info(u"==> Received 0MQ messages data: %s" % format(data))
			# ==> Received 0MQ messages data: {u'command_id': 35, u'value': u'1', u'device_id': 112}
			# ==> Received 0MQ messages data: {u'command_id': 36, u'value': u'128', u'device_id': 113}
			# ==> Received 0MQ messages data: {u'command_id': 37, u'value': u'Bonjour', u'device_id': 114}
			
			self.send_data(data["device_id"], data["value"])

			self.log.info("Reply to command 0MQ")
			reason = None
			status = True
			reply_msg = MQMessage()
			reply_msg.set_action('client.cmd.result')
			reply_msg.add_data('status', status)
			reply_msg.add_data('reason', reason)
			self.reply(reply_msg.get())

		
if __name__ == "__main__":
	VDeviceManager()
