from collections import Counter, OrderedDict
import json
import os
import scrapy
import urllib

class FileUrl(scrapy.Item):
    url = scrapy.Field()
    print('url : ', url)

class HtmlDirectoryCrawler(scrapy.Spider):
    name = os.path.basename(__file__)
    def __init__(self, url=''):
        self.start_urls = [url]
        self.ext_counter = Counter()
    def parse(self, response):
        #print('response : ', response)
        for href in response.xpath('//a/@href')[5:]:
        # Skipping the 5 first hrefs: Name, Last modified, Size, Description, Parent Folder
            child_url = urllib.parse.urljoin(response.url, href.extract())
            #print(child_url)
            is_folder = (child_url[-1] == '/')
            if is_folder:
                yield scrapy.Request(child_url, self.parse)
            else:
                ext = child_url.split('.')[-1]
                self.ext_counter[ext] += 1
                yield FileUrl(url=child_url)
    def closed(self, reason):
        print('cntr : ', self.ext_counter)
        ordered_ext_counter = OrderedDict(sorted(
                self.ext_counter.items(),
                key=lambda x: (x[1],x[0])))
        self.log("Stats on extensions found:\n{}".format(
                json.dumps(ordered_ext_counter, indent=4)))