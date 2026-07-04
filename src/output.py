import time


class Benchmark:

    def __init__(self):

        self.start = time.time()

    def finish(

        self,

        search,

        location,

        found,

        scraped,

        failed

    ):

        end = time.time()

        elapsed = end - self.start

        avg = elapsed / max(scraped, 1)

        print()

        print("=" * 60)

        print("CRAWLER SUMMARY")

        print("=" * 60)

        print(f"Search Query : {search}")

        print(f"Location     : {location}")

        print(f"URLs Found   : {found}")

        print(f"URLs Scraped : {scraped}")

        print(f"Failed       : {failed}")

        print(f"Elapsed Time : {elapsed:.2f} sec")

        print(f"Average      : {avg:.2f} sec/place")

        print(f"Items Export : {scraped}")

        print("=" * 60)