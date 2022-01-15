from yellow_curry import yellow_curry
from selenium import webdriver
from bs4 import BeautifulSoup as BS4
from datetime import datetime
import time
import sys
import traceback
import subprocess

URL = 'https://quasarzone.com/bbs/qb_saleinfo'
LAST_POSTNUM = '/home/sychoi/scrappers/last_postnum.txt'
CHROME_DRIVER_DIR = '/home/sychoi/chrome/chromedriver'

SLACK_CHANNEL = 'quasarzone_sale'

EXCLUDE_TITLES = ['마존', 'ali', '알리', '외장']
INCLUDE_TITLES = [
    'ssd',
    'nvme',
    '12400',
    'b660',
    '12600',
    'h610',
    'tb',
    '테라'
]

TIME_FORMAT='%Y-%m-%d %H:%M:%S'

def get_last_postnum():
    try:
        return int(subprocess.check_output('''sed -n '1,1p' {} 2> /dev/null'''.format(LAST_POSTNUM), shell=True, universal_newlines=True).strip())
    except:
        return 0
    
def update_postnum(new_postnum):
    with open(LAST_POSTNUM, 'w') as f:
        f.write(str(new_postnum))    
        
def format_error_msg(error_info):
    # 에러 내용을 슬랙에 전송할 형식으로 변환
    msg = '\n'.join(["{}: {}".format(key, str(value).strip()) for key, value in error_info.items()])
    return  '```{}```'.format(msg)
    
def send_msg(bot, msg):
    print(msg)
    bot.send(msg)


def get_soap(url):
    # 셀레니움으로 크롤링 후 bs4 오브젝트로 변환 후 리턴
    for attempt in range(3):
        try:
            driver.get(url)
            html = driver.page_source
            soap = BS4(html, 'html.parser')
            return True, soap
        except:
            error_info = {
                'Detail': traceback.format_exc(),
                'URL': url,
                'Datetime': datetime.now().strftime(TIME_FORMAT),
                'Function': sys._getframe().f_code.co_name
            }
            msg = format_error_msg(error_info)
        # 점진적으로 오래 쉬기
        time.sleep((attempt + 1) * 3)
    else:
        # MAX RETRY 만큼 시도했음에도 정상적인 응답을 받지 못했다면 False와 에러메시지 리턴
        return False, msg

def get_updates(soap):
    post_html_list = soap.find_all('div',{'class':'market-info-list'})
    new_postnum = get_last_postnum()
    
    update_list = []
    try:
        for post in reversed(post_html_list):
            uri = post.find('a').attrs['href']
            href = 'https://quasarzone.com{}'.format(uri)
            number = int(uri.split('/')[-1])
            titlehtml = post.find('span', attrs = {'class':'ellipsis-with-reply-cnt'})
            if not titlehtml:
                continue
            title = titlehtml.get_text()
            price = post.find('span', attrs = {'class':'text-orange'}).get_text()
            
            # 크롤링한 게시글 번호가 마지막으로 크롤링한 게시글 번호보다 작거나 같으면 스킵
            if number <= new_postnum:
                continue
            
            new_postnum = number
            
            # 원치 않는 키워드가 있거나, 원하는 키워드가 없을 경우 스킵
            if any(t in title.lower() for t in EXCLUDE_TITLES) or not any(t in title.lower() for t in INCLUDE_TITLES):
                continue
            
            update_list.append({
                'url': href,
                'title': title,
                'price': price,
            })
            time.sleep(1)
        
        update_postnum(new_postnum)
        return True, update_list
        
    except:
        error_info = {
            'Detail': traceback.format_exc(),
            'Datetime': datetime.now().strftime(TIME_FORMAT),
            'Function': sys._getframe().f_code.co_name
        }
        msg = format_error_msg(error_info)
        return False, msg

def terminate():
    driver.quit()
    # subprocess.run('sudo pgrep chrome | xargs kill', shell=True)
    exit()

if __name__ == "__main__":
    DEMON_NAME = 'quasarzone_scrapper.py' 
    DEMON_VER = '1.0.0'
    DEMON_DATE = '2022-01-12'
    bot = yellow_curry(SLACK_CHANNEL, demon_name=DEMON_NAME, demon_ver=DEMON_VER, demon_date=DEMON_DATE, show_demon_info=False)
    
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(CHROME_DRIVER_DIR, chrome_options=chrome_options)
        driver.implicitly_wait(3)
    except:
        error_info = {
            'Detail': traceback.format_exc(),
            'Datetime': datetime.now().strftime(TIME_FORMAT),
            'Function': sys._getframe().f_code.co_name
        }
        msg = format_error_msg(error_info)
        send_msg(bot, msg)
        terminate()
        
    res, soap = get_soap(URL)
    if not res:
        print(soap)
        send_msg(bot, soap)
        terminate()
    
    res, updates = get_updates(soap)
    if not res:
        print(updates)
        send_msg(bot, updates)
        terminate()

    msg = '할인정보가 올라왔어요\n'
    
    if updates:
        for update in updates:
            msg += "<{}|{} ({})>\n".format(update['url'], update['title'], update['price'])
        send_msg(bot, msg)
    terminate()
    