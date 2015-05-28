# -*- coding: utf-8 -*-
import scrapy
import urllib
import base64
import re
import json
import rsa
import binascii
#from os.path import isfile
import cookielib
try:
    from scrapy.downloadermiddlewares.cookies import CookiesMiddleware
except ImportError:
    from scrapy.contrib.downloadermiddleware.cookies import CookiesMiddleware


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
        self.COOKIE_FILE = self.settings.get(
            "COOKIE_FILE", "/tmp/weibo_cookie")
        try:
            lwpcookiejar = cookielib.LWPCookieJar(self.COOKIE_FILE)
            lwpcookiejar.load(ignore_discard=True, ignore_expires=True)
            for middleware in self.crawler.engine.downloader.middleware.middlewares:
                if isinstance(middleware, CookiesMiddleware):
                    cookies_middleware = middleware
                    break
            else:
                raise KeyError()
            cookiejar = cookies_middleware.jars[None].jar
            for cookie in lwpcookiejar:
                cookiejar.set_cookie(cookie)
            for request in self.get_start_requests():
                yield request

        except:
            self.username = self.settings.get("USERNAME")
            self.password = self.settings.get("PASSWORD")
            for request in self.login():
                yield request

    def login(self, pin=False):
        prelogin_url = "http://login.sina.com.cn/sso/prelogin.php?entry=weibo" \
            "&callback=sinaSSOController.preloginCallBack&su={}" \
            "&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.11)" \
            .format(self.get_user(self.username))
        yield scrapy.Request(prelogin_url,
                             meta={"pin": pin},
                             dont_filter=True,
                             callback=self.parse_prelogin)

    @staticmethod
    def get_user(username):
        _username = urllib.quote(username)
        _username = base64.encodestring(_username)[:-1]
        return _username

    def parse_prelogin(self, response):
        meta = response.meta
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
        if meta.get("pin", False):
            pcid = data["pcid"]
            login_data["pcid"] = pcid
            import random
            pin = "http://login.sina.com.cn/cgi/pin.php?r={}&s=0&p={}".format(
                random.randint(10000000, 99999999), pcid)
            yield scrapy.Request(pin,
                                 meta={"login_data": login_data},
                                 dont_filter=True,
                                 callback=self.parse_pin)
        else:
            yield scrapy.FormRequest(LOGIN_URL,
                                     formdata=login_data,
                                     dont_filter=True,
                                     callback=self.parse_login)

    def parse_pin(self, response):
        login_data = response.meta["login_data"]
        WEIBO_PIN_PATH = self.settings.get(
            "WEIBO_PIN_PATH", "/tmp/weibo_pin.png")
        with open(WEIBO_PIN_PATH, "wb") as weibo_pin:
            weibo_pin.write(response.body)
        # sync
        from select import select
        import sys
        print(u"请输入验证码:")
        rlist, _, _ = select([sys.stdin], [], [], 60)
        if rlist:
            door = sys.stdin.readline().replace("\n", "").replace("\r", "")
        else:
            sys.exit(1)
        login_data["door"] = door
        yield scrapy.FormRequest(LOGIN_URL,
                                 formdata=login_data,
                                 dont_filter=True,
                                 callback=self.parse_login)

    def parse_login(self, response):
        p = re.compile("location.replace\(['|\"](.*?)['|\"]\)")
        matched = p.search(response.body)
        if matched:
            login_url = matched.group(1)
            if "retcode=0" in login_url:
                return scrapy.Request(login_url,
                                      callback=self.parse_redirect)
            else:
                return self.login(pin=True)
        else:
            return self.login(pin=True)

    def parse_redirect(self, response):
        p = re.compile("feedBackUrlCallBack\((.*)\)", re.M)
        matched = p.search(response.body)
        feedback_json = json.loads(matched.group(1))
        assert feedback_json["result"]
        self.save_cookie(response)
        return self.origin_start_requests()

    def save_cookie(self, response=None):
        lwpcookiejar = cookielib.LWPCookieJar(self.COOKIE_FILE)
        for middleware in self.crawler.engine.downloader.middleware.middlewares:
            if isinstance(middleware, CookiesMiddleware):
                cookies_middleware = middleware
                break
        else:
            return
        for cookie in cookies_middleware.jars[None].jar:
            lwpcookiejar.set_cookie(cookie)
        lwpcookiejar.save(ignore_discard=True, ignore_expires=True)

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
