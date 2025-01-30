
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
import cloudscraper
import urllib3
import ssl
from faker import Faker
from telegram import Bot
from loguru import logger
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs, urlencode
from fake_headers import Headers
from requests.exceptions import JSONDecodeError
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

os.makedirs("static", exist_ok=True)
config_file = 'static/config.json'

class CustomAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super(CustomAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super(CustomAdapter, self).proxy_manager_for(*args, **kwargs)

def get_scraper_session(socks_proxies=None):
    """创建支持cloudflare的session，并正确处理SSL"""
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    # 添加自定义适配器
    scraper.mount('https://', CustomAdapter())
    scraper.verify = False
    
    if socks_proxies:
        scraper.proxies = socks_proxies
    
    return scraper

def get_user_name():
    """获取随机用户名"""
    url = "https://www.ivtool.com/random-name-generater/uinames/api/index.php?region=united%20states&gender=male&amount=5&="
    scraper = get_scraper_session()
    resp = scraper.get(url)
    if resp.status_code != 200:
        print(resp.status_code, resp.text)
        raise Exception("获取名字出错")
    data = resp.json()
    return data

def generate_random_username():
    """生成随机用户名"""
    length = random.randint(7, 10)
    characters = string.ascii_letters
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

def generate_random_email(domain):
    """生成随机邮箱"""
    length = random.randint(7, 10)
    characters = string.ascii_lowercase + string.digits
    username = ''.join(random.choice(characters) for _ in range(length))
    return f"{username}@{domain}"

def generate_random_headers():
    """生成随机请求头"""
    return {
        "Accept-Language": random.choice(["en-US,en;q=0.9", "ja-JP,ja;q=0.9", "fr-FR,fr;q=0.9", "de-DE,de;q=0.9", "es-ES,es;q=0.9"]),
        "User-Agent": Headers(os="random").generate()["User-Agent"],
        "X-Forwarded-For": Faker().ipv4(),
        "X-Network-Type": random.choice(["Wi-Fi", "4G", "5G"]),
        "X-Timezone": random.choice(pytz.all_timezones)
    }

def generate_random_data():
    """生成随机浏览器指纹数据"""
    screen_resolution = f"{random.choice([1280, 1366, 1440, 1600, 1920])}x{random.choice([720, 768, 900, 1080, 1200])}"
    fonts = ["Arial", "Times New Roman", "Verdana", "Helvetica", "Georgia", "Courier New"]
    webgl_info = {
        "vendor": random.choice(["Google Inc. (NVIDIA)", "Intel Inc.", "AMD Inc."]),
        "renderer": random.choice([
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "Intel(R) HD Graphics 630",
            "AMD Radeon RX 580",
            "NVIDIA GeForce RTX 3090",
            "Intel(R) Iris Plus Graphics 655"
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
    """发送Telegram消息"""
    try:
        bot = Bot(token=tg_token)
        await bot.send_message(chat_id=tg_chat_id, text=message)
    except Exception as e:
        logger.error(f"发送失败: {e}")

def parse_socks_string(socks_str):
    """解析代理字符串"""
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

def process_email(email, max_captcha_retries, max_email_retries, tg_token, tg_chat_id, socks_proxies):
    """处理单个邮箱注册"""
    email_retry_count = 0
    while email_retry_count < max_email_retries:
        try:
            random_headers = generate_random_headers()
            random_data = generate_random_data()
            User_Agent = random_headers["User-Agent"]
            Cookie = "csrftoken={}"
            url1 = "https://www.serv00.com/offer/create_new_account"
            url2 = "https://www.serv00.com"
            
            session = get_scraper_session(socks_proxies)
            session.headers.update(random_headers)
            
            logger.info(f"获取网页信息 - 尝试次数: \033[1;94m{email_retry_count + 1}\033[0m.")
            
            # 处理Cloudflare验证
            resp = session.get(url2)
            if resp.status_code == 403:
                logger.warning("检测到 Cloudflare 验证，正在尝试绕过...")
                time.sleep(random.uniform(5, 10))
                resp = session.get(url2)
            
            if resp.status_code != 200:
                logger.error(f"访问网站失败: {resp.status_code}")
                raise Exception("无法访问网站")

            headers = resp.headers
            csrftoken = re.findall(r"csrftoken=(\w+);", headers.get("set-cookie"))[0]
            resp = session.get(url1)
            content = resp.text
            
            captcha_url = "https://www.serv00.com/captcha/image/{}/"
            captcha_0 = re.findall(r'id=\"id_captcha_0\" name=\"captcha_0\" value=\"(\w+)\">', content)[0]
            
            # 处理验证码
            captcha_retry = 1
            while True:
                time.sleep(random.uniform(2, 6))
                logger.info("获取验证码")
                resp = session.get(captcha_url.format(captcha_0))
                time.sleep(random.uniform(0.5, 2))
                content = resp.content
                
                with open("static/image.jpg", "wb") as f:
                    f.write(content)
                    
                captcha_1 = ddddocr.DdddOcr(show_ad=False).classification(content).upper()
                if bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                    logger.info(f"识别验证码成功: \033[1;92m{captcha_1}\033[0m")
                    break
                else:
                    logger.warning("\033[7m验证码识别失败,正在重试...\033[0m")
                    captcha_retry += 1
                    if captcha_retry > max_captcha_retries:
                        logger.error(f"验证码识别失败次数过多({max_captcha_retries}), 正在跳过该邮箱.")
                        return
                    continue

            # 生成注册数据
            usernames = get_user_name()
            _ = usernames.pop()
            first_name = _["name"]
            last_name = _["surname"]
            username = generate_random_username().lower()
            print(""), logger.info(f"{email} {first_name} {last_name} {username}")

            # 提交注册
            data = f"csrfmiddlewaretoken={csrftoken}&first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=free&tos=on{urlencode(random_data)}"
            url3 = "https://www.serv00.com/offer/create_new_account.json"
            header3 = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": "https://www.serv00.com/offer/create_new_account",
                "Cookie": Cookie.format(csrftoken),
                "User-Agent": User_Agent,
                **random_headers
            }
            
            time.sleep(random.uniform(0.5, 1.2))
            logger.info("提交注册")
            resp = session.post(url=url3, headers=header3, data=data)
            logger.info(f'请求状态码: \033[1;93m{resp.status_code}\033[0m')
            
            try:
                content = resp.json()
                if resp.status_code == 200 and len(content.keys()) == 2:
                    logger.success(f"\033[1;92m🎉 账户 {username} 已成功创建!\033[0m")
                    if tg_token and tg_chat_id:
                        asyncio.run(send_message(f"Success!\nEmail: {email}\nUserName: {username}", tg_token, tg_chat_id))
                    return
                else:
                    first_key = next(key for key in content if key not in ['__captcha_key', '__captcha_image_src'])
                    first_content = re.search(r"\['(.+?)'\]", str(content[first_key])).group(1)
                    logger.info(f"\033[36m{first_key.capitalize()}: {first_content}\033[0m")
                    if first_content == "An account has already been registered to this e-mail address.":
                        logger.warning(f"\033[1;92m该邮箱已存在,或账户 {username} 已成功创建🎉!")
                        if tg_token and tg_chat_id:
                            asyncio.run(send_message(f"Success!\nEmail: {email}\nUserName: {username}", tg_token, tg_chat_id))
                        return
            except JSONDecodeError:
                logger.error("\033[7m获取信息错误,正在重试...\033[0m")
                time.sleep(random.uniform(0.5, 1.2))
                continue
                
        except cloudscraper.exceptions.CloudflareChallengeError as e:
            logger.error(f"Cloudflare 验证失败: {e}")
            time.sleep(random.uniform(10, 20))
            email_retry_count += 1
        except Exception as e:
            logger.error(f"\033[7m发生异常:{e},正在重新开始任务...\033[0m")
            time.sleep(random.uniform(0.5, 1.2))
            email_retry_count += 1
            
        if email_retry_count >= max_email_retries:
            logger.error(f"邮箱 {email} 尝试注册次数过多({max_email_retries}), 正在跳过该邮箱.")
            return
def start_task(email_domains, num_emails):
    """启动注册任务"""
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

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for domain in email_domains:
            for _ in range(num_emails):
                email = generate_random_email(domain)
                future = executor.submit(process_email, email, max_captcha_retries, max_email_retries, tgtoken, tg_chat_id, socks_proxies)
                futures.append(future)
        for future in futures:
            future.result()

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    
    # 初始检查
    scraper = get_scraper_session()
    try:
        resp = scraper.get("https://www.serv00.com/", verify=False)
        response = scraper.get('https://ping0.cc/geo', verify=False)
        print(f"=============================\n\033[96m{response.text[:200]}\033[0m=============================")
        
        match = re.search(r'(\d+)\s*/\s*(\d+)', resp.text)
        if not match:
            logger.error('无法获取注册量信息，请检查网站访问状态!')
            exit()
            
        match = match.group(0).replace(' ', '')
        logger.info(f"\033[1;5;32m当前注册量:{match}\033[0m")
    except Exception as e:
        logger.error(f'初始检查失败: {e}')
        exit()

    # 读取环境变量
    email_domains_str = os.environ.get("EMAIL_DOMAIN", "")
    email_domains = [domain.strip() for domain in email_domains_str.split(';')]

    num_emails = int(os.environ.get("NUM_EMAILS", 10))

    start_task(email_domains, num_emails)
