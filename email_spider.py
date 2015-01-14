#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
:Name:
email_spider.py

:Authors:
Soufian Salim (soufi@nsal.im)

:Date:
November 16th, 2014

:Description:
lists.ubuntu.com/archives spider
"""

import io
import json
import urllib2

from bs4 import BeautifulSoup
from bs4 import NavigableString
from dateutil.parser import parse
from scrapy import Spider

archive = "ubuntu-fr"

months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
year = "2014"


class EmailSpider(Spider):
	"""
	This spider crawls lists.ubuntu.com/archives/ for conversation threads
	"""
	name = "email"

	allowed_domains = ["lists.ubuntu.com"]

	start_urls = ["https://lists.ubuntu.com/archives/{0}/{1}-{2}/thread.html".format(archive, year, month) for month in months]


	def parse(self, response):
		"""
		Parses the archive page for threads
		"""
		html = "<ul>" + response.xpath("//ul").extract()[1] + "</ul>"

		soup = BeautifulSoup(html)

		messages_tree = []
		messages_flat = []

		for ul in soup.ul.children:
			if isinstance(ul, NavigableString):
				continue
			ul_tree, ul_flat = self.parse_tree(response, ul)

			messages_tree.extend(ul_tree)
			messages_flat.extend(ul_flat)

		filename = response.request.url[8:-5].replace("/", "_")

		self.save_json(messages_tree, "data/{0}.json".format(filename))

		for message in messages_flat:
			if "answers" in message:
				del message["answers"]

		self.save_json(messages_flat, "data/{0}.json".format(filename))


	def parse_tree(self, response, soup):
		"""
		Parses an email tree
		"""
		messages_tree = []
		messages_flat = []

		for li in soup.children:
			if isinstance(li, NavigableString):
				continue

			email = self.parse_email(response.request.url.replace("thread.html", li.a.get('href')))
			
			if li.ul:
				email["answers"] = []
				
				for ul in li.children:
					if isinstance(ul, NavigableString) or not ul.li:
						continue

					ul_tree, ul_flat = self.parse_tree(response, ul)

					email["answers"].extend(ul_tree)
					messages_flat.extend(ul_flat)

			messages_tree.append(email)
			messages_flat.append(email)

		return messages_tree, messages_flat


	def parse_email(self, url):
		"""
		Parses a single email
		"""
		html = urllib2.urlopen(url).read()
		soup = BeautifulSoup(html)

		datetime = soup.i.get_text().replace("  ", " ")[4:-9] + " " + year

		for fr, en in [(u"Fév", u"Feb"), (u"Avr", u"Apr"), (u"Mai", u"May"), (u"Juin", u"Jun"), (u"Juil", u"Jul"), (u"Aou", u"Aug"), (u"Déc", u"Dec")]:
			datetime = datetime.replace(fr, en)

		datetime = str(parse(datetime))

		return {
			"identifier": url[-11:-5],
			"subject": soup.h1.get_text(),
			"author_name": soup.b.get_text(),
			"author_address": soup.a.get_text().replace(" at ", "@").strip(),
			"datetime": datetime,
			"content": soup.pre.get_text(),
		}


	def save_json(self, data, path):
		with io.open(path, "w", encoding="utf-8") as f:
			f.write(unicode(json.dumps(data, ensure_ascii=False)))