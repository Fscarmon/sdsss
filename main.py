import os
import re
import json
import time
import pytz
import string
import random
import ddddocr
import inspect
import hashlib
import asyncio
import requests
from faker import Faker
from telegram import Bot
from loguru import logger
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs, urlencode
from fake_headers import Headers
from requests.exceptions import JSONDecodeError
from concurrent.futures import ThreadPoolExecutor

os.makedirs("static", exist_ok=True)
config_file = 'static/config.json'

def get_user_name():
    url = "https://www.ivtool.com/random-name-generater/uinames/api/index.php?region=united%20states&gender=male&amount=5&="
    resp = requests.get(url, verify=False)
    if resp.status_code != 200:
        print(resp.status_code, resp.text)
        raise Exception("获取名字出错")
    data = resp.json()
    return data

def generate_random_username():
    length = random.randint(7, 10)
    characters = string.ascii_letters
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

def generate_random_email(domain):
    length = random.randint(7, 10)
    characters = string.ascii_lowercase + string.digits
    username = ''.join(random.choice(characters) for _ in range(length))
    return f"{username}@{domain}"

def generate_random_headers():
    return {
        "Accept-Language": random.choice(["en-US,en;q=0.9", "ja-JP,ja;q=0.9", "fr-FR,fr;q=0.9", "de-DE,de;q=0.9", "es-ES,es;q=0.9"]),
        "User-Agent": Headers(os="random").generate()["User-Agent"],
        "X-Forwarded-For": Faker().ipv4(),
        "X-Network-Type": random.choice(["Wi-Fi", "4G", "5G"]),
        "X-Timezone": random.choice(pytz.all_timezones)
    }

def generate_random_data():
    screen_resolution = f"{random.choice([1280, 1366, 1440, 1600, 1920])}x{random.choice([720, 768, 900, 1080, 1200])}"
    fonts = ["Arial", "Times New Roman", "Verdana", "Helvetica", "Georgia", "Courier New"]
    webgl_info = {
        "vendor": random.choice(["Google Inc. (NVIDIA)", "Intel Inc.", "AMD Inc."]),
        "renderer": random.choice([
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Intel(R) HD Graphics 630",
            "AMD Radeon RX 580", "NVIDIA GeForce RTX 3090", "Intel(R) Iris Plus Graphics 655",
            "AMD Radeon RX 5700 XT", "NVIDIA GeForce GTX 1660 Ti",
            "Intel(R) UHD Graphics 630 (Coffeelake)", "AMD Radeon RX 5600 XT",
            "NVIDIA Quadro RTX 8000", "Intel(R) HD Graphics 520",
            "AMD Radeon RX 480", "NVIDIA GeForce GTX 1050 Ti", "Intel(R) UHD Graphics 620", "NVIDIA GeForce RTX 3080", "AMD Radeon Vega 64",
            "NVIDIA Titan V", "AMD Radeon RX 6800 XT", "NVIDIA GeForce GTX 980 Ti", "Intel(R) Iris Xe Graphics"
        ])
    }
    return {
        "screen_resolution": screen_resolution,
        "color_depth": random.choice([16, 24, 32]),
        "fonts": random.sample(fonts, k=random.randint(3, len(fonts))),
        "webgl_info": webgl_info,
        "canvas_fingerprint": hashlib.md5(os.urandom(16)).hexdigest(),
        "plugins": random.sample(["Chrome PDF Viewer", "Google Docs Offline", "AdBlock", "Grammarly", "LastPass"], k=random.randint(2, 5))
    }

async def send_message(message, tg_token, tg_chat_id):
    try:
        bot = Bot(token=tg_token)
        await bot.send_message(chat_id=tg_chat_id, text=message)
    except Exception as e:
        logger.error(f"发送失败: {e}")


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


