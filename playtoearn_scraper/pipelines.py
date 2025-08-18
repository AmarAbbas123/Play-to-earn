from scrapy.exceptions import DropItem

class DuplicatesPipeline:
    def __init__(self):
        self.seen = set()

    def process_item(self, item, spider):
        unique_key = item.get("Name")

        if unique_key in self.seen:
            raise DropItem(f"Duplicate item found: {unique_key}")
        else:
            self.seen.add(unique_key)
            return item
