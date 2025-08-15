import scrapy
from urllib.parse import urljoin
from playtoearn_scraper.items import GameItem

class BlockchainGamesSpider(scrapy.Spider):
    name = "blockchain_games"
    allowed_domains = ["playtoearn.com"]

    custom_settings = {
        "FEED_EXPORT_FIELDS": [
            "Name","Blockchain","Device",
            "Status","NFT","F2P","P2E","P2E_Score"
        ],
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.25,
        "AUTOTHROTTLE_ENABLED": True,
        "CONCURRENT_REQUESTS": 8,
        "RETRY_TIMES": 2,
    }

    def start_requests(self):
        for i in range(1, 5):  # all pages
            url = f"https://playtoearn.com/blockchaingames?p={i}"
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        ("wait_for_load_state", "networkidle")
                    ],
                    "playwright_context": "default"
                },
                callback=self.parse
            )

    def parse(self, response):
        rows = response.css("tbody.__TableItemsSwiper tr")
        self.logger.info(f"Page URL: {response.url}, rows found: {len(rows)}")

        for row in rows:
            item = GameItem()

            # Name & URL
            name_tag = row.css("div.__TextViewGameContainer a.dapp_detaillink b::text").get()
            url = row.css("div.__TextViewGameContainer a.dapp_detaillink::attr(href)").get()
            item["Name"] = (name_tag or "").strip()

            #  Blockchain
            device = row.css("div.TableGameBlockchainItems a::attr(title)").get()
            item["Device"] = (device or "").strip()

            # Categories (adjust if needed)
            categories = row.css("div.__TableCategoryTags a div.__TagItem::text").getall()
            item["Blockchain"] = ", ".join([c.strip() for c in categories if c.strip()])

            # Status using your new selector
            status = row.css("td a.__ButtonStatusLive::text").get()
            item["Status"] = (status or "").strip()

            # NFT
            nft = row.css("td a.buttonNo[aria-label*='NFT']::attr(aria-label)").get()
            item["NFT"] = (nft or "").replace(" NFT Support", "").strip()

            # F2P
            f2p = row.css("td a.buttonNo[aria-label*='FreeToPlay']::attr(aria-label)").get()
            item["F2P"] = (f2p or "").strip()

            # P2E
            p2e = row.css("td a.buttonYes[aria-label*='Play-To-Earn']::attr(aria-label)").get()
            item["P2E"] = (p2e or "").strip()

            # P2E Score
            score = row.css("td span.dailychangepercentage::text").get()
            item["P2E_Score"] = (score or "").strip()

            # Follow detail page if exists
            if url:
                url = urljoin(response.url, url)
                yield scrapy.Request(
                    url,
                    meta={
                        "item": item,
                        "playwright": True,
                        "playwright_page_methods": [
                            ("wait_for_load_state", "networkidle")
                        ],
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

        # Additional details
        chains = response.css(".chain::text, .badge-chain::text, .blockchains a::text, .blockchains::text").getall()
        devs = response.css(".device::text, .badge-device::text, .devices a::text, .devices::text").getall()
        status = response.css(".status::text, .badge-status::text, .status .value::text").get()
        nft = response.css(".nft::text, .badge-nft::text, .nft .value::text").get()
        f2p = response.css(".f2p::text, .badge-f2p::text, .f2p .value::text").get()
        p2e = response.css(".p2e::text, .badge-p2e::text, .p2e .value::text").get()
        score = response.css(".p2e-score::text, .score::text, .p2eScore::text").get()

        def join_text(sel_list):
            return ", ".join([t.strip() for t in sel_list if t and t.strip()])

        if chains: item["Blockchain"] = join_text(chains) or item["Blockchain"]
        if devs: item["Device"] = join_text(devs) or item["Device"]
        if status: item["Status"] = status.strip() or item["Status"]
        if nft: item["NFT"] = nft.strip() or item["NFT"]
        if f2p: item["F2P"] = f2p.strip() or item["F2P"]
        if p2e: item["P2E"] = p2e.strip() or item["P2E"]
        if score: item["P2E_Score"] = score.strip() or item["P2E_Score"]

        yield item
