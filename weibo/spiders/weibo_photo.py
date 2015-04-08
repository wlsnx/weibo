#!/usr/bin/env python
# encoding: utf-8


from wb import WbSpider
import scrapy
import redis
from twisted.internet import reactor
import json
from weibo.items import PhotoItem
from scrapy.exceptions import DontCloseSpider


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

    #ALBUM_URL = "http://photo.weibo.com/albums/get_{}"
    """
    LATEST FORM PARAMS:
        uid: user id
        page: page number
        count: photo number of per page
    """
    IMAGE_URL = "http://ww1.sinaimg.cn/large/{}"
    USER_HOME = "http://weibo.com/{}"

    def __init__(self, uid=None, user=None, *args, **kwargs):
        super(WeiboPhotoSpider, self).__init__(*args, **kwargs)
        self.uid = set(uid.split(",")) if uid else []
        self.user = set(user.split(",")) if user else []
        #if uid or user:
            #self.CLOSE_ON_IDLE = False
        #else:
            #self.CLOSE_ON_IDLE = True

    def load_config(self):
        from weibo import settings
        reload(settings)
        self.settings.setmodule(settings)
        self.crawler.signals.connect(self.spider_idle, scrapy.signals.spider_idle)
        self.SCRAPE_INTERVAL = self.settings.getint("SCRAPE_INTERVAL", 60)
        self.CLOSE_ON_IDLE = self.settings.getbool("CLOSE_ON_IDLE", True)
        self.UID_KEY = self.settings.get("UID_KEY", "weibo_photo_uids")
        self.USER_KEY = self.settings.get("USER_KEY", "weibo_photo_users")
        self.COUNT = self.settings.getint("COUNT", 30)
        self.FORCE_DOWNLOAD = self.settings.getbool("FORCE_DOWNLOAD", False)
        self.FIRST_CRAWL_COUNT = self.settings.getint("FIRST_CRAWL_COUNT", 20)

    def list_photo(self, uid, page, meta=None):
        formdata = dict(uid=uid,
                        page=str(page),
                        type="3",
                        count=str(self.COUNT))
        meta = meta or {}
        meta.update(formdata)
        a =  scrapy.FormRequest(self.PHOTO_URL,
                                  callback=self.parse_photo_list,
                                  method="GET",
                                  meta=meta,
                                  dont_filter=True,
                                  formdata=formdata)
        return a

    def get_start_requests(self):
        self.load_config()
        reactor.callLater(self.SCRAPE_INTERVAL, self.restart)
        self.first_crawl = {}
        for uid in self.get_uids():
            if not uid:
                continue
            yield self.list_photo(uid, 1)

        for request in self.trans_user():
            yield request

    def restart(self):
        for request in self.get_start_requests():
            self.crawler.engine.schedule(request=request,
                                         spider=self)

    def get_uids(self):
        if self.uid:
            self.db.sadd(self.UID_KEY, *self.uid)
            return self.uid
        return self.db.sscan(self.UID_KEY)[1]

    def trans_user(self):
        #if self.user:
        for user in self.user:
            yield scrapy.Request(self.USER_HOME.format(user),
                                    callback=self.parse_user_home)
        #else:
            #while True:
                #user = self.db.rpop(self.USER_KEY)
                #if user:
                    #yield scrapy.Request(self.USER_HOME.format(user),
                                        #callback=self.parse_user_home)
                #else:
                    #break

    def parse_user_home(self, response):
        import re
        uid_pattern = re.compile(r"CONFIG\['oid'\]='(\d+)';")
        matched = uid_pattern.search(response.body)
        if matched:
            uid = matched.group(1)
            new_uid = self.db.sadd(self.UID_KEY, uid)
            if new_uid:
                yield self.list_photo(uid, 1)

    def parse_photo_list(self, response):
        data_json = json.loads(response.body)
        meta = response.meta
        uid = meta["uid"]
        page = int(meta["page"])
        #type = meta["type"]
        data = data_json["data"]
        total = data.get("total", 0)
        photo_list = data.get("photo_list", [])
        photo_item = PhotoItem()
        image_ids = [photo["pic_name"] for photo in photo_list]
        latest_image_key = "weibo_image:{}".format(uid)
        #crawled_page_key = "weibo_page:{type}:{uid}".format(type=type, uid=uid)
        latest_image = self.db.get(latest_image_key)
        if latest_image in image_ids:
            index = image_ids.index(latest_image)
            crawl_count = 0
        else:
            crawl_count = meta.get("crawl_count", 0) or self.FIRST_CRAWL_COUNT
            if 0 < crawl_count <= self.COUNT:
                index = crawl_count
                crawl_count = 0
            elif crawl_count > self.COUNT:
                index = self.COUNT
                crawl_count -= self.COUNT
        image_ids = image_ids[:index]
        #crawled_page = int(self.db.get(crawled_page_key) or 1)
        #page = page + crawled_page - 1
        crawl_done = True if crawl_count == 0 else False
        if page == 1 and image_ids:
            self.db.set(latest_image_key, image_ids[0])
        #image_urls = [self.IMAGE_URL.format(photo["pic_name"]) for photo in photo_list]
        image_urls = [self.IMAGE_URL.format(image_id) for image_id in image_ids]
        photo_item["image_urls"] = image_urls
        photo_item["uid"] = uid
        yield photo_item
        #self.db.set(crawled_page_key, page)
        if total > page*self.COUNT and not crawl_done:
            yield self.list_photo(uid, page+1, meta={"crawl_count": crawl_count})

    def spider_idle(self, spider):
        if spider is self and not self.CLOSE_ON_IDLE:
            raise DontCloseSpider()

