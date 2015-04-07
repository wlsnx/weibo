# -*- coding: utf-8 -*-
import scrapy
import redis


class WeiboEntrySpider(scrapy.Spider):
    name = "entry"
    allowed_domains = [""]
    #start_urls = (
        #'http://www./',
    #)
    custom_settings = {
        "CLOSE_ON_IDLE": True,
    }

    def __init__(self, uid=None, user=None):
        self.uid = uid.split(",") if uid else []
        self.user = user.split(",") if user else []

    def start_requests(self):
        self.db = redis.Redis()
        self.UID_KEY = self.settings.get("UID_KEY", "weibo_photo_uids")
        self.USER_KEY = self.settings.get("USER_KEY", "weibo_photo_users")
        if self.uid:
            self.db.sadd(self.UID_KEY, *self.uid)
        if self.user:
            self.db.lpush(self.USER_KEY, *self.user)
        return []

    def parse(self, response):
        pass
