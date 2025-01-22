import re
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_image_base_name(img_url):
    path = urlparse(img_url).path
    filename = os.path.splitext(os.path.basename(path))[0]
    base_name = re.sub(r'-\d+x\d+$', '', filename)
    return base_name

def get_image_resolution(img_url):
    match = re.search(r'-(\d+)x\d+', img_url)
    return int(match.group(1)) if match else 0

def get_sitemap(url):
    MAX_SITEMAP_LENGTH = 3000
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    sitemap_urls = []

    default_sitemap_url = f"{base_url}/sitemap.xml"
    sitemap_urls.append(default_sitemap_url)

    robots_url = f"{base_url}/robots.txt"
    try:
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            for line in response.text.split('\n'):
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    sitemap_urls.append(sitemap_url)
    except requests.RequestException:
        pass

    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                if len(content) > MAX_SITEMAP_LENGTH:
                    return "Sitemap is present and of good quality"
                else:
                    return content
        except requests.RequestException:
            continue
    return "Sitemap not found"

def get_screenshot_url(url):
    params = urlencode({
        "access_key": "2de2b02f98b743f6afd8bf426bef332c",  # Replace with your API key
        "url": url,
        "full_page": "true",
        "delay": "5"
    })
    return f"https://api.apiflash.com/v1/urltoimage?{params}"

def get_page_load_time(url):
    start_time = time.time()
    requests.get(url)
    return time.time() - start_time

def has_ssl(url):
    return urlparse(url).scheme == "https"

def get_meta_tags(soup):
    meta_tags = {}
    for tag in soup.find_all('meta'):
        if 'name' in tag.attrs:
            meta_tags[tag.attrs['name']] = tag.attrs.get('content', '')
        elif 'property' in tag.attrs:
            meta_tags[tag.attrs['property']] = tag.attrs.get('content', '')
    return meta_tags

def is_mobile_friendly(url):
    mobile_options = Options()
    mobile_emulation = {"deviceName": "Nexus 5"}
    mobile_options.add_experimental_option("mobileEmulation", mobile_emulation)
    mobile_options.add_argument('--headless')
    mobile_options.add_argument('--no-sandbox')
    mobile_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=mobile_options)
    driver.set_page_load_timeout(30)
    try:
        driver.get(url)
        time.sleep(2)
        is_friendly = True  # Implement logic to determine mobile-friendliness
    except Exception:
        is_friendly = False
    finally:
        driver.quit()
    return is_friendly

def check_broken_links(soup, base_url):
    broken_links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            full_url = urljoin(base_url, href)
            try:
                response = requests.head(full_url, allow_redirects=True, timeout=5)
                if response.status_code >= 400:
                    broken_links.append(full_url)
            except requests.RequestException:
                broken_links.append(full_url)
    return broken_links

def parse_website(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        start_time = time.time()
        driver.get(url)
        load_time = time.time() - start_time

        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        for script in soup(['script', 'style', 'noscript']):
            script.decompose()
        text = ' '.join(soup.stripped_strings)

        meta_tags = get_meta_tags(soup)
        ssl = has_ssl(url)
        mobile_friendly = is_mobile_friendly(url)
        broken_links = check_broken_links(soup, url)

        image_dict = {}
        for tag in soup.find_all(['img', 'source']):
            for attr in ['src', 'data-src', 'data-original', 'srcset']:
                img_src = tag.get(attr)
                if img_src:
                    img_sources = img_src.split(',')
                    for src in img_sources:
                        src = src.strip().split(' ')[0]
                        if 'inita_CP.png' in src:
                            continue
                        img_url = urljoin(url, src)
                        img_name = get_image_base_name(img_url)
                        img_resolution = get_image_resolution(img_url)
                        if img_name not in image_dict or img_resolution > image_dict[img_name][1]:
                            image_dict[img_name] = (img_url, img_resolution)

        style_tags = soup.find_all(style=True)
        for tag in style_tags:
            style = tag['style']
            matches = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
            for background_url in matches:
                if 'inita_CP.png' in background_url:
                    continue
                img_url = urljoin(url, background_url)
                img_name = get_image_base_name(img_url)
                img_resolution = get_image_resolution(img_url)
                if img_name not in image_dict or img_resolution > image_dict[img_name][1]:
                    image_dict[img_name] = (img_url, img_resolution)

        sitemap_content = get_sitemap(url)
        screenshot_link = get_screenshot_url(url)

        images = [img_url for img_name, (img_url, img_resolution) in image_dict.items()]
        result = {
            "text": text,
            "images": images,
            "sitemap": sitemap_content,
            "screenshot": screenshot_link,
            "page_load_time": load_time,
            "meta_tags": meta_tags,
            "ssl": ssl,
            "mobile_friendly": mobile_friendly,
            "broken_links": broken_links
        }
        return result

    finally:
        driver.quit()