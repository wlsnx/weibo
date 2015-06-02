# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


try:
    from scrapy.pipelines.images import ImagesPipeline, ImageException
except ImportError:
    from scrapy.contrib.pipeline.images import ImagesPipeline, ImageException
from io import BytesIO
from PIL import Image
from scrapy import Request


class WeiboImagePipeline(ImagesPipeline):

    @classmethod
    def from_settings(cls, settings):
        #cls.MAX_WIDTH = settings.getint("IMAGES_MAX_WIDTH", 10000)
        #cls.MAX_HEIGHT = settings.getint("IMAGES_MAX_HEIGHT", 10000)
        cls.MAX_WIDTH_HEIGHT_SCALE = settings.getfloat(
            "IMAGES_MAX_WIDTH_HEIGHT_SCALE", 0)
        cls.MAX_HEIGHT_WIDTH_SCALE = settings.getfloat(
            "IMAGES_MAX_HEIGHT_WIDTH_SCALE", 0)
        #cls.MAX_WIDTH = settings.getint("IMAGES_MAX_WIDTH", 0)
        #cls.MAX_HEIGHT = settings.getint("IMAGES_MAX_HEIGHT", 0)
        cls.IMAGES_MAX_WIDTH = settings.getint("IMAGES_MAX_WIDTH", 0)
        cls.IMAGES_MAX_HEIGHT = settings.getint("IMAGES_MAX_HEIGHT", 0)
        cls.IMAGES_RESIZE = settings.getlist("IMAGES_RESIZE")
        return super(WeiboImagePipeline, cls).from_settings(settings)

    def resize(self, width, height):
        if not self.IMAGES_RESIZE:
            return False
        elif self.IMAGES_MAX_WIDTH is not 0 and width > self.IMAGES_MAX_WIDTH \
            or self.IMAGES_MAX_HEIGHT is not 0 and height > self.IMAGES_MAX_HEIGHT:
            return True

    #def process_item(self, item, spider):
        #self.uid = item["uid"]
        #return super(WeiboImagePipeline, self).process_item(item, spider)

    def file_path(self, request, response=None, info=None):
        path = super(WeiboImagePipeline, self).file_path(
            request, response, info)
        url = request.url
        path = path[:path.rfind(".")] + url[url.rfind("."):]
        uid = request.meta["uid"]
        return path.replace("full/", "full/weibo_{}_".format(uid))

    def thumb_path(self, request, response=None, info=None):
        path = super(WeiboImagePipeline, self).thumb_path(
            request, response, info)
        url = request.url
        path = path[:path.rfind(".")] + url[url.rfind("."):]
        uid = request.meta["uid"]
        return path.replace("thumb/", "thumb/weibo_{}_".format(uid))

    def image_downloaded(self, response, request, info):
        check_sum = None
        for path, image, buf in self.get_images(response, request, info):
            if check_sum is None:
                buf.seek(0)
                from scrapy.utils.misc import md5sum
                check_sum = md5sum(buf)
            width, height = image.size
            if response.url.endswith(".gif"):
                buf = BytesIO(response.body)
            self.store.persist_file(
                path, buf, info,
                meta={"width": width,
                      "height": height},
            )
        return check_sum

    def get_media_requests(self, item, info):
        return [Request(x, meta={"uid": item["uid"]}) for x in item.get(self.IMAGES_URLS_FIELD, [])]

    def get_images(self, response, request, info):
        path = self.file_path(request, response=response, info=info)
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
        elif self.resize(width, height):
            image, buf = self.convert_image(orig_image, self.IMAGES_RESIZE)
            yield path, image, buf
        else:
            for info in super(WeiboImagePipeline, self).get_images(response, request, info):
                yield info

