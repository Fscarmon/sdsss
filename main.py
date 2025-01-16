import os
import re
import json
import time
import pytz
import string
import random
import ddddocr
import hashlib
import asyncio
import aiohttp
import requests
from faker import Faker
from telegram import Bot
from loguru import logger
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs, urlencode
from fake_headers import Headers
from requests.exceptions import JSONDecodeError
from aiohttp.client_exceptions import ClientError, ClientConnectionError

# Configuration Constants
CONFIG_FILE = 'static/config.json'
REGISTRATION_URL = "https://www.serv00.com/offer/create_new_account"
CAPTCHA_URL = "https://www.serv00.com/captcha/image/{}/"
REGISTER_API_URL = "https://www.serv00.com/offer/create_new_account.json"
USER_AGENT_URL = "https://www.ivtool.com/random-name-generater/uinames/api/index.php?region=united%20states&gender=male&amount=5&="

# Header Constants
ACCEPT_LANGUAGES = ["en-US,en;q=0.9", "ja-JP,ja;q=0.9", "fr-FR,fr;q=0.9", "de-DE,de;q=0.9", "es-ES,es;q=0.9"]
NETWORK_TYPES = ["Wi-Fi", "4G", "5G"]

# WebGL Constants
WEBGL_VENDORS = ["Google Inc. (NVIDIA)", "Intel Inc.", "AMD Inc."]
WEBGL_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Intel(R) HD Graphics 630",
    "AMD Radeon RX 580", "NVIDIA GeForce RTX 3090", "Intel(R) Iris Plus Graphics 655",
    "AMD Radeon RX 5700 XT", "NVIDIA GeForce GTX 1660 Ti",
    "Intel(R) UHD Graphics 630 (Coffeelake)", "AMD Radeon RX 5600 XT",
    "NVIDIA Quadro RTX 8000", "Intel(R) HD Graphics 520",
    "AMD Radeon RX 480", "NVIDIA GeForce GTX 1050 Ti", "Intel(R) UHD Graphics 620", "NVIDIA GeForce RTX 3080",
    "AMD Radeon Vega 64",
    "NVIDIA Titan V", "AMD Radeon RX 6800 XT", "NVIDIA GeForce GTX 980 Ti", "Intel(R) Iris Xe Graphics"
]

# Data Constants
SCREEN_RESOLUTIONS = [1280, 1366, 1440, 1600, 1920]
SCREEN_HEIGHTS = [720, 768, 900, 1080, 1200]
FONTS = ["Arial", "Times New Roman", "Verdana", "Helvetica", "Georgia", "Courier New"]
COLOR_DEPTHS = [16, 24, 32]
PLUGINS = ["Chrome PDF Viewer", "Google Docs Offline", "AdBlock", "Grammarly", "LastPass"]


os.makedirs("static", exist_ok=True)

def get_user_name():
    try:
        resp = requests.get(USER_AGENT_URL, verify=False)
        resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = resp.json()
        return data
    except requests.exceptions.RequestException as e:
         logger.error(f"Error fetching user names: {e}")
         raise
    except JSONDecodeError as e:
        logger.error(f"Error decoding JSON from user name API {e}")
        raise


def generate_random_username():
    length = random.randint(7, 10)
    characters = string.ascii_letters
    return ''.join(random.choice(characters) for _ in range(length))

def generate_random_email(domain):
    length = random.randint(7, 10)
    characters = string.ascii_lowercase + string.digits
    username = ''.join(random.choice(characters) for _ in range(length))
    return f"{username}@{domain}"

def generate_random_headers():
    return {
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "User-Agent": Headers(os="random").generate()["User-Agent"],
        "X-Forwarded-For": Faker().ipv4(),
        "X-Network-Type": random.choice(NETWORK_TYPES),
        "X-Timezone": random.choice(pytz.all_timezones)
    }

def generate_random_data():
    screen_resolution = f"{random.choice(SCREEN_RESOLUTIONS)}x{random.choice(SCREEN_HEIGHTS)}"
    webgl_info = {
        "vendor": random.choice(WEBGL_VENDORS),
        "renderer": random.choice(WEBGL_RENDERERS)
    }
    return {
        "screen_resolution": screen_resolution,
        "color_depth": random.choice(COLOR_DEPTHS),
        "fonts": random.sample(FONTS, k=random.randint(3, len(FONTS))),
        "webgl_info": webgl_info,
        "canvas_fingerprint": hashlib.md5(os.urandom(16)).hexdigest(),
        "plugins": random.sample(PLUGINS, k=random.randint(2, 5))
    }

async def send_message(message, tg_token, tg_chat_id):
    try:
        bot = Bot(token=tg_token)
        await bot.send_message(chat_id=tg_chat_id, text=message)
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")

def parse_socks_string(socks_str):
    if socks_str.startswith("https://t.me/socks?"):
        parsed_url = urlparse(socks_str)
        query_params = parse_qs(parsed_url.query)
        server = query_params.get('server', [''])[0]
        port = query_params.get('port', [''])[0]
        user = query_params.get('user', [''])[0]
        password = query_params.get('pass', [''])[0]
        if server and port and user and password:
           return f"socks5://{user}:{password}@{server}:{port}"
    return socks_str

