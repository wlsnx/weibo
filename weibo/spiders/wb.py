# -*- coding: utf-8 -*-
import scrapy
import urllib
import base64
import re
import json
import rsa
import binascii


LOGIN_DATA = {
    "entry": "weibo",
    "gateway": "1",
    "from": "",
    "savestate": "7",
    "userticket": "1",
    "pagerefer": "",
    "vsnf": "1",
    "su": "",
    "service": "miniblog",
    "servertime": "",
    "nonce": "",
    "pwencode": "rsa2",
    "rsakv": "",
    "sp": "",
    "encoding": "UTF-8",
    "prelt": "45",
    "url": "http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack",
    "returntype": "META",
}

LOGIN_URL = "http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.11)"


class WbSpider(scrapy.Spider):

    allowed_domains = ["weibo.com",
                       "sina.com",
                       "sina.cn",
                       "sina.com.cn"]

    def start_requests(self):
        self.username = self.settings.get("USERNAME")
        self.password = self.settings.get("PASSWORD")
        return self.login()

    def login(self):
        prelogin_url = "http://login.sina.com.cn/sso/prelogin.php?entry=weibo" \
                        "&callback=sinaSSOController.preloginCallBack&su={}" \
                        "&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.11)" \
                        .format(self.get_user(self.username))
        yield scrapy.Request(prelogin_url,
                             callback=self.parse_prelogin)

    @staticmethod
    def get_user(username):
        _username = urllib.quote(username)
        _username = base64.encodestring(_username)[:-1]
        return _username

    def parse_prelogin(self, response):
        login_data = LOGIN_DATA.copy()
        p = re.compile("\((.*)\)")
        matched = p.search(response.body)
        assert matched
        data = json.loads(matched.group(1))
        servertime = str(data["servertime"])
        nonce = data["nonce"]
        rsakv = data["rsakv"]

        login_data["servertime"] = servertime
        login_data["nonce"] = nonce
        login_data["su"] = self.get_user(self.username)
        login_data["sp"] = self.get_pwd_rsa(self.password, servertime, nonce)
        login_data["rsakv"] = rsakv
        yield scrapy.FormRequest(LOGIN_URL,
                                 formdata=login_data,
                                 callback=self.parse_login)

    def parse_login(self, response):
        p = re.compile("location.replace\(['|\"](.*?)['|\"]\)")
        matched = p.search(response.body)
        assert matched
        login_url = matched.group(1)
        yield scrapy.Request(login_url,
                             callback=self.parse_redirect)

    def parse_redirect(self, response):
        p = re.compile("feedBackUrlCallBack\((.*)\)", re.M)
        matched = p.search(response.body)
        assert matched
        feedback_json = json.loads(matched.group(1))
        assert feedback_json["result"]
        return self.origin_start_requests()

    def origin_start_requests(self):
        from itertools import chain
        return chain(super(WbSpider, self).start_requests(),
                     self.get_start_requests())

    def get_start_requests(self):
        yield

    @staticmethod
    def get_pwd_rsa(pwd, servertime, nonce):
        weibo_rsa_n = 'EB2A38568661887FA180BDDB5CABD5F21C7BFD59C090CB2D245A87AC253062882729293E5506350508E7F9AA3BB77F4333231490F915F6D63C55FE2F08A49B353F444AD3993CACC02DB784ABBB8E42A9B1BBFFFB38BE18D78E87A0E41B9B8F73A928EE0CCEE1F6739884B9777E4FE9E88A1BBE495927AC4A799B3181D6442443'
        weibo_rsa_e = 65537
        message = str(servertime) + '\t' + str(nonce) + '\n' + str(pwd)
        key = rsa.PublicKey(int(weibo_rsa_n, 16), weibo_rsa_e)
        encropy_pwd = rsa.encrypt(message, key)
        return binascii.b2a_hex(encropy_pwd)


    def parse(self, response):
        pass

