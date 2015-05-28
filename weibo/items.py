# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
try:
    from scrapy.loader.processors import MapCompose, TakeFirst
    from scrapy.loader import ItemLoader
except ImportError:
    from scrapy.contrib.loader.processor import MapCompose, TakeFirst
    from scrapy.contrib.loader import ItemLoader


class DefaultItem(scrapy.Item):

    def __init__(self, *args, **kwargs):
        super(DefaultItem, self).__init__(*args, **kwargs)
        for key in self.fields:
            if key not in self and "default" in key:
                self[key] = key["default"]


class PhotoItemLoader(ItemLoader):

    default_output_processor = TakeFirst()


def strftime(timestamp):
    from datetime import datetime
    time = datetime.fromtimestamp(int(timestamp))
    return time.strftime("%Y-%m-%d %H:%M:%S")


class PhotoItem(scrapy.Item):

    caption      = scrapy.Field()
    created_time = scrapy.Field(input_processor = MapCompose(strftime))
    img_std_url  = scrapy.Field()
    code         = scrapy.Field()
    image_urls   = scrapy.Field()
    timestamp    = scrapy.Field()
    images       = scrapy.Field()
    uid          = scrapy.Field()

