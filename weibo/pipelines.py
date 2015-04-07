# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


from scrapy.contrib.pipeline.images import ImagesPipeline


class WeiboImagePipeline(ImagesPipeline):

    def process_item(self, item, spider):
        self.uid = item["uid"]
        return super(WeiboImagePipeline, self).process_item(item, spider)

    def file_path(self, request, response=None, info=None):
        path = super(WeiboImagePipeline, self).file_path(request, response, info)
        if request.url.endswith("gif"):
            path = path[:-3] + "gif"
        return path.replace("full/", "full/weibo_{}_".format(self.uid))

    def thumb_path(self, request, response=None, info=None):
        path = super(WeiboImagePipeline, self).thumb_path(request, response, info)
        if request.url.endswith("gif"):
            path = path[:-3] + "gif"
        return path.replace("thumb/", "thumb/weibo_{}_".format(self.uid))