async def fetch_registration_page(session, headers):
    """Fetches the registration page and extracts the CSRF token and captcha_0."""
    try:
        async with session.get(url=REGISTRATION_URL, headers=headers, ssl=False) as resp:
            resp.raise_for_status() # Raise exception for bad status codes
            content = await resp.text()
            csrftoken = re.findall(r"csrftoken=(\w+);", resp.headers.get("set-cookie", ""))[0]
            captcha_0 = re.findall(r'id=\"id_captcha_0\" name=\"captcha_0\" value=\"(\w+)\">', content)[0]
            return csrftoken, captcha_0
    except (ClientError, IndexError, KeyError, re.error) as e:
        logger.error(f"Failed to fetch registration page: {e}")
        raise

async def solve_captcha(session, captcha_url, headers, max_captcha_retries):
    """Attempts to solve the captcha with retries."""
    captcha_retry = 1
    while captcha_retry <= max_captcha_retries:
      try:
        await asyncio.sleep(random.uniform(0.5, 1.2))
        logger.info("Getting Captcha")
        async with session.get(url=captcha_url, headers=headers, ssl=False) as resp:
            resp.raise_for_status()
            image_content = await resp.read()
            captcha_text = ddddocr.DdddOcr(show_ad=False).classification(image_content).upper()
            if bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_text)):
                logger.info(f"Captcha Solved: \033[1;92m{captcha_text}\033[0m")
                return captcha_text
            else:
               logger.warning(f"Captcha Failed, retrying... (Attempt {captcha_retry}/{max_captcha_retries})")
               captcha_retry += 1
               await asyncio.sleep(random.uniform(0.5, 1.2))
      except (ClientError, ddddocr.DdddOcrError, re.error) as e:
          logger.error(f"Error solving captcha: {e}")
          captcha_retry += 1
          await asyncio.sleep(random.uniform(0.5, 1.2))
    logger.error(f"Max captcha retries ({max_captcha_retries}) exceeded.")
    return None

async def submit_registration_form(session, url, headers, data):
    """Submits the registration form and handles the response."""
    try:
        async with session.post(url=url, headers=headers, data=data, ssl=False) as resp:
          resp.raise_for_status()
          return await resp.json()
    except (ClientError, JSONDecodeError) as e:
        logger.error(f"Failed to submit form, {e}")
        raise

async def handle_registration_response(content, email, username, tg_token, tg_chat_id):
    """Handles different response scenarios after registration submission."""
    if content and len(content.keys()) == 2:
       logger.success(f"\033[1;92m🎉 Account {username} created successfully!\033[0m")
       if tg_token and tg_chat_id:
          await send_message(f"Success!\nEmail: {email}\nUserName: {username}", tg_token, tg_chat_id)
       return True
    else:
        first_key = next((key for key in content if key not in ['__captcha_key', '__captcha_image_src']), None)
        if not first_key:
            logger.error(f"Unexpected response format: {content}")
            return False
        first_content = re.search(r"\['(.+?)'\]", str(content[first_key])).group(1)
        logger.info(f"\033[36m{first_key.capitalize()}: {first_content}\033[0m")
        if first_content == "An account has already been registered to this e-mail address.":
           logger.warning(f"\033[1;92mEmail already exists or account {username} created!\033[0m")
           if tg_token and tg_chat_id:
              await send_message(f"Success!\nEmail: {email}\nUserName: {username}", tg_token, tg_chat_id)
           return True
        if content.get("username") and content["username"][0] == "Maintenance time. Try again later.":
            logger.error("\033[7mMaintenance in progress, retry later...\033[0m")
            return False
        if content.get("email") and content["email"][0] == "Enter a valid email address.":
            logger.error("\033[7mInvalid email address, skipping\033[0m")
            return True
        return False


