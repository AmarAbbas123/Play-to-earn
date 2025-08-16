import scrapy
from urllib.parse import urljoin
from playtoearn_scraper.items import GameItem

class BlockchainGamesSpider(scrapy.Spider):
    name = "blockchain_games"
    allowed_domains = ["playtoearn.com"]

    custom_settings = {
        "FEED_EXPORT_FIELDS": [
            "Name","Description","Blockchain","Device",
            "Status","NFT","F2P","P2E","P2E_Score"
        ],
        "FEED_FORMAT": "csv",
        "FEED_URI": "blockchain_games.csv",
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.25,
        "AUTOTHROTTLE_ENABLED": True,
        "CONCURRENT_REQUESTS": 8,
        "RETRY_TIMES": 2,
    }

    def start_requests(self):
        # Change the range to cover all pages
        for i in range(1, 2):
            url = f"https://playtoearn.com/blockchaingames?p={i}"
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [("wait_for_load_state", "networkidle")],
                    "playwright_context": "default"
                },
                callback=self.parse
            )

    def parse(self, response):
        rows = response.css("div.TableGameItem")
        self.logger.info(f"Page URL: {response.url}, rows found: {len(rows)}")

        for row in rows:
            item = GameItem()

            # Name & short description
            name_tag = row.css("div.__TextViewGameContainer a.dapp_detaillink b::text").get()
            url = row.css("div.__TextViewGameContainer a.dapp_detaillink::attr(href)").get()
            description = row.css("div.__TextViewGameContainer > span::text").get()

            item["Name"] = (name_tag or "").strip()
            item["Description"] = (description or "").strip()

            # Blockchain & Device
            categories = row.css("div.__TableCategoryTags a div.__TagItem::text").getall()
            item["Blockchain"] = ", ".join([c.strip() for c in categories if c.strip()])
            device = row.css("div.TableGameBlockchainItems a::attr(title)").get()
            item["Device"] = (device or "").strip()

            # Status
            status = row.css("a.__ButtonStatusLive::text").get()
            item["Status"] = (status or "").strip()

            # NFT
            nft = row.css("a[aria-label*='NFT']::attr(aria-label)").get()
            item["NFT"] = (nft or "").replace(" NFT Support", "").strip()

            # F2P (Yes/No)
            f2p_yes = row.css("a[aria-label*='Free-To-Play'].buttonYes::text").get()
            f2p_no = row.css("a[aria-label*='Free-To-Play'].buttonNo::text").get()
            item["F2P"] = "Yes" if f2p_yes else "No" if f2p_no else ""

            # P2E (Yes/No)
            p2e_yes = row.css("a.buttonYes[aria-label*='Play-To-Earn']::text").get()
            p2e_no = row.css("a.buttonNo[aria-label*='Play-To-Earn']::text").get()
            item["P2E"] = "Yes" if p2e_yes else "No" if p2e_no else ""

            # P2E Score
            score = row.css("span.dailychangepercentage::text").get()
            item["P2E_Score"] = (score or "").strip()

            # Follow detail page if exists for longer description
            if url:
                url = urljoin(response.url, url)
                yield scrapy.Request(
                    url,
                    meta={
                        "item": item,
                        "playwright": True,
                        "playwright_page_methods": [("wait_for_load_state", "networkidle")],
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

        # Long description from detail page
        long_desc = response.css("div.game_desc p::text, div.game_desc::text").getall()
        if long_desc:
            item["Description"] = " ".join([d.strip() for d in long_desc if d.strip()])

        # Other fields from detail page
        chains = response.css(".chain::text, .badge-chain::text, .blockchains a::text").getall()
        devs = response.css(".device::text, .badge-device::text, .devices a::text").getall()
        status = response.css(".status::text, .badge-status::text, .status .value::text").get()
        nft = response.css(".nft::text, .badge-nft::text, .nft .value::text").get()
        f2p = response.css("a.buttonYes[aria-label*='Free-To-Play']::text").get()
        if not f2p:
            f2p_no = response.css("a.buttonNo[aria-label*='Free-To-Play']::text").get()
            f2p = "No" if f2p_no else ""
        else:
            f2p = "Yes"
        p2e = response.css("a.buttonYes[aria-label*='Play-To-Earn']::text").get()
        if not p2e:
            p2e_no = response.css("a.buttonNo[aria-label*='Play-To-Earn']::text").get()
            p2e = "No" if p2e_no else ""
        else:
            p2e = "Yes"
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