# 主要修改 process_email 函数中获取 csrftoken 的部分
def process_email(email, max_captcha_retries, max_email_retries, tg_token, tg_chat_id, socks_proxies):
    email_retry_count = 0
    while email_retry_count < max_email_retries:
        try:
            random_headers = generate_random_headers()
            random_data = generate_random_data()
            User_Agent = random_headers["User-Agent"]
            Cookie = "csrftoken={}"
            url1 = "https://www.serv00.com/offer/create_new_account"
            headers = {"User-Agent": User_Agent, **random_headers}
            captcha_url = "https://www.serv00.com/captcha/image/{}/"
            header2 = {"Cookie": Cookie, "User-Agent": User_Agent, **random_headers}
            url3 = "https://www.serv00.com/offer/create_new_account.json"
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
            logger.info(f"{email} {first_name} {last_name} {username}")
            
            with requests.Session() as session:
                session.verify = False
                if socks_proxies:
                    session.proxies = socks_proxies
                    logger.info(f"使用代理: {socks_proxies['http']}")
                
                logger.info(f"获取网页信息 - 尝试次数: \033[1;94m{email_retry_count + 1}\033[0m.")
                
                # 增加重试机制获取初始页面
                for _ in range(3):
                    try:
                        resp = session.get(url=url1, headers=headers, timeout=10)
                        resp.raise_for_status()
                        break
                    except requests.RequestException as e:
                        logger.warning(f"获取页面失败，正在重试: {e}")
                        time.sleep(random.uniform(1, 3))
                else:
                    raise Exception("无法获取初始页面")

                content = resp.text
                logger.debug(f"响应头: {dict(resp.headers)}")
                
                # 尝试多种方式获取 csrf token
                csrftoken = None
                
                # 1. 从 cookies 中获取
                if 'csrftoken' in session.cookies:
                    csrftoken = session.cookies['csrftoken']
                    logger.debug("从 cookies 获取到 csrftoken")
                
                # 2. 从 set-cookie 头中获取
                if not csrftoken and 'Set-Cookie' in resp.headers:
                    csrf_match = re.search(r'csrftoken=([^;]+)', resp.headers['Set-Cookie'])
                    if csrf_match:
                        csrftoken = csrf_match.group(1)
                        logger.debug("从 Set-Cookie 获取到 csrftoken")
                
                # 3. 从页面内容中获取 csrfmiddlewaretoken
                if not csrftoken:
                    csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\'](.*?)["\']', content)
                    if csrf_match:
                        csrftoken = csrf_match.group(1)
                        logger.debug("从页面内容获取到 csrfmiddlewaretoken")
                
                # 4. 从 meta 标签获取
                if not csrftoken:
                    csrf_match = re.search(r'<meta name="csrf-token" content="(.*?)"', content)
                    if csrf_match:
                        csrftoken = csrf_match.group(1)
                        logger.debug("从 meta 标签获取到 csrf-token")

                if not csrftoken:
                    logger.error("页面响应内容:")
                    logger.error(content[:500])  # 只打印前500个字符
                    raise Exception("无法获取 csrftoken")

                logger.info(f"成功获取 csrftoken: {csrftoken[:5]}...")  # 只显示token前5位
                
                header2["Cookie"] = header2["Cookie"].format(csrftoken)
                header3["Cookie"] = header3["Cookie"].format(csrftoken)
                
                # 获取 captcha_0
                captcha_match = re.search(r'name="captcha_0" value="(\w+)"', content)
                if not captcha_match:
                    logger.error("页面内容片段:")
                    logger.error(content[:500])
                    raise Exception("无法获取验证码 ID")
                
                captcha_0 = captcha_match.group(1)
                logger.info(f"获取到验证码ID: {captcha_0}")

                # 其余代码保持不变...
                [原有的验证码处理和表单提交代码]

        except Exception as e:
            logger.error(f"\033[7m发生异常: {str(e)}, 正在重新开始任务...\033[0m")
            logger.debug(f"详细错误: {repr(e)}")
            email_retry_count += 1
            time.sleep(random.uniform(1, 3))
            continue
            
        if email_retry_count >= max_email_retries:
            logger.error(f"邮箱 {email} 尝试注册次数过多({max_email_retries}), 正在跳过该邮箱.")
            return



def start_task(email_domains, num_emails):
    max_captcha_retries = int(os.environ.get("MAX_CAPTCHA_RETRIES", 5))
    max_email_retries = int(os.environ.get("MAX_EMAIL_RETRIES", 10))
    tg_env = os.environ.get("TG", "")
    tg_token = None
    tg_chat_id = None
    if tg_env:
        try:
            tg_token, tg_chat_id = tg_env.split(";")
        except ValueError:
            logger.error("TG环境变量格式错误，请使用'token;chat_id'格式")

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
                logger.warning("SOCKS 环境变量格式不正确，请检查")
        except ValueError as e:
             logger.error(f"SOCKS 环境变量格式错误: {e}")
    else:
        logger.info("SOCKS 环境变量未设置，将不使用代理")

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for domain in email_domains:
            for _ in range(num_emails):
                email = generate_random_email(domain)
                future = executor.submit(process_email, email, max_captcha_retries, max_email_retries, tg_token, tg_chat_id, socks_proxies)
                futures.append(future)
        for future in futures:
             future.result()
            


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    resp = requests.get("https://www.serv00.com/", verify=False)
    response = requests.get('https://ping0.cc/geo', verify=False)
    print(f"=============================\n\033[96m{response.text[:200]}\033[0m=============================")
    match = re.search(r'(\d+)\s*/\s*(\d+)', resp.text).group(0).replace(' ', '') if resp.status_code == 200 and re.search(r'(\d+)\s*/\s*(\d+)', resp.text) else (logger.error('请求失败,请检查代理IP是否封禁!'), exit())
    logger.info(f"\033[1;5;32m当前注册量:{match}\033[0m")

    # 读取环境变量
    email_domains_str = os.environ.get("EMAIL_DOMAIN", "")
    email_domains = [domain.strip() for domain in email_domains_str.split(';')]

    num_emails = int(os.environ.get("NUM_EMAILS", 10))

    start_task(email_domains, num_emails)