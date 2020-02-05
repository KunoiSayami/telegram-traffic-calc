# -*- coding: utf-8 -*-
# trafficcalc.py
# Copyright (C) 2020 KunoiSayami
#
# This module is part of telegram-traffic-calc and is released under
# the AGPL v3 License: https://www.gnu.org/licenses/agpl-3.0.txt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import datetime
import string
from configparser import ConfigParser

from pyrogram import Client

from libpy3.mysqldb import mysqldb


class TrafficRecord:
	def __init__(self, q: dict):
		self._id = q['id']
		self._user_id = q['user_id']
		self._u = q['u']
		self._d = q['d']
		self._node_id = q['node_id']
		self._rate = q['rate']
		self._traffic = self.convert_traffic_to_byte(q['traffic'])
		self._log_time = q['log_time']

	@staticmethod
	def get_basic_num(traffic: str) -> int:
		if traffic[-2] == 'K':
			return 1024
		elif traffic[-2] == 'M':
			return 1024 * 1024
		elif traffic[-2] == 'G':
			return 1024 ** 3
		elif traffic[-2] == 'T':
			return 1024 ** 4
		else:
			return 1

	@staticmethod
	def convert_traffic_to_byte(traffic: str) -> float:
		basic_num = TrafficRecord.get_basic_num(traffic)
		if traffic[-2] in string.ascii_uppercase:
			return float(traffic[:-2]) * basic_num
		else:
			return float(traffic[:-1])

	@property
	def rid(self) -> int:
		return self._id

	@property
	def user_id(self) -> int:
		return self._user_id

	@property
	def u(self) -> int:
		return self._u

	@property
	def d(self) -> int:
		return self._d

	@property
	def node_id(self) -> int:
		return self._node_id

	@property
	def rate(self) -> int:
		return self._rate

	@property
	def traffic(self) -> float:
		return self._traffic

	@property
	def log_time(self) -> int:
		return self._log_time

	@staticmethod
	def get_small_traffic(traffic: float) -> float:
		return traffic if traffic < 1024 else traffic / 1024

	@staticmethod
	def get_traffic_string(traffic: float) -> str:
		if traffic > 1024:
			for x in ['KB', 'MB', 'GB']:
				traffic = TrafficRecord.get_small_traffic(traffic)
				if traffic < 1024:
					break
		else:
			x = 'B'
		return '{:.2f}{}'.format(traffic, x)


class User:
	def __init__(self, s: dict):
		self._user_id = s['id']
		self._user_name = s['user_name']

	@property
	def user_id(self) -> int:
		return self._user_id

	@property
	def user_name(self) -> str:
		return self._user_name

class Bot:
	def __init__(self):
		config = ConfigParser()
		config.read('config.ini')

		self.conn = mysqldb('localhost', config.get('mysql', 'user'), config.get('mysql', 'passwd'), config.get('mysql', 'database'))

		bot_token = config.get('telegram', 'bot_token')
		self.bot = Client(
			bot_token.split(':')[0],
			config.get('telegram', 'api_id'),
			config.get('telegram', 'api_hash'),
			bot_token=bot_token
		)
		self.channel = config.getint('telegram', 'target_channel')

	def run(self):
		self.bot.start()
		today = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
		if datetime.datetime.now() - today < datetime.timedelta(hours=23, minutes=30):
			today = datetime.datetime.combine(datetime.datetime.today() - datetime.timedelta(hours=23, minutes=30), datetime.datetime.min.time())
		endday = today + datetime.timedelta(days=1)
		sqlObj = self.conn.query("SELECT * FROM `user_traffic_log` WHERE `log_time` > %s AND `log_time` <= %s ORDER BY `log_time` DESC", (today.timestamp(), endday.timestamp()))
		users = {}
		for x in map(TrafficRecord, sqlObj):
			if x.user_id in users:
				users[x.user_id] += x.traffic
			else:
				users.update({x.user_id: x.traffic})
		s = []
		for _ in range(3):
			maxnum = -0x7ffffff
			user = 0
			for k, v in users.items():
				if maxnum < v:
					user = k
					maxnum = v
			user = User(self.conn.query1("SELECT * FROM `user` WHERE `id` = %s", user))
			s.append('{}, <code>{}</code>, {}'.format(user.user_id, user.user_name, TrafficRecord.get_traffic_string(users.get(user.user_id))))
			users.pop(user.user_id)
		self.bot.send_message(self.channel, '\n'.join(s), 'html')
		self.bot.stop()

if __name__ == "__main__":
	bot = Bot()
	bot.run()
