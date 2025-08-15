import scrapy

class GameItem(scrapy.Item):
    Name = scrapy.Field()
   
    Blockchain = scrapy.Field()
    Device = scrapy.Field()
    Status = scrapy.Field()
    NFT = scrapy.Field()
    F2P = scrapy.Field()
    P2E = scrapy.Field()
    P2E_Score = scrapy.Field()
