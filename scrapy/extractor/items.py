# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from datetime import date
import scrapy


class ResourceItem(scrapy.Item):
    url = scrapy.Field()
    #title = scrapy.Field()
    start_date = scrapy.Field()
    end_date = scrapy.Field()
    last_updated = scrapy.Field()
