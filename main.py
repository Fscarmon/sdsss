from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions
import os
import re
import json
import time
import string
import random
import ddddocr
import hashlib
from faker import Faker
import requests
from loguru import logger
from datetime import datetime
from urllib.parse import quote, urlencode
from fake_headers import Headers
import pytz

os.makedirs("static", exist_ok=True)

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

def start_task(email_domains, num_emails):
   max_email_retries = int(os.environ.get("MAX_EMAIL_RETRIES", 10))
   email_retry_count = 0
   for domain in email_domains:
       for _ in range(num_emails):
           email = generate_random_email(domain)
           while email_retry_count < max_email_retries:
               try:
                   options = ChromiumOptions()
                   
                   random_headers = generate_random_headers()
                   User_Agent = random_headers["User-Agent"]
                   
                   options.set_argument("--user-agent=" + User_Agent)
                   options.set_argument("--disable-blink-features=AutomationControlled")
                   if os.environ.get("SOCKS", ""):
                       options.set_argument(f'--proxy-server={os.environ.get("SOCKS", "")}')
                       
                   options.set_headers({'Accept-Language': random_headers["Accept-Language"]})
                   
                   options.headless = False  # for debugging
                   page = ChromiumPage(options=options)

                   # Registration flow
                   url1 = "https://www.serv00.com/offer/create_new_account"
                   page.get(url1)

                   # Wait for Cloudflare to complete (adjust timeout as needed)
                   page.wait.sleep(5)

                   # Get CSRF token
                   content = page.html
                   csrftoken = re.findall(r"csrftoken=(\w+);", page.headers.get("set-cookie"))[0]

                   # Get captcha_0
                   captcha_0 = re.findall(r'id=\"id_captcha_0\" name=\"captcha_0\" value=\"(\w+)\">', content)[0]

                   # Solve Captcha
                   captcha_url = f"https://www.serv00.com/captcha/image/{captcha_0}/"
                   page.get(captcha_url)

                   # Save captcha image
                   image_path = "static/image.jpg"
                   page.save.page(image_path)  # Save the whole page as an image (debugging)
                   page.get_img(index=1).save(image_path)  # Assuming captcha is the first img

                   # OCR
                   with open(image_path, "rb") as f:
                       captcha_1 = ddddocr.DdddOcr(show_ad=False).classification(f.read()).upper()
                   logger.info(f"识别验证码: \033[1;92m{captcha_1}\033[0m")
                   if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                       logger.warning("\033[7m验证码识别失败，跳过此次尝试...\033[0m")
                       page.close()
                       email_retry_count += 1
                       continue

                   usernames = get_user_name()
                   _ = usernames.pop()
                   first_name = _["name"]
                   last_name = _["surname"]
                   username = generate_random_username().lower()
                   logger.info(f"{email} {first_name} {last_name} {username}")

                   # Fill in the form using DrissionPage
                   page.ele('#id_first_name').input(first_name)
                   page.ele('#id_last_name').input(last_name)
                   page.ele('#id_username').input(username)
                   page.ele('#id_email').input(email)
                   page.ele('#id_captcha_0').input(captcha_0)
                   page.ele('#id_captcha_1').input(captcha_1)
                   page.ele('#id_tos').click()  # Assuming 'tos' is the ID of the checkbox

                   # Submit the form
                   page.ele("text:'Create my account'").click()

                   # Wait for the response and check for success
                   page.wait.sleep(3)
                   if "Registration complete" in page.html or "registrazione completata" in page.html:
                      logger.success(f"\033[1;92m🎉 账户 {username} 已成功创建!\033[0m")
                      break
                   else:
                      logger.warning(f"\033[7m注册失败，正在重试...\033[0m\n{page.html}")
                      email_retry_count += 1
                      time.sleep(1)

                   # Close page
                   page.close()

               except Exception as e:
                   logger.error(f"\033[7m发生异常:{e},正在重新开始任务...\033[0m")
                   email_retry_count += 1
                   time.sleep(1)

               if email_retry_count >= max_email_retries:
                   logger.error(f"邮箱 {email} 尝试注册次数过多({max_email_retries}), 正在跳过该邮箱.")
                   break

if __name__ == "__main__":
   os.system("cls" if os.name == "nt" else "clear")
   resp = requests.get("https://www.serv00.com/", verify=False)
   response = requests.get('https://ping0.cc/geo', verify=False)
   print(f"=============================\n\033[96m{response.text[:200]}\033[0m=============================")
   match = re.search(r'(\d+)\s*/\s*(\d+)', resp.text).group(0).replace(' ', '') if resp.status_code == 200 and re.search(r'(\d+)\s*/\s*(\d+)', resp.text) else (logger.error('请求失败,请检查代理IP是否封禁!'), exit())
   logger.info(f"\033[1;5;32m当前注册量:{match}\033[0m")

   email_domains_str = os.environ.get("EMAIL_DOMAIN", "")
   email_domains = [domain.strip() for domain in email_domains_str.split(';')]

   num_emails = int(os.environ.get("NUM_EMAILS", 10))

   start_task(email_domains, num_emails)
