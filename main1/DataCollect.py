#!/usr/bin/env python
# coding: utf-8

# In[20]:


from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
import re
import requests
import pymysql
from pymysql import IntegrityError, InterfaceError
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import sys
import warnings
import schedule, time


warnings.filterwarnings(action = 'ignore')


# In[21]:


def FindStartDate(db):

    try:
        date_query = "SELECT date FROM reports;"
        date_df = pd.read_sql_query(date_query, db)
        date_df = date_df.sort_values(by = 'date', ascending = False)

        reports_last_date = date_df['date'][0] # SQL에 date 타입으로 저장되어 있기 때문에 그대로 가져온다 

        if reports_last_date == datetime.today().date():
            print('이미 오늘의 데이터가 있기 때문에 탐색을 종료합니다')
            sys.exit()
            return 

        start_date = reports_last_date + timedelta(days = 1)

    except IndexError:
        start_date = datetime.strptime("2022-01-01", "%Y-%m-%d").date()
        
    finally:
        return start_date
        

# 네이버 증권에 접속 -> 해당 기업의 산업 코드 얻기
def GetCategory(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        category = soup.select_one('div.trade_compare>h4>em>a').text
    
    except:
        category = "몰?루"
    
    finally:
        return category 

def CollectDatas():
    
    # 한경 컨센서스의 보고서에 올라온 기업과 관련된 정보를 탐색 및 SQL에 데이터 저장.

    today = datetime.today().date()
    
    db = pymysql.connect(host='localhost', user = 'root', passwd = '0000', db = 'project02', charset = 'utf8')
    
    start_date = FindStartDate(db)

    
    get_name = re.compile(".+?(?=\()") # .+만 쓰면 가장 큰 범위부터 탐색해서 매칭하면 끝남. ?을 붙여 reluctant를 이용한다.
    get_code = re.compile("([0-9]{6})")
    find_idx_code = re.compile('[0-9]+')
    
    with db.cursor() as curs:
        with webdriver.Chrome('./chromedriver.exe') as driver:
            driver.implicitly_wait(2)
            
            # 페이지 갯수 얻고 시작
            driver.get(f'http://hkconsensus.hankyung.com/apps.analysis/analysis.list?sdate={start_date}&edate={today}&now_page=1&search_value=&report_type=UP&pagenum=80&search_text=&business_code=')
            pages = driver.find_element(By.CSS_SELECTOR, 'div.paging>a.last').get_attribute('href')
            last_page = re.compile('(?<=now_page\=)[0-9]+').findall(pages)[0] # 후방탐색
            print(last_page)
            
            for i in range(1, int(last_page) + 1):
                
                if i != 1:
                    driver.get(f'http://hkconsensus.hankyung.com/apps.analysis/analysis.list?sdate={start_date}&edate={today}&now_page={i}&search_value=&report_type=UP&pagenum=80&search_text=&business_code=')

                contents = driver.find_elements(By.CSS_SELECTOR, 'table>tbody>tr')
                
                for j in contents:
                    # 웹 스크래핑
                    try:
                        
                        date = j.find_element(By.CSS_SELECTOR, 'td.txt_number').text
                        report_idx = find_idx_code.findall(j.find_element(By.CSS_SELECTOR, 'td.text_l>a').get_attribute('href'))[0]
                        report = j.find_element(By.CSS_SELECTOR, 'td.text_l').text
                        name = get_name.findall(report)[0]
                        code = get_code.findall(report)[0]
                        
                        category = GetCategory(code) 
                        made_by = j.find_element(By.CSS_SELECTOR, 'td:nth-child(5)').text


                        print(name, code, date, category, made_by, report_idx) 
                        
                    # pymysql에 저장
                        query1 = "INSERT INTO reports(company, date, written_by, reports_idx) VALUES(%s, %s, %s, %s);"
                        curs.execute(query1, (name, date, made_by, report_idx))

                        query2 = "INSERT INTO companies(company, code, category) VALUES(%s, %s, %s);"
                        curs.execute(query2, (name, code, category))
                        
                        
                    except InterfaceError:
                        print("인터페이스 에러 발생")

                    except IntegrityError:
                        pass
                    
                    except NoSuchElementException: # 이 예외는 올라온 보고서가 없는 경우에도 작동할 거라고 기대할 수 있겠다
                        break # 이렇게 둬도 반복문 잘 작동함
                    
    db.commit()
    db.close()



# In[22]:


CollectDatas()


# In[47]:


if __name__ == "__main__":
    if datetime.today().weekday() <= 4: # 평일에만 프로그램을 가동시킴 (5, 6이 토, 일임)
        
        count = 0
        schedule.every().at("20:00").do(CollectDatas())
        
        while True:
            
            schedule.run_pending()
            time.sleep(1)
            


# In[5]:





# In[19]:





# In[ ]:




