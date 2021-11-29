from collections import Counter, OrderedDict
import json
import os
import scrapy
import urllib
from extractor.items import ResourceItem

VALID_FORMAT = '.gz'

class FileUrl(scrapy.Item):
    url = scrapy.Field()
    print('url : ', url)

def convert_date_isoformat(date_string):
    """
    Convert a date string to ISO format.
    """
    #TODO: Convert to isoformat
    return date_string

class ChirpsSpider(scrapy.Spider):
    name = "chirps"
    def __init__(self):
        self.start_urls = [
            #'https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_6-hourly/p1_bin/'
            'https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_6-hourly/p1_bin/200905/'
            ]
        
    def parse(self, response):
        for href in response.xpath('//a/@href')[5:]:
            # Skipping the 5 first hrefs: Name, Last modified, Size, Description, Parent Folder
            child_url = urllib.parse.urljoin(response.url, href.extract())
            is_folder = (child_url[-1] == '/')
            if is_folder:
                yield scrapy.Request(child_url, self.parse)
            else:
                ext = child_url.split('.')[-1]
                if ext in VALID_FORMAT:
                    #TODO: Calculate the end_date
                    start_date = child_url.split('.')[-2]
                    iso_date = convert_date_isoformat(start_date)
                    yield ResourceItem(url=child_url, start_date=start_date)