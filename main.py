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
            print(""), logger.info(f"{email} {first_name} {last_name} {username}")
            with requests.Session() as session:
                if socks_proxies:
                    session.proxies = socks_proxies
                    logger.info(f"使用代理: {socks_proxies['http']}")

                logger.info(f"获取网页信息 - 尝试次数: \033[1;94m{email_retry_count + 1}\033[0m.")
                resp = session.get(url=url1, headers=headers, verify=False)
                headers = resp.headers
                content = resp.text
                csrftoken = re.findall(r"csrftoken=(\w+);", headers.get("set-cookie"))[0]
                header2["Cookie"] = header2["Cookie"].format(csrftoken)
                header3["Cookie"] = header3["Cookie"].format(csrftoken)
                captcha_0 = re.findall(r'id=\"id_captcha_0\" name=\"captcha_0\" value=\"(\w+)\">', content)[0]
                captcha_retry = 1
                while True:
                    time.sleep(random.uniform(2, 6))
                    logger.info("获取验证码")
                    resp = session.get(url=captcha_url.format(captcha_0), headers=dict(header2, **{"Cookie": header2["Cookie"].format(csrftoken)}), verify=False); time.sleep(random.uniform(0.5, 2))
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
                            return  # 跳出验证码重试循环
                        continue
                if captcha_retry > max_captcha_retries:
                    email_retry_count += 1
                    logger.info(f"邮箱 {email} 验证码重试次数({max_captcha_retries})已达上限, 准备重新开始注册尝试.")
                    continue  # 跳过本次注册，重新开始尝试
                data = f"csrfmiddlewaretoken={csrftoken}&first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=free&tos=on{urlencode(random_data)}"
                time.sleep(random.uniform(0.5, 1.2))
                logger.info("请求信息")
                resp = session.post(url=url3, headers=dict(header3, **{"Cookie": header3["Cookie"].format(csrftoken)}), data=data, verify=False)
                logger.info(f'请求状态码: \033[1;93m{resp.status_code}\033[0m')
                try:
                    content = resp.json()
                    if resp.status_code == 200 and len(content.keys()) == 2:
                        logger.success(f"\033[1;92m🎉 账户 {username} 已成功创建!\033[0m")
                        if tg_token and tg_chat_id:
                            asyncio.run(send_message(f"Success!\nEmail: {email}\nUserName: {username}", tg_token,
                                                    tg_chat_id))
                        return  # 成功注册跳出循环，并跳出全局邮箱重试循环
                    else:
                        first_key = next(key for key in content if key not in ['__captcha_key', '__captcha_image_src'])
                        first_content = re.search(r"\['(.+?)'\]", str(content[first_key])).group(1)
                        logger.info(f"\033[36m{first_key.capitalize()}: {first_content}\033[0m")
                        if first_content == "An account has already been registered to this e-mail address.":
                           logger.warning(f"\033[1;92m该邮箱已存在,或账户 {username} 已成功创建🎉!")
                           if tg_token and tg_chat_id:
                               asyncio.run(send_message(f"Success!\nEmail: {email}\nUserName: {username}", tg_token,
                                                         tg_chat_id))
                           return
                except JSONDecodeError:
                    logger.error("\033[7m获取信息错误,正在重试...\033[0m")
                    time.sleep(random.uniform(0.5, 1.2))
                    continue
                if content.get("captcha") and content["captcha"][0] == "Invalid CAPTCHA":
                    captcha_0 = content["__captcha_key"]
                    logger.warning("\033[7m验证码错误,正在重新获取...\033[0m")
                    time.sleep(random.uniform(0.5, 1.2))
                    continue
                if content.get("username") and content["username"][0] == "Maintenance time. Try again later.":
                    email_retry_count += 1
                    logger.error("\033[7m系统维护中,正在重试...\033[0m")
                    time.sleep(random.uniform(0.5, 1.2))
                    return
                if content.get("email") and content["email"][0] == "Enter a valid email address.":
                    logger.error("\033[7m无效的邮箱,请重新输入.\033[0m")
                    time.sleep(random.uniform(0.5, 1.2))
                    return
                else:
                    email_retry_count += 1
                    continue
        except Exception as e:
            logger.error(f"\033[7m发生异常:{e},正在重新开始任务...\033[0m")
            time.sleep(random.uniform(0.5, 1.2))
            email_retry_count += 1
        if email_retry_count >= max_email_retries:
            logger.error(f"邮箱 {email} 尝试注册次数过多({max_email_retries}), 正在跳过该邮箱.")
            return  # 跳过此邮箱继续下一个

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


    # 1. 生成邮箱列表
    all_emails = []
    for domain in email_domains:
        for _ in range(num_emails):
             all_emails.append(generate_random_email(domain))

    # 随机打乱邮箱顺序
    random.shuffle(all_emails)

    max_workers = 50
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        # 2. 循环处理邮箱列表
        while all_emails:
            # 3. 随机选取邮箱
            email = all_emails.pop()

            # 创建线程任务
            future = executor.submit(process_email, email, max_captcha_retries, max_email_retries, tg_token, tg_chat_id, socks_proxies)
            futures.append(future)
        
        # 等待所有任务完成
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