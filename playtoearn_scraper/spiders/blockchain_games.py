import scrapy
from urllib.parse import urljoin
from playtoearn_scraper.items import GameItem

class BlockchainGamesSpider(scrapy.Spider):
    name = "blockchain_games"
    allowed_domains = ["playtoearn.com"]
    seen = set()  # Deduplicate by Name only

    custom_settings = {
        "FEED_FORMAT": "csv",
        "FEED_URI": "blockchain_games.csv",
        "FEED_EXPORT_FIELDS": [
            "Name", "Description", "Category","Blockchain",  "Device",
            "Status", "NFT", "F2P", "P2E", "P2E_Score"
        ],
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.25,
        "AUTOTHROTTLE_ENABLED": True,
        "CONCURRENT_REQUESTS": 8,
        "RETRY_TIMES": 2,
    }

    def start_requests(self):
        for i in range(1, 3):
            url = f"https://playtoearn.com/blockchaingames?p={i}"
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        ("wait_for_selector", "tbody.__TableItemsSwiper tr", {"timeout":15000})
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

            # Name & Description (table page)
            item["Name"] = row.css("div.__TextViewGameContainer a.dapp_detaillink b::text").get(default="").strip()
            item["Description"] = row.css("div.__TextViewGameContainer > span::text").get(default="").strip()

            # Category
            categories = row.css("div.__TableCategoryTags div.__TagItem::text").getall()
            item["Category"] = ", ".join([c.strip() for c in categories if c.strip()])

            # Blockchain & Device
            all_data = row.css("div.TableGameBlockchainItems a[aria-label]::attr(title)").getall()
            item["Blockchain"] = all_data[0].strip() if all_data else ""
            item["Device"] = ", ".join([d.strip() for d in all_data[1:]]) if len(all_data) > 1 else ""

            # Status
            status = row.css("a[class^='__ButtonStatus']::attr(aria-label)").get()
            item["Status"] = (status or "").strip()

            # NFT
            nft = row.css("a[aria-label*='NFT']::attr(aria-label)").get()
            item["NFT"] = (nft or "").replace(" NFT Support", "").strip()

            # F2P
            allowed_f2p = {"free-to-play","crypto required","nft required","game required"}
            labels = row.css("a[aria-label]::attr(aria-label)").getall()
            item["F2P"] = next((lab.strip() for lab in labels if lab and lab.strip().casefold() in allowed_f2p), "")

            # P2E
            p2e = row.css("a[aria-label*='Play-To-Earn']::attr(aria-label)").get()
            item["P2E"] = (p2e or "None").strip()

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
                        "playwright_page_methods": [("wait_for_selector", "div.__TextViewGameContainer", {"timeout":10000})],
                        "playwright_context": "default"
                    },
                    callback=self.parse_game,
                    dont_filter=True
                )
            else:
                # Deduplicate here too if table page has no detail link
                if item["Name"] not in self.seen:
                    self.seen.add(item["Name"])
                    yield item

    def parse_game(self, response):
        item = response.meta["item"]

        # Update Name from detail page
        name = response.css("h1::text, .game-title::text").get()
        if name:
            item["Name"] = name.strip()

        # ✅ Skip duplicates by Name
        if item["Name"] in self.seen:
            return
        self.seen.add(item["Name"])

        # Long description
        long_desc = response.css("div.game_desc p::text, div.game_desc::text").getall()
        if long_desc:
            item["Description"] = " ".join([d.strip() for d in long_desc if d.strip()])

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
