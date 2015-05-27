#!/usr/bin/env python
# encoding: utf-8


from wb import WbSpider
import scrapy
import redis
from twisted.internet import reactor
import json
from weibo.items import PhotoItem
from scrapy.exceptions import DontCloseSpider
#from scrapy.contrib.loader import ItemLoader
from weibo.items import PhotoItemLoader as ItemLoader


class WeiboPhotoSpider(WbSpider):

    name = "wp"
    db = redis.Redis()
    allowed_domains = ["sina.com",
                       "sina.cn",
                       "sina.com.cn",
                       "weibo.com",
                       "sinaimg.cn"]
    PHOTO_URL = "http://photo.weibo.com/photos/get_all"
    #PHOTO_URL = "http://photo.weibo.com/photos/get_{}"
    #PHOTO_TYPES = ("all")

    tasks = []

    #ALBUM_URL = "http://photo.weibo.com/albums/get_{}"
    """
    LATEST FORM PARAMS:
        uid: user id
        page: page number
        count: photo number of per page
    """
    IMAGE_URL = "http://ww1.sinaimg.cn/large/{}"
    USER_HOME = "http://weibo.com/{}"

    def __init__(self, uid=None, user=None, action="start", *args, **kwargs):
        super(WeiboPhotoSpider, self).__init__(*args, **kwargs)
        self.uid = set(uid.split(",")) if uid else []
        self.user = set(user.split(",")) if user else []
        self.action = action

    def load_config(self):
        #from weibo import settings
        #reload(settings)
        #self.settings.setmodule(settings)
        self.crawler.signals.connect(
            self.spider_idle, scrapy.signals.spider_idle)
        self.SCRAPE_INTERVAL = self.settings.getint("SCRAPE_INTERVAL", 60)
        self.CLOSE_ON_IDLE = self.settings.getbool("CLOSE_ON_IDLE", True)
        self.UID_KEY = self.settings.get("UID_KEY", "weibo_photo_uids")
        self.USER_KEY = self.settings.get("USER_KEY", "weibo_photo_users")
        #self.COUNT = self.settings.getint("COUNT", 30)
        self.FIRST_CRAWL_COUNT = self.settings.getint("FIRST_CRAWL_COUNT", 20)
        self.AUTO_UPDATE = self.settings.getbool("AUTO_UPDATE", False)
        self.QRSYNC = self.settings.get("QRSYNC", "qrsync")
        # scrapy.log.start_from_crawler(self.crawler)

    def list_photo(self, uid, page, crawl_count=0, meta=None):
        formdata = dict(uid=uid,
                        page=str(page),
                        type="3",
                        count=str(crawl_count) if crawl_count else str(self.FIRST_CRAWL_COUNT))
        meta = meta or {}
        meta.update(formdata)
        a = scrapy.FormRequest(self.PHOTO_URL,
                               callback=self.parse_photo_list,
                               method="GET",
                               meta=meta,
                               dont_filter=True,
                               formdata=formdata)
        return a

    def update(self, conf_path=""):
        import os
        qn_conf = os.path.join(conf_path, "qn_conf.json")
        if os.path.isfile(qn_conf):
            os.system("{} '{}'".format(self.QRSYNC, qn_conf))
        self.do_rest_tasks()

    def get_start_requests(self):
        self.load_config()
        reactor.callLater(self.SCRAPE_INTERVAL, self.restart)
        #self.first_crawl = {}
        self.first_idle = True

        for request in self.trans_user():
            yield request

        for uid in self.get_uids():
            if not uid:
                continue
            yield self.list_photo(uid, 1)

    def restart(self):
        for request in self.start_requests():
            self.crawler.engine.schedule(request=request,
                                         spider=self)

    def get_uids(self):
        if self.uid:
            if self.action == "start":
                self.db.sadd(self.UID_KEY, *self.uid)
            elif self.action == "stop":
                self.db.srem(self.UID_KEY, *self.uid)
        return self.db.sscan(self.UID_KEY)[1]

    def trans_user(self):
        for user in self.user:
            yield scrapy.Request(self.USER_HOME.format(user),
                                 callback=self.parse_user_home)

    def parse_user_home(self, response):
        import re
        uid_pattern = re.compile(r"CONFIG\['oid'\]='(\d+)';")
        matched = uid_pattern.search(response.body)
        if matched:
            uid = matched.group(1)
            if self.action == "start":
                new_uid = self.db.sadd(self.UID_KEY, uid)
                if new_uid:
                    yield self.list_photo(uid, 1)
            elif self.action == "stop":
                self.db.srem(self.UID_KEY, uid)

    def parse_photo_list(self, response):
        try:
            data_json = json.loads(response.body)
        except ValueError:
            import os
            os.remove(self.COOKIE_FILE)
            self.close()
        meta = response.meta
        uid = meta["uid"]
        #page = int(meta["page"])
        data = data_json["data"]
        total = data.get("total", 0)
        photo_list = data.get("photo_list", [])
        #photo_item = PhotoItem()
        #image_ids = [photo["pic_name"] for photo in photo_list]
        latest_index_key = "weibo_index:{}".format(uid)
        latest_index = self.db.get(latest_index_key)
        #self.db.set(latest_index_key, total - self.COUNT * (page - 1))

        new_photo_count = max(total - int(latest_index), 0) if latest_index else self.FIRST_CRAWL_COUNT
        new_photo_count = min(new_photo_count, total)
        if not new_photo_count:
            yield
        elif new_photo_count > len(photo_list):
            yield self.list_photo(uid, 1, new_photo_count)

        #if latest_index and page == 1:
            #crawl_count = max(total - int(latest_index), 0)
        #else:
            #crawl_count = meta.get("crawl_count", 0) or self.FIRST_CRAWL_COUNT
        #if page == 1:
            #self.db.set(latest_index_key, total)

        #crawl_count = max(total - int(latest_index), 0) % self.COUNT if latest_index else self.COUNT

        #image_ids = image_ids[:min(crawl_count, self.COUNT)]
        #photo_list = photo_list[crawl_count:0:-1]
        else:
            self.db.set(latest_index_key, total)
            #photo_list.reverse()
            photo_list = photo_list[new_photo_count-1::-1]
        #crawl_count = max(crawl_count - self.COUNT, 0)

        #crawl_done = True if crawl_count == 0 else False
        #image_urls = [
            #self.IMAGE_URL.format(image_id) for image_id in image_ids]
        #photo_item["image_urls"] = image_urls
        #photo_item["uid"] = uid
        #yield photo_item
            for photo in photo_list:
                photo_item = ItemLoader(PhotoItem())
                photo_item.add_value("image_urls", [[self.IMAGE_URL.format(photo["pic_name"]),],])
                photo_item.add_value("caption", photo["caption_render"])
                photo_item.add_value("created_time", photo["timestamp"])
                photo_item.add_value("timestamp", photo["timestamp"])
                photo_item.add_value("code", photo["pic_pid"])
                #photo_item.add_value("ins_id", photo["uid"])
                photo_item.add_value("uid", photo["uid"])
                yield photo_item.load_item()

        #if total > page * self.COUNT and crawl_count:
            #yield self.list_photo(uid, page + 1, crawl_count=crawl_count)

    def spider_idle(self, spider):
        if self.first_idle and self.AUTO_UPDATE:
            self.update(self.settings.get("IMAGES_STORE", ""))
            self.first_idle = False
        if spider is self and not self.CLOSE_ON_IDLE:
            raise DontCloseSpider()

    def do_rest_tasks(self):
        import requests
        import copy
        ytapi_url = self.settings.get("YTAPI_URL")
        self.tasks.sort(key=lambda x: x[1])
        tasks = copy.copy(self.tasks)
        self.tasks = []
        for task in tasks:
            print(task[1])
            response = requests.post(ytapi_url, data=task[0])
            if "post_result" not in response.content:
                self.tasks.append(task)

    def close(self, reason="cancelled"):
        return self.crawler.engine.close_spider(self, reason)

