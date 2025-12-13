import asyncio
from ultimate_pack.feeds.data_feeds import FearGreedFeed, LongShortRatioFeed

async def main():
    print("Testing Feeds...")
    fg = FearGreedFeed()
    res = await fg.fetch()
    if res: print(f"FearGreed: {res.value}")
    
    ls = LongShortRatioFeed()
    res2 = await ls.fetch_ratio()
    if res2: print(f"L/S Ratio: {res2.long_short_ratio}")

if __name__ == "__main__":
    asyncio.run(main())
