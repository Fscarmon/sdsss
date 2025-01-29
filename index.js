import json
import time
import requests
from bs4 import BeautifulSoup
import ddddocr
from typing import Optional, Dict, Tuple, List
import random
import string

def generate_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))

def load_proxies(proxy_file: str) -> List[str]:
    """Load HTTP proxies from file"""
    try:
        with open(proxy_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error loading proxy file: {e}")
        return []

def get_random_proxy(proxies: List[str]) -> Optional[Dict]:
    """Get random proxy from list"""
    if not proxies:
        return None
    proxy = random.choice(proxies)
    return {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }

def signup(
    email: str,
    proxy_file: str = "./proxies.list",
    max_retries: int = 10,
    retry_delay: int = 2
) -> Dict:
    """
    Create account on serv00.com using proxy
    
    Args:
        email: User's email
        proxy_file: Path to proxy list file
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        Dict containing API response
    """
    
    # Generate username from email
    username = email.split('@')[0]
    first_name = username
    last_name = username
    
    # Load proxies
    proxies = load_proxies(proxy_file)
    if not proxies:
        raise Exception("No valid proxies found")
        
    # First request to get CSRF token
    proxy = get_random_proxy(proxies)
    try:
        response = requests.get(
            "https://www.serv00.com/offer/create_new_account",
            proxies=proxy,
            timeout=10
        )
        response.raise_for_status()
        csrftoken = response.cookies.get('csrftoken')
        if not csrftoken:
            raise Exception("Failed to get CSRF token")
    except Exception as e:
        print(f"Error getting CSRF token: {e}")
        return {"error": str(e)}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.serv00.com/offer/create_new_account",
        "Cookie": f"csrftoken={csrftoken}"
    }

    headers_json = {**headers, "Content-Type": "application/json"}
    
    ocr = ddddocr.DdddOcr(beta=True)
    ocr.set_ranges(6)
    
    captcha_cache: Optional[Tuple[str, str]] = None
    retries = 0
    
    while retries < max_retries:
        try:
            # Get new proxy for each attempt
            proxy = get_random_proxy(proxies)
            
            # Get CAPTCHA image
            if captcha_cache is None:
                captcha_id, img_url = get_captcha(headers, proxy)
            else:
                captcha_id, img_url = captcha_cache
                
            # Solve CAPTCHA
            captcha_solution = solve_captcha(img_url, headers, ocr, proxy)
            if not captcha_solution:
                captcha_cache = None
                continue
                
            # Submit form
            data = {
                "csrfmiddlewaretoken": csrftoken,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "email": email,
                "captcha_0": captcha_id,
                "captcha_1": captcha_solution.lower(),
                "question": "free",
                "tos": "on"
            }
            
            response = submit_form(data, headers, proxy)
            response_json = json.loads(response.text)
            
            # Handle response
            if "Try again later" in response.text or "Invalid CAPTCHA" in response.text:
                print(f"Attempt {retries + 1} failed: {response.text}")
                captcha_cache = (
                    response_json.get("__captcha_key"),
                    response_json.get("__captcha_image_src")
                )
                time.sleep(retry_delay)
                retries += 1
                continue
                
            return response_json
            
        except Exception as e:
            print(f"Error occurred: {e}")
            captcha_cache = None
            time.sleep(retry_delay)
            retries += 1
            
    raise Exception("Max retries exceeded")

def get_captcha(headers: Dict, proxy: Optional[Dict]) -> Tuple[str, str]:
    """Get CAPTCHA image URL and ID"""
    response = requests.get(
        "https://www.serv00.com/offer/create_new_account",
        headers=headers,
        proxies=proxy,
        timeout=10
    )
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    captcha_img = soup.find("img", class_="captcha is-")
    if not captcha_img:
        raise Exception("CAPTCHA image not found")
        
    img_src = captcha_img.get("src")
    captcha_id = img_src.split("/")[-2]
    img_url = f"https://www.serv00.com{img_src}"
    
    return captcha_id, img_url

def solve_captcha(img_url: str, headers: Dict, ocr: ddddocr.DdddOcr, proxy: Optional[Dict]) -> Optional[str]:
    """Download and solve CAPTCHA"""
    img_data = requests.get(
        img_url,
        headers=headers,
        proxies=proxy,
        timeout=10
    )
    img_data.raise_for_status()
    
    for _ in range(5):
        result = ocr.classification(img_data.content)
        if len(result) == 4:
            return result
    return None

def submit_form(data: Dict, headers: Dict, proxy: Optional[Dict]) -> requests.Response:
    """Submit account creation form"""
    response = requests.post(
        "https://www.serv00.com/offer/create_new_account.json",
        data=data,
        headers=headers,
        proxies=proxy,
        timeout=10
    )
    response.raise_for_status()
    return response

if __name__ == '__main__':
    for i in range(5):
        print(i+1, end=': ')
        print(str(signup(generate_random_string(5)+'@mu.mn')))