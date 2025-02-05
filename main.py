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
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "Intel(R) HD Graphics 630", "AMD Radeon RX 580", "NVIDIA GeForce RTX 3090"
        ])
    }
    return {
        "screen_resolution": screen_resolution,
        "color_depth": random.choice([16, 24, 32]),
        "fonts": random.sample(fonts, k=random.randint(3, len(fonts))),
        "webgl_info": webgl_info,
        "canvas_fingerprint": hashlib.md5(os.urandom(16)).hexdigest(),
        "plugins": random.sample(["Chrome PDF Viewer", "Google Docs Offline", "AdBlock"], k=random.randint(2, 3))
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

def get_proxy_settings():
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
    return socks_proxies

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

    socks_proxies = get_proxy_settings()

    for domain in email_domains:
        for _ in range(num_emails):
            id_retry = 1
            email = generate_random_email(domain)
            email_retry_count = 0
            
            while email_retry_count < max_email_retries:
                try:
                    random_headers = generate_random_headers()
                    random_data = generate_random_data()
                    User_Agent = random_headers["User-Agent"]
                    Cookie = "csrftoken={}"
                    
                    with requests.Session() as session:
                        if socks_proxies:
                            session.proxies = socks_proxies
                            logger.info(f"使用代理: {socks_proxies['http']}")

                        # 获取csrftoken
                        logger.info(f"获取网页信息 - 尝试次数: \033[1;94m{id_retry}\033[0m.")
                        url1 = "https://www.serv00.com"
                        resp = session.get(url=url1, headers={"User-Agent": User_Agent, **random_headers}, verify=False)
                        headers = resp.headers
                        csrftoken = re.findall(r"csrftoken=(\w+);", headers.get("set-cookie"))[0]

                        # 准备用户数据
                        usernames = get_user_name()
                        user_info = usernames.pop()
                        first_name = user_info["name"]
                        last_name = user_info["surname"]
                        username = generate_random_username().lower()
                        print(""), logger.info(f"{email} {first_name} {last_name} {username}")

                        # 设置请求头
                        url3 = "https://www.serv00.com/offer/create_new_account.json"
                        header3 = {
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "Referer": "https://www.serv00.com/offer/create_new_account",
                            "Cookie": Cookie.format(csrftoken),
                            "User-Agent": User_Agent,
                            **random_headers
                        }

                        captcha_retry = 0
                        while captcha_retry < max_captcha_retries:
                            try:
                                # 发送初始请求获取验证码key
                                initial_data = f"csrfmiddlewaretoken={csrftoken}&first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&question=free&tos=on{urlencode(random_data)}"
                                resp = session.post(url=url3, headers=header3, data=initial_data, verify=False)
                                content = resp.json()

                                if "__captcha_key" not in content:
                                    logger.error("未能获取验证码key")
                                    break

                                captcha_key = content["__captcha_key"]
                                
                                logger.info("获取验证码")
                                captcha_url = f"https://www.serv00.com/captcha/image/{captcha_key}/"
                                resp = session.get(url=captcha_url, headers=header3, verify=False)
                                time.sleep(random.uniform(3, 10))
                                
                                captcha_image = resp.content
                                with open("static/image.jpg", "wb") as f:
                                    f.write(captcha_image)
                                
                                captcha_1 = ddddocr.DdddOcr(show_ad=False).classification(captcha_image).upper()
                                
                                if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                                    logger.warning("\033[7m验证码识别失败,正在重试...\033[0m")
                                    captcha_retry += 1
                                    continue

                                logger.info(f"识别验证码成功: \033[1;92m{captcha_1}\033[0m")

                                # 提交注册数据
                                data = f"csrfmiddlewaretoken={csrftoken}&first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_key}&captcha_1={captcha_1}&question=free&tos=on{urlencode(random_data)}"
                                resp = session.post(url=url3, headers=header3, data=data, verify=False)
                                content = resp.json()

                                if resp.status_code == 200 and len(content.keys()) == 2:
                                    logger.success(f"\033[1;92m🎉 账户 {username} 已成功创建!\033[0m")
                                    if tg_token and tg_chat_id:
                                        asyncio.run(send_message(f"Success!\nEmail: {email}\nUserName: {username}", tg_token, tg_chat_id))
                                    return

                                # 处理错误情况
                                if "username" in content and content["username"][0] == "Maintenance time. Try again later.":
                                    logger.error("\033[7m系统维护中,正在重试...\033[0m")
                                    time.sleep(random.uniform(1, 2))
                                    break

                                if "email" in content and "An account has already been registered to this e-mail address." in str(content["email"]):
                                    logger.warning(f"\033[1;92m该邮箱已存在,或账户 {username} 已成功创建🎉!")
                                    return

                                if content.get("captcha") and content["captcha"][0] == "Invalid CAPTCHA":
                                    captcha_key = content["__captcha_key"]
                                    logger.warning("\033[7m验证码错误,正在重新获取...\033[0m")
                                    time.sleep(random.uniform(0.5, 1.2))
                                    continue

                                captcha_retry += 1
                                time.sleep(random.uniform(0.5, 1.2))

                            except JSONDecodeError:
                                logger.error("\033[7m获取信息错误,正在重试...\033[0m")
                                captcha_retry += 1
                                time.sleep(random.uniform(0.5, 1.2))
                                continue

                        if captcha_retry >= max_captcha_retries:
                            email_retry_count += 1
                            logger.error(f"验证码重试次数过多({max_captcha_retries}), 准备使用新邮箱重试")
                            break

                except Exception as e:
                    logger.error(f"\033[7m发生异常:{e},正在重新开始任务...\033[0m")
                    email_retry_count += 1
                    time.sleep(random.uniform(0.5, 1.2))

                if email_retry_count >= max_email_retries:
                    logger.error(f"邮箱 {email} 尝试注册次数过多({max_email_retries}), 跳过该邮箱")
                    break

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
