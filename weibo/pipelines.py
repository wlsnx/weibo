# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


from scrapy.contrib.pipeline.images import ImagesPipeline, ImageException
from io import BytesIO
from PIL import Image


class WeiboImagePipeline(ImagesPipeline):

    @classmethod
    def from_settings(cls, settings):
        #cls.MAX_WIDTH = settings.getint("IMAGES_MAX_WIDTH", 10000)
        #cls.MAX_HEIGHT = settings.getint("IMAGES_MAX_HEIGHT", 10000)
        cls.MAX_WIDTH_HEIGHT_SCALE = settings.getfloat(
            "IMAGES_MAX_WIDTH_HEIGHT_SCALE", 0)
        cls.MAX_HEIGHT_WIDTH_SCALE = settings.getfloat(
            "IMAGES_MAX_HEIGHT_WIDTH_SCALE", 0)
        return super(WeiboImagePipeline, cls).from_settings(settings)

    def process_item(self, item, spider):
        self.uid = item["uid"]
        return super(WeiboImagePipeline, self).process_item(item, spider)

    def file_path(self, request, response=None, info=None):
        path = super(WeiboImagePipeline, self).file_path(
            request, response, info)
        return path.replace("full/", "full/weibo_{}_".format(self.uid))

    def thumb_path(self, request, response=None, info=None):
        path = super(WeiboImagePipeline, self).thumb_path(
            request, response, info)
        return path.replace("thumb/", "thumb/weibo_{}_".format(self.uid))

    def get_images(self, response, request, info):
        orig_image = Image.open(BytesIO(response.body))
        width, height = orig_image.size
        #if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
            #raise ImageException("Image too big (%dx%d > %dx%d)" %
                                 #(width, height, self.MAX_WIDTH, self.MAX_HEIGHT))
        #if height > width:
            #width, height = height, width
        #scale = width*1.0 / height
        width_height_scale = width * 1.0 / height
        height_width_scale = height * 1.0 / width
        if self.MAX_WIDTH_HEIGHT_SCALE and width_height_scale > self.MAX_WIDTH_HEIGHT_SCALE:
            raise ImageException("Image too wide (%d/%d > %.2f)" %
                                 (width, height, self.MAX_WIDTH_HEIGHT_SCALE))
        elif self.MAX_HEIGHT_WIDTH_SCALE and height_width_scale > self.MAX_HEIGHT_WIDTH_SCALE:
            raise ImageException("Image too high (%d/%d > %.2f)" %
                                 (height, width, self.MAX_HEIGHT_WIDTH_SCALE))
        else:
            return super(WeiboImagePipeline, self).get_images(response, request, info)

