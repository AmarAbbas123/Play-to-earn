import scrapy
from urllib.parse import urljoin
from playtoearn_scraper.items import GameItem

class BlockchainGamesSpider(scrapy.Spider):
    name = "blockchain_games"
    allowed_domains = ["playtoearn.com"]

    custom_settings = {
        "FEED_FORMAT": "csv",
        "FEED_URI": "blockchain_games.csv",
        "FEED_EXPORT_FIELDS": [
            "Name", "Description", "Category", "Blockchain", "Device",
            "amar_device", "Status", "NFT", "F2P", "P2E", "P2E_Score"
        ],
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.25,
        "AUTOTHROTTLE_ENABLED": True,
        "CONCURRENT_REQUESTS": 8,
        "RETRY_TIMES": 2,
    }

    def start_requests(self):
        for i in range(1, 61):
            url = f"https://playtoearn.com/blockchaingames?p={i}"
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        ("wait_for_selector", "tbody.__TableItemsSwiper tr")
                    ],
                    "playwright_context": "default",
                },
                callback=self.parse
            )


    def parse(self, response):
        rows = response.css("tbody.__TableItemsSwiper tr")
        self.logger.info(f"Page URL: {response.url}, rows found: {len(rows)}")

        for row in rows:
            item = GameItem()

            # Name & Description
            item["Name"] = row.css("div.__TextViewGameContainer a.dapp_detaillink b::text").get(default="").strip()
            item["Description"] = row.css("div.__TextViewGameContainer > span::text").get(default="").strip()

            # Category
            categories = row.css("div.__TableCategoryTags div.__TagItem::text").getall()
            item["Category"] = ", ".join([c.strip() for c in categories if c.strip()])

            # Blockchain
            blockchains = row.css("div.TableGameBlockchainItems a[aria-label]::attr(title)").getall()
            item["Blockchain"] = ", ".join([b.strip() for b in blockchains if b.strip()])

            # Device
            first_device = row.css("div.TableGameBlockchainItems a[aria-label]::attr(title)").get(default="").strip()
            item["Device"] = first_device

            # amar_device (all devices)
            all_devices = row.css("div.TableGameBlockchainItems a[aria-label]::attr(title)").getall()
            item["amar_device"] = ", ".join([d.strip() for d in all_devices if d.strip()])

            # Status
            item["Status"] = row.css("a.__ButtonStatusLive::text, a.__ButtonStatusDead::text").get(default="").strip()

            # NFT
            nft = row.css("a[aria-label*='NFT']::attr(aria-label)").get()
            item["NFT"] = (nft or "").replace(" NFT Support", "").strip()

            # F2P
            f2p = row.css("a[aria-label*='Free-To-Play']::attr(aria-label)").get()
            item["F2P"] = (f2p or "").strip()

            # P2E (multiple)
            p2e = row.css("a[aria-label*='Play-To-Earn']::attr(aria-label)").getall()
            item["P2E"] = ", ".join([p.strip() for p in p2e if p.strip()])

            # P2E Score
            item["P2E_Score"] = row.css("span.dailychangepercentage::text").get(default="").strip()

            # Follow detail page if exists
            url = row.css("div.__TextViewGameContainer a.dapp_detaillink::attr(href)").get()
            if url:
                url = urljoin(response.url, url)
                yield scrapy.Request(
                    url,
                    meta={
                        "item": item,
                        "playwright": True,
                        "playwright_page_methods": [("wait_for_selector", "div.__TextViewGameContainer")],
                        "playwright_context": "default"
                    },
                    callback=self.parse_game,
                    dont_filter=True
                )
            else:
                yield item

    def parse_game(self, response):
        item = response.meta["item"]

        # Update Name if more detailed title exists
        name = response.css("h1::text, .game-title::text").get()
        if name:
            item["Name"] = name.strip()

        # Long description
        long_desc = response.css("div.game_desc p::text, div.game_desc::text").getall()
        if long_desc:
            item["Description"] = " ".join([d.strip() for d in long_desc if d.strip()])

        # Blockchain from detail page
        chains = response.css("div.TableGameBlockchainItems a[aria-label]::attr(title)").getall()
        if chains:
            item["Blockchain"] = ", ".join([c.strip() for c in chains if c.strip()])

        # Devices and amar_device
        devices = response.css("div.TableGameBlockchainItems a[aria-label]::attr(title)").getall()
        if devices:
            item["Device"] = ", ".join([d.strip() for d in devices if d.strip()])
            item["amar_device"] = item["Device"]

        # Status
        status = response.css("a.__ButtonStatusLive::text, a.__ButtonStatusDead::text").get()
        if status:
            item["Status"] = status.strip()

        # NFT
        nft = response.css("a[aria-label*='NFT']::attr(aria-label)").get()
        if nft:
            item["NFT"] = nft.replace(" NFT Support", "").strip()

        # F2P
        f2p = response.css("a[aria-label*='Free-To-Play']::attr(aria-label)").get()
        if f2p:
            item["F2P"] = f2p.strip()

        # P2E
        p2e = response.css("a[aria-label*='Play-To-Earn']::attr(aria-label)").getall()
        if p2e:
            item["P2E"] = ", ".join([p.strip() for p in p2e if p.strip()])

        # P2E Score
        score = response.css("span.dailychangepercentage::text").get()
        if score:
            item["P2E_Score"] = score.strip()

        yield item
