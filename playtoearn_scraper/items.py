import scrapy

class GameItem(scrapy.Item):
    Name = scrapy.Field()
    Description = scrapy.Field()
    Category = scrapy.Field()
    Blockchain = scrapy.Field()
    Device = scrapy.Field()       # Main device (first one)
    amar_device = scrapy.Field()  # All devices like Linux, MAC, Web, Windows
    Status = scrapy.Field()
    NFT = scrapy.Field()
    F2P = scrapy.Field()
    P2E = scrapy.Field()
    P2E_Score = scrapy.Field()
