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
                        url1 = "https://www.serv00.com/offer/create_new_account"
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
