import time
from browser import Browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ChannelScraper():
    def __init__(self, url, threshold, wait_seconds=10):
        self.browser = Browser(url, wait_seconds)
        self.threshold = threshold

    def views_to_int(self, views):
        views = views.replace(' views', '').lower()
        if 'k' in views: views = (int(float(views.replace('k', '')) * 1000))
        elif 'm' in views: views = (int(float(views.replace('m', '')) * 1000000))
        else: views = (int(views))
        return views

    def scrape_ytber(self):
        popular_xpath = '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse/ytd-two-column-browse-results-renderer/div[1]/ytd-rich-grid-renderer/div[1]/ytd-feed-filter-chip-bar-renderer/div/div/div[3]/iron-selector/yt-chip-cloud-chip-renderer[2]/div[2]/yt-formatted-string'
        WebDriverWait(self.browser.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, popular_xpath))).click()
        time.sleep(3)
        self.videos = []
        i = 1
        while True:
            video_xpath = f"/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse/ytd-two-column-browse-results-renderer/div[1]/ytd-rich-grid-renderer/div[6]/ytd-rich-item-renderer[{i}]/div/ytd-rich-grid-media/div[1]/div[3]/div[2]"
            video = self.browser.scroll_find(video_xpath)
            if video is None: break
            title = video.find_element(By.XPATH, ".//h3/a").text
            views = video.find_element(By.XPATH, ".//ytd-video-meta-block/div[1]/div[2]/span[1]").text
            views = self.views_to_int(views)
            if views < self.threshold: break
            url = video.find_element(By.XPATH, ".//h3/a").get_attribute("href")
            self.videos.append({'title': title, 'views': views, 'url': url})
            i += 1
            
if __name__ == '__main__':
    url = "https://www.youtube.com/@entreprenuership_opportunities/videos"
    threshold = 100000
    wait_seconds = 10
    scraper = ChannelScraper(url, threshold, wait_seconds)
    scraper.scrape_ytber()
    for v in scraper.videos: print(v['views'])