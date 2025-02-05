import os
import string
import random
import re
import time
import ddddocr
from curl_cffi import requests
from urllib.parse import quote
from loguru import logger
import threading
from faker import Faker
from PIL import Image
import io
from queue import Queue
import concurrent.futures

ocr = ddddocr.DdddOcr()
fake = Faker()

os.makedirs("static", exist_ok=True)

NUM_THREADS = 50
EMAIL_QUEUE = Queue()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
]

class Config:
    def __init__(self):
        self.email_domains = [domain.strip() for domain in os.environ.get("EMAIL_DOMAIN", "").split(';')]
        self.num_emails_per_domain = 20
        self.proxy_file = "proxy.txt"
        self.captcha_retries = 5
        self.request_timeout = 10
        self.delay_range = (0.5, 1.2)
        self.working_proxies = []  # Initialize an empty list for working proxies

config = Config()


def generate_random_email_prefix(length=20):
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_user_name():
    names = []
    for _ in range(5):
        try:
            name = fake.name()
            first_name = name.split(" ")[0]
            last_name = name.split(" ")[-1]
            names.append({"name": first_name, "surname": last_name})
        except Exception as e:
            logger.error(f"生成随机姓名失败: {e}")
            first_name = random.choice(["Alice", "Bob"])
            last_name = random.choice(["Smith", "Jones"])
            names.append({"name": first_name, "surname": last_name})
    return names

def generate_random_username():
    length = random.randint(7, 10)
    characters = string.ascii_letters
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

def load_proxies(config):
    """Loads proxies from the SOCKS environment variable and a proxy file, then tests them."""
    proxies = []

    # Load from SOCKS environment variable
    socks_env = os.environ.get("SOCKS", "")
    proxies.extend(socks_env.split(";") if socks_env else [])

    # Load from proxy.txt
    try:
        with open(config.proxy_file, "r") as f:
            proxies.extend(line.strip() for line in f)
    except FileNotFoundError:
        logger.warning(f"Proxy file '{config.proxy_file}' not found.")

    # Test and store working proxies
    test_url = "https://www.google.com"  # Or any reliable URL
    tested_proxies = test_proxies(proxies, test_url, config.request_timeout)
    config.working_proxies = tested_proxies
    logger.info(f"Found {len(config.working_proxies)} working proxies.")



def test_proxies(proxies, test_url, timeout):
    """Tests a list of proxies and returns only the working ones."""
    working_proxies = []
    for proxy_string in proxies:
        proxy_string = proxy_string.strip()
        if not proxy_string:  # Skip empty lines
            continue

        try:
            parts = proxy_string.split(":")
            if len(parts) < 3:
                logger.warning(f"Invalid proxy format: {proxy_string}")
                continue
            ip, port, proxy_type = parts[0], parts[1], parts[2].lower()
            proxy = f"{proxy_type}://{ip}:{port}"

            proxies_dict = {"http": proxy, "https": proxy} # format the proxy here.

            response = requests.get(test_url, proxies=proxies_dict, timeout=timeout)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            working_proxies.append(proxy_string)
            logger.info(f"Proxy {proxy_string} is working.")

        except requests.errors.RequestsError as e:
            logger.warning(f"Proxy {proxy_string} failed: {e}")  # Changed Exception Class

        except Exception as e:
             logger.error(f"Proxy testing encountered an error: {e}")

    return working_proxies

def get_random_proxy(working_proxies):
    """Gets a random, tested proxy from the working proxies list."""
    if not working_proxies:
        return None
    return random.choice(working_proxies)



