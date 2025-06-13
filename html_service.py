import os
from jinja2 import Environment, FileSystemLoader

root = '/Users/apple/Desktop/sd/repo'

env = Environment(loader=FileSystemLoader(root))

template = env.get_template(f"scripts/html/article_template.html")

css_list = ["https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
            "https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css",
            "https://unpkg.com/@picocss/pico@1.5.3/css/pico.min.css",
            "https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css",
            "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
            "https://cdn.jsdelivr.net/npm/foundation-sites@6.6.3/dist/css/foundation.min.css",
            "https://cdn.jsdelivr.net/npm/surface-framework@3.0.0-alpha.1/surface.min.css",
            "https://unpkg.com/spectre.css/dist/spectre.min.css",
            "https://cdnjs.cloudflare.com/ajax/libs/tachyons/4.12.0/tachyons.min.css",
                "https://cdn.tailwindcss.com"]


css_url = css_list[2]

# 準備文章資料
article_data = {
    "title": "The Bitcoin Rush: A Modern Gold Rush or a Risky Gamble?",
    "author": "Dr. John Doe",
    "date": "2025-01-27",
    "content": "In the early 21st century, the term 'Bitcoin Rush' has emerged as a metaphorical callback to the gold rushes of the 19th century. Bitcoin, the first and most prominent cryptocurrency, has revolutionized the way people think about money, investment, and technology. With its meteoric rise in value and adoption over the past decade, it has attracted both seasoned investors and everyday individuals hoping to strike digital gold. But what exactly is driving this Bitcoin Rush, and what does it mean for the future of finance?\nWhat Is Bitcoin?\nBitcoin is a decentralized digital currency that operates without the need for a central authority, like a bank or government. It is powered by blockchain technology, a distributed ledger system that ensures transparency, security, and immutability. Created in 2009 by the pseudonymous developer Satoshi Nakamoto, Bitcoin was initially a niche concept embraced by tech enthusiasts. Over time, it gained mainstream attention as a potential alternative to traditional currencies and as an investment vehicle.\n\n",
    "cover_image": "../../data/tests/0/stroke_overlay.png",
    "css_file": 'css/theme1.css'
}

html_content = template.render(**article_data)

with open(root + "/scripts/html/article1.html", "w", encoding="utf-8") as f:
    f.write(html_content)
from browser import Browser
Browser("file://" + root + "/scripts/html/article1.html")
import time
time.sleep(200)
print("HTML doc created")
