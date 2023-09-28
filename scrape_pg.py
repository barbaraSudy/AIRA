from actions.scraper import Scraper
import os
import uuid

root_dir = os.path.abspath(os.path.dirname( __file__ ))
directory_name = uuid.uuid4().hex
dir_path = os.path.dirname(f"./outputs/{directory_name}/")
output_path = os.path.join(root_dir, "outputs", directory_name)
os.makedirs(output_path, exist_ok=True)



urllist = [
    'https://remkim.com/blog/how-to-fix-google--looks-like-youre-in-a-different-country-from-the-family-manager',
    'https://www.msn.com/de-ch/nachrichten/digital/nach-iphone-update-5-dinge-die-sie-bei-ios-17-sofort-aktivieren-sollten/ar-AA1h3kEu?ocid=msedgntp&cvid=01cdc339880e4a31910ffd3a4229d7ef&ei=19',
    'https://superfastpython.com/asyncio-gather/',
    'https://stackoverflow.com/questions/9786102/how-do-i-parallelize-a-simple-python-loop',
    'https://www.blick.ch/',
    'https://www.nau.ch/news/schweiz/elternteil-statt-mami-papi-das-sagt-ein-psychologe-66605485',
    'https://www.finanzen.net/nachricht/aktien/eu-kartellvorschriften-nasdaq-titel-intel-aktie-in-rot-eu-verhaengt-millionenschwere-geldbusse-gegen-intel-12851552',
    'https://www.tagesanzeiger.ch/kritik-an-70-millionen-deal-was-will-die-schweizer-post-wirklich-mit-dem-wald-in-deutschland-500159064798',
]

scraper = Scraper()
results = scraper.scrape_parallel(urllist, output_path)
# c = CrawlerProcess({
#     'USER_AGENT': 'Mozilla/5.0'
# })
# c.crawl(Scraper, urllist=urllist, output_dir=output_path)
# c.start()
# print("------------------------------------------------------------------------------------")
# print(results)