def register_email(email, ua, proxy=None):
    try:
        with requests.Session() as session:
            if proxy:
                parts = proxy.split(":")
                if len(parts) < 3:
                    logger.warning(f"Invalid proxy format: {proxy}")
                    return

                ip, port, proxy_type = parts[0], parts[1], parts[2].lower()
                formatted_proxy = f"{proxy_type}://{ip}:{port}"
                session.proxies = {"http": formatted_proxy, "https": formatted_proxy}

                logger.info(f"Using proxy: {proxy}")

            header_base = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q;0.2",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Priority": "u=1",
            }
            url_base = "https://www.serv00.com"
            logger.info(f"Requesting base URL: {url_base}")
            try:
                resp_base = session.get(url_base, headers=header_base, impersonate="chrome124", timeout=config.request_timeout)
                resp_base.raise_for_status()
            except requests.errors.RequestsError as e: # changed here too
                logger.error(f"Failed to get base page: {e}")
                return

            logger.info(f"Base page status code: {resp_base.status_code}")
            cookie = resp_base.headers.get("set-cookie")
            logger.info(f"Cookie: {cookie}")

            if not cookie:
                logger.warning("No cookie received.")
                return

            try:
                usernames = get_user_name()
            except Exception as e:
                logger.error(f"Failed to get user name: {e}")
                return

            _ = usernames.pop()
            first_name = _["name"]
            last_name = _["surname"]
            username = generate_random_username().lower()
            logger.info(f"{email} {first_name} {last_name} {username}")

            url_create_account = "https://www.serv00.com/offer/create_new_account.json"
            header_create_account = {
                "Host": "www.serv00.com",
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q;0.2",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.serv00.com",
                "Connection": "keep-alive",
                "Referer": "https://www.serv00.com/offer/create_new_account",
                "Cookie": cookie,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",

            }

            try:
                resp_create_account = session.get(url_create_account, headers=header_create_account,
                                                  impersonate="chrome124", timeout=config.request_timeout)
                resp_create_account.raise_for_status()
            except requests.errors.RequestsError as e: # and here.
                logger.error(f"Failed to get captcha_0: {e}")
                return

            logger.info(f"captcha_0 status code: {resp_create_account.status_code}")

            content_create_account = resp_create_account.text

            try:
                content_create_account = eval(content_create_account)
                captcha_0 = content_create_account["__captcha_key"]
                logger.info(f"Extracted captcha_0: {captcha_0}")
            except (KeyError, SyntaxError, TypeError) as e:
                logger.error(f"Failed to extract captcha_0, content: {content_create_account}, error: {str(e)}")
                raise Exception(f"Failed to extract captcha_0: {str(e)}")

            captcha_url = f"https://www.serv00.com/captcha/image/{captcha_0}/"
            logger.info(f"Captcha image URL: {captcha_url}")

            image_headers = header_create_account

            for retry in range(config.captcha_retries):
                time.sleep(random.uniform(*config.delay_range))
                logger.info(f"Attempt {retry + 1} to get captcha")
                try:
                    logger.info(f"Requesting captcha image URL: {captcha_url}")
                    resp_captcha = session.get(captcha_url, headers=image_headers, impersonate="chrome124", timeout=config.request_timeout)

                    resp_captcha.raise_for_status()

                    content_captcha = resp_captcha.content

                    image_stream = io.BytesIO(content_captcha)
                    try:
                        img = Image.open(image_stream)
                        img.save("static/image.jpg")
                    except Exception as e:
                        logger.error(f"Failed to save image: {e}")
                        continue

                    captcha_1 = ocr.classification(content_captcha).lower()
                    logger.info(f"OCR result: {captcha_1}")

                    if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                        logger.warning(f"Invalid captcha: {captcha_1}, retrying")
                        continue

                    logger.info(f"Captcha: {captcha_1}")

                    url_submit = "https://www.serv00.com/offer/create_new_account.json"

                    submit_headers = header_create_account

                    data = f"first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=0&tos=on"
                    logger.info(f"POST data: {data}")

                    logger.info(f"Requesting URL: {url_submit}")
                    resp_submit = session.post(url_submit, headers=submit_headers, data=data,
                                                impersonate="chrome124", timeout=config.request_timeout)

                    resp_submit.raise_for_status()

                    logger.info(f"Submit status code: {resp_submit.status_code}")

                    content_submit = resp_submit.json()
                    logger.info(f"Submit response: {content_submit}")

                    if content_submit.get("captcha") and content_submit["captcha"][0] == "Invalid CAPTCHA":
                        logger.warning("Invalid captcha, retrying")
                        time.sleep(random.uniform(*config.delay_range))
                        continue
                    else:
                        logger.info(f"Email {email} registered successfully!")
                        return

                except Exception as e:
                    logger.error(f"Failed to get captcha or submit registration: {e}")
                finally:
                    if os.path.exists("static/image.jpg"):
                        os.remove("static/image.jpg")
                    else:
                        logger.warning("Image static/image.jpg not found, cannot delete")

            logger.warning(f"Failed to register email {email}, trying next email")

    except Exception as e:
        logger.error(f"Failed to get cookie or captcha_0: {e}")
        return

def worker(config):
    while True:
        email = EMAIL_QUEUE.get()
        if email is None:
            break

        ua = random.choice(USER_AGENTS)
        proxy = get_random_proxy(config.working_proxies)
        logger.info(f"Thread {threading.current_thread().name} using User-Agent: {ua}, email: {email}, proxy: {proxy}")

        try:
            register_email(email, ua, proxy)
        except Exception as e:
            logger.error(f"Thread {threading.current_thread().name} failed to register email {email}: {e}")
        finally:
            EMAIL_QUEUE.task_done()


def main():
    """Main function."""

    logger.info(f"Using email suffixes: {config.email_domains}")
    load_proxies(config) # Load and test proxies here
    logger.info(f"Using Proxies: {config.working_proxies}")


    # Populate email queue
    for email_domain in config.email_domains:
        for _ in range(config.num_emails_per_domain):
            email_prefix = generate_random_email_prefix()
            email = f"{email_prefix}@{email_domain}"
            EMAIL_QUEUE.put(email)


    # Use ThreadPoolExecutor for simpler thread management
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        for _ in range(NUM_THREADS):
            executor.submit(worker, config)

    EMAIL_QUEUE.join()
    logger.info("All threads completed, exiting")

if __name__ == '__main__':
    main()