async def register_email(email, max_captcha_retries, max_email_retries, tg_token, tg_chat_id, socks_proxies):
    email_retry_count = 0
    while email_retry_count < max_email_retries:
        id_retry = 1
        try:
            random_headers = generate_random_headers()
            random_data = generate_random_data()
            User_Agent = random_headers["User-Agent"]
            Cookie = "csrftoken={}"
            header1 = {"User-Agent": User_Agent, **random_headers}
            header2 = {"Cookie": Cookie, "User-Agent": User_Agent, **random_headers}
            header3 = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": "https://www.serv00.com/offer/create_new_account",
                "Cookie": Cookie,
                "User-Agent": User_Agent,
                **random_headers
            }
            usernames = get_user_name()
            _ = usernames.pop()
            first_name = _["name"]
            last_name = _["surname"]
            username = generate_random_username().lower()
            print(""), logger.info(f"{email} {first_name} {last_name} {username}")
            async with aiohttp.ClientSession() as session:
               if socks_proxies:
                   logger.info(f"Using Proxy: {socks_proxies['http']}")
                   session.proxies = socks_proxies["http"]
               logger.info(f"Fetching Webpage - Attempt: \033[1;94m{id_retry}\033[0m.")
               try:
                  csrftoken, captcha_0 = await fetch_registration_page(session, header1)
                  header2["Cookie"] = header2["Cookie"].format(csrftoken)
                  header3["Cookie"] = header3["Cookie"].format(csrftoken)
                  captcha_text = await solve_captcha(session, CAPTCHA_URL.format(captcha_0), dict(header2, **{"Cookie": header2["Cookie"].format(csrftoken)}), max_captcha_retries)
                  if not captcha_text:
                     email_retry_count += 1
                     logger.info(f"Captcha retries ({max_captcha_retries}) hit, restarting...")
                     continue
                  data = f"csrfmiddlewaretoken={csrftoken}&first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_text}&question=free&tos=on{urlencode(random_data)}"
                  await asyncio.sleep(random.uniform(0.5, 1.2))
                  logger.info("Submitting registration form")
                  content = await submit_registration_form(session, REGISTER_API_URL, header3, data)
                  if await handle_registration_response(content, email, username, tg_token, tg_chat_id):
                     break
                  if content.get("captcha") and content["captcha"][0] == "Invalid CAPTCHA":
                     logger.warning("\033[7mCaptcha Invalid, reattempting...\033[0m")
                     await asyncio.sleep(random.uniform(0.5, 1.2))
                     continue
               except Exception as e:
                    logger.error(f"An error occurred: {e}")
                    email_retry_count += 1
                    await asyncio.sleep(random.uniform(0.5, 1.2))
                    continue
               email_retry_count += 1

        except Exception as e:
            logger.error(f"Error during email registration: {e}, restarting task")
            await asyncio.sleep(random.uniform(0.5, 1.2))
            email_retry_count += 1
            continue

        if email_retry_count >= max_email_retries:
            logger.error(f"Email {email} hit max registration attempts ({max_email_retries}), skipping...")
            continue

async def start_task(email_domains, num_emails):
    max_captcha_retries = int(os.environ.get("MAX_CAPTCHA_RETRIES", 5))
    max_email_retries = int(os.environ.get("MAX_EMAIL_RETRIES", 10))
    tg_env = os.environ.get("TG", "")
    tg_token = None
    tg_chat_id = None
    if tg_env:
        try:
            tg_token, tg_chat_id = tg_env.split(";")
        except ValueError:
            logger.error("TG environment variable wrong format, must be 'token;chat_id'")

    socks_env = os.environ.get("SOCKS", "")
    socks_proxies = None
    if socks_env:
        socks_str = parse_socks_string(socks_env)
        try:
            if socks_str.startswith("socks5://"):
                 socks_proxies = {
                    "http": socks_str,
                    "https": socks_str
                 }
            elif socks_str.startswith("https://"):
                 # Use regex to extract user, password, host and port
                match = re.match(r'https://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)', socks_str)
                if match:
                   user, password, host, port = match.groups()
                   if user and password:
                       socks_proxies = {
                        "http": f"https://{user}:{password}@{host}:{port}",
                        "https": f"https://{user}:{password}@{host}:{port}"
                         }
                   else:
                      socks_proxies = {
                        "http": f"https://{host}:{port}",
                        "https": f"https://{host}:{port}"
                       }
                else:
                    socks_proxies = {
                        "http": socks_str,
                        "https": socks_str
                   }
            else:
                logger.warning("SOCKS environment variable wrong format, please check")
        except ValueError as e:
             logger.error(f"SOCKS environment variable parsing error: {e}")
    else:
        logger.info("SOCKS environment variable not set, skipping using proxy")

    tasks = []
    for domain in email_domains:
        for _ in range(num_emails):
            email = generate_random_email(domain)
            task = asyncio.create_task(register_email(email, max_captcha_retries, max_email_retries, tg_token, tg_chat_id, socks_proxies))
            tasks.append(task)

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    try:
        resp = requests.get("https://www.serv00.com/", verify=False)
        resp.raise_for_status()
        response = requests.get('https://ping0.cc/geo', verify=False)
        response.raise_for_status()
        print(f"=============================\n\033[96m{response.text[:200]}\033[0m=============================")
        match = re.search(r'(\d+)\s*/\s*(\d+)', resp.text).group(0).replace(' ', '') if re.search(r'(\d+)\s*/\s*(\d+)', resp.text) else (logger.error('Request Failed, Check if proxy is blocked!'), exit())
        logger.info(f"\033[1;5;32mCurrent registration count:{match}\033[0m")

    except requests.exceptions.RequestException as e:
        logger.error(f"Initial request failed: {e}")
        exit()
    # Load from env vars
    email_domains_str = os.environ.get("EMAIL_DOMAIN", "")
    if not email_domains_str:
        logger.error("EMAIL_DOMAIN environment variable is not set")
        exit()
    email_domains = [domain.strip() for domain in email_domains_str.split(';')]

    try:
        num_emails = int(os.environ.get("NUM_EMAILS", 10))
    except ValueError:
        logger.error("NUM_EMAILS must be a number, using default (10)")
        num_emails = 10
    asyncio.run(start_task(email_domains, num_emails))