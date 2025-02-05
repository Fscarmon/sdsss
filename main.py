import os
import string
import random
import re
import time
import ddddocr
from curl_cffi import requests
from urllib.parse import quote, unquote
from loguru import logger
import threading
from faker import Faker
from PIL import Image
import io
from queue import Queue
import concurrent.futures

# 初始化 OCR 和 Faker
ocr = ddddocr.DdddOcr()
fake = Faker()

# 确保静态文件夹存在
os.makedirs("static", exist_ok=True)

NUM_THREADS = 50
EMAIL_QUEUE = Queue()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
]

class ProxyHandler:
    VALID_PROTOCOLS = {'http', 'https', 'socks4', 'socks5'}
    
    @staticmethod
    def format_proxy(proxy_string):
        """格式化代理字符串，支持多种格式"""
        if not proxy_string or not isinstance(proxy_string, str):
            return None
            
        proxy_string = proxy_string.strip()
        
        try:
            # 检查是否已经是标准格式（带认证）
            pattern_with_auth = r'^(http|https|socks4|socks5)://([^:]+):([^@]+)@([^:]+):(\d+)/?$'
            match = re.match(pattern_with_auth, proxy_string)
            if match:
                protocol, username, password, ip, port = match.groups()
                if protocol.lower() in ProxyHandler.VALID_PROTOCOLS:
                    return proxy_string
            
            # 检查是否已经是标准格式（不带认证）
            pattern_without_auth = r'^(http|https|socks4|socks5)://([^:]+):(\d+)/?$'
            match = re.match(pattern_without_auth, proxy_string)
            if match:
                protocol, ip, port = match.groups()
                if protocol.lower() in ProxyHandler.VALID_PROTOCOLS:
                    return proxy_string
                    
            # 处理其他格式
            auth_part = None
            ip_port_protocol = proxy_string
            
            # 分离认证信息
            if '@' in proxy_string:
                auth_part, ip_port_protocol = proxy_string.rsplit('@', 1)
            
            parts = ip_port_protocol.split(':')
            
            if len(parts) == 3:  # ip:port:protocol 或 username:password@ip:port:protocol
                ip, port, protocol = parts
                if protocol.lower() not in ProxyHandler.VALID_PROTOCOLS:
                    protocol = 'http'
            elif len(parts) == 2:  # ip:port
                ip, port = parts
                protocol = 'http'
            else:
                raise ValueError(f"Invalid proxy format: {proxy_string}")
            
            # 构建标准格式代理字符串
            if auth_part:
                # 处理认证信息中可能包含的特殊字符
                if ':' not in auth_part:
                    raise ValueError(f"Invalid auth format in proxy: {proxy_string}")
                username, password = auth_part.split(':', 1)
                username = quote(username)
                password = quote(password)
                return f"{protocol}://{username}:{password}@{ip}:{port}"
            else:
                return f"{protocol}://{ip}:{port}"
                
        except Exception as e:
            logger.error(f"Error formatting proxy {proxy_string}: {str(e)}")
            return None

    @staticmethod
    def test_proxy(proxy_string, test_url="https://httpbin.org/ip", timeout=10):
        """测试单个代理是否可用"""
        try:
            formatted_proxy = ProxyHandler.format_proxy(proxy_string)
            if not formatted_proxy:
                return False
                
            proxies = {
                "http": formatted_proxy,
                "https": formatted_proxy
            }
            
            with requests.Session() as session:
                response = session.get(
                    test_url,
                    proxies=proxies,
                    timeout=timeout,
                    impersonate="chrome120"
                )
                response.raise_for_status()
                
            logger.info(f"Proxy {formatted_proxy} is working")
            return True
            
        except Exception as e:
            logger.warning(f"Proxy {proxy_string} test failed: {str(e)}")
            return False

    @staticmethod
    def test_proxies(proxy_list, test_url="https://httpbin.org/ip", timeout=10):
        """测试代理列表，返回可用代理列表"""
        working_proxies = []
        
        for proxy in proxy_list:
            if ProxyHandler.test_proxy(proxy, test_url, timeout):
                formatted_proxy = ProxyHandler.format_proxy(proxy)
                if formatted_proxy:
                    working_proxies.append(formatted_proxy)
                    
        return working_proxies

    @staticmethod
    def get_random_proxy(proxy_list):
        """从代理列表中随机选择一个代理"""
        if not proxy_list:
            return None
        return random.choice(proxy_list)

class Config:
    def __init__(self):
        self.email_domains = [domain.strip() for domain in os.environ.get("EMAIL_DOMAIN", "").split(';')]
        self.num_emails_per_domain = 20
        self.proxy_file = "proxy.txt"
        self.captcha_retries = 5
        self.request_timeout = 10
        self.delay_range = (0.5, 1.2)
        self.working_proxies = []

def load_proxies_from_file(filename):
    """从文件加载代理列表"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error loading proxies from file {filename}: {str(e)}")
        return []

def generate_random_email_prefix(length=20):
    """生成随机邮箱前缀"""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_user_name():
    """获取随机用户名"""
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
    """生成随机用户名"""
    length = random.randint(7, 10)
    characters = string.ascii_letters
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

def load_proxies(config):
    """加载并测试代理"""
    proxies = []
    
    # 从环境变量加载
    socks_env = os.environ.get("SOCKS", "")
    if socks_env:
        proxies.extend(socks_env.split(";"))
    
    # 从文件加载
    file_proxies = load_proxies_from_file(config.proxy_file)
    proxies.extend(file_proxies)
    
    # 测试并保存可用代理
    config.working_proxies = ProxyHandler.test_proxies(proxies)
    logger.info(f"Found {len(config.working_proxies)} working proxies")

def register_email(email, ua, proxy=None):
    """注册邮箱的主要逻辑"""
    try:
        with requests.Session() as session:
            if proxy:
                session.proxies = {"http": proxy, "https": proxy}
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

            # 获取基础页面和Cookie
            url_base = "https://www.serv00.com"
            logger.info(f"Requesting base URL: {url_base}")
            try:
                resp_base = session.get(url_base, headers=header_base, impersonate="chrome124", timeout=config.request_timeout)
                resp_base.raise_for_status()
            except requests.errors.RequestsError as e:
                logger.error(f"Failed to get base page: {e}")
                return

            logger.info(f"Base page status code: {resp_base.status_code}")
            cookie = resp_base.headers.get("set-cookie")
            logger.info(f"Cookie: {cookie}")

            if not cookie:
                logger.warning("No cookie received.")
                return

            # 获取用户信息
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

            # 创建账号
            url_create_account = "https://www.serv00.com/offer/create_new_account.json"
            header_create_account = {
                "Host": "www.serv00.com",
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q;0.2",
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
                resp_create_account = session.get(
                    url_create_account, 
                    headers=header_create_account,
                    impersonate="chrome124", 
                    timeout=config.request_timeout
                )
                resp_create_account.raise_for_status()
            except requests.errors.RequestsError as e:
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

            # 处理验证码
            captcha_url = f"https://www.serv00.com/captcha/image/{captcha_0}/"
            logger.info(f"Captcha image URL: {captcha_url}")
            image_headers = header_create_account

            for retry in range(config.captcha_retries):
                time.sleep(random.uniform(*config.delay_range))
                logger.info(f"Attempt {retry + 1} to get captcha")
                try:
                    logger.info(f"Requesting captcha image URL: {captcha_url}")
                    resp_captcha = session.get(
                        captcha_url, 
                        headers=image_headers, 
                        impersonate="chrome124", 
                        timeout=config.request_timeout
                    )
                    resp_captcha.raise_for_status()
                    content_captcha = resp_captcha.content

                    # 保存验证码图片
                    image_stream = io.BytesIO(content_captcha)
                    try:
                        img = Image.open(image_stream)
                        img.save("static/image.jpg")
                    except Exception as e:
                        logger.error(f"Failed to save image: {e}")
                        continue

                    # OCR识别验证码
                    captcha_1 = ocr.classification(content_captcha).lower()
                    logger.info(f"OCR result: {captcha_1}")

                    if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                        logger.warning(f"Invalid captcha: {captcha_1}, retrying")
                        continue

                    logger.info(f"Captcha: {captcha_1}")

                   # 提交注册
                    url_submit = "https://www.serv00.com/offer/create_new_account.json"
                    submit_headers = header_create_account
                    data = f"first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=0&tos=on"
                    logger.info(f"POST data: {data}")

                    logger.info(f"Requesting URL: {url_submit}")
                    resp_submit = session.post(
                        url_submit,
                        headers=submit_headers,
                        data=data,
                        impersonate="chrome124",
                        timeout=config.request_timeout
                    )
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
    """工作线程函数"""
    while True:
        email = EMAIL_QUEUE.get()
        if email is None:
            break

        ua = random.choice(USER_AGENTS)
        proxy = ProxyHandler.get_random_proxy(config.working_proxies)
        logger.info(f"Thread {threading.current_thread().name} using User-Agent: {ua}, email: {email}, proxy: {proxy}")

        try:
            register_email(email, ua, proxy)
        except Exception as e:
            logger.error(f"Thread {threading.current_thread().name} failed to register email {email}: {e}")
        finally:
            EMAIL_QUEUE.task_done()

def main():
    """主函数"""
    # 初始化配置
    config = Config()
    logger.info(f"Using email suffixes: {config.email_domains}")

    # 加载并测试代理
    load_proxies(config)
    logger.info(f"Using Proxies: {config.working_proxies}")

    # 生成邮箱队列
    for email_domain in config.email_domains:
        for _ in range(config.num_emails_per_domain):
            email_prefix = generate_random_email_prefix()
            email = f"{email_prefix}@{email_domain}"
            EMAIL_QUEUE.put(email)

    # 使用线程池处理注册任务
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        for _ in range(NUM_THREADS):
            executor.submit(worker, config)

    # 等待所有任务完成
    EMAIL_QUEUE.join()
    logger.info("All threads completed, exiting")

if __name__ == '__main__':
    # 配置日志记录
    logger.add(
        "registration_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8"
    )
    main()
