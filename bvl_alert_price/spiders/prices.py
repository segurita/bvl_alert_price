# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
import logging
from email.mime.text import MIMEText
import smtplib

import yaml
import scrapy
from scrapy.http import Request


class PricesSpider(scrapy.Spider):
    name = "prices"
    allowed_domains = ["bvl.com.pe"]
    today = datetime.today()
    a_month_ago = today - timedelta(days=30)

    with open("../config.yml", "r") as handle:
        data = yaml.load(handle.read())

    def start_requests(self):
        for element in self.data['prices']:
            nemonico = list(element.keys())[0]
            url = "http://www.bvl.com.pe/jsp/cotizacion.jsp?fec_inicio={0}&fec_fin={1}&nemonico={2}".format(
                self.a_month_ago.strftime("%Y%m%d"),
                self.today.strftime("%Y%m%d"),
                nemonico,
            )
            yield Request(
                url,
                meta={
                    "nemonico": nemonico,
                    "share_price": float(element[nemonico]),
                },
                callback=self.parse,
            )

    def parse(self, response):
        closing_price = 0
        with open("a.html", "w") as handle:
            handle.write(str(response.body))

        for tr in response.xpath("//tr"):
            cells = tr.xpath(".//td")
            if cells:
                price_date = cells[0].xpath("text()").extract_first().strip()
                closing_price = cells[2].xpath("text()").extract_first().strip()
                if closing_price:
                    logging.debug("### {} Date: {}, Closing price: {}".format(
                        response.meta['nemonico'],
                        price_date,
                        closing_price,
                    ))
                    break
        if closing_price and float(closing_price) <= response.meta['share_price']:
            self.send_email(response.meta)

    def send_email(self, meta):
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(self.data["email_account"], self.data["email_password"])
        text = "BVL alerta: {} a {}".format(meta['nemonico'], meta['share_price'])
        msg = MIMEText(text)
        msg['Subject'] = text
        msg['From'] = self.data["email_account"]
        msg['To'] = self.data["email_recipient"]
        server.send_message(msg)
        logging.debug("Sending {}".format(text))
        server.quit()
