#!/usr/bin/env python
# coding: utf-8

# In[1]:


from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
import re
import requests
import pymysql
from pymysql import IntegrityError, InterfaceError, OperationalError
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import sys
import warnings
import schedule, time
from sql_info import USER, PASSWORD, DB_NAME


warnings.filterwarnings(action = 'ignore')


# In[13]:


def FindStartDate(conn):

    try:
        date_query = "SELECT date FROM reports;"
        date_df = pd.read_sql_query(date_query, conn)
        date_df = date_df.sort_values(by = 'date', ascending = False)
        
        reports_last_date = date_df.iloc[0]['date'] # SQL에 date 타입으로 저장되어 있기 때문에 그대로 가져온다 
                                                    # iloc를 통해 인덱스 번호에 상관 없이 가장 위에 있는 데이터를 가져옴
        print("DB에 저장된 마지막 날짜 : ", reports_last_date)
        
        if reports_last_date == datetime.today().date():
            print('이미 오늘의 데이터가 있기 때문에 탐색을 종료합니다')
            sys.exit()


        start_date = reports_last_date + timedelta(days = 1)

    except IndexError:
        start_date = datetime.strptime("2022-01-01", "%Y-%m-%d").date()
        
 
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

# DB_NAME = "temp2"

def Initialize():
    """
    DB가 이미 있다 -> 해당 DB에 바로 연결만 함(DB가 있다는 이미 테이블까지 있다고 가정)
    DB가 없다면 DB_NAME
    """
    
    try:
        conn = pymysql.connect(host='localhost', user = USER, passwd = PASSWORD, db = DB_NAME, charset = 'utf8')
        
    except OperationalError:
        conn = pymysql.connect(host='localhost', user = USER, passwd = PASSWORD, charset = 'utf8')
        curs = conn.cursor()
        q = f"CREATE DATABASE {DB_NAME}"
        curs.execute(q)
        q_1 = f"USE {DB_NAME}"
        curs.execute(q_1)
        
        # 테이블 설정
        reports_q = "CREATE TABLE reports(reports_idx VARCHAR(20), company VARCHAR(40) NOT NULL, date DATE NOT NULL, written_by VARCHAR(20) NOT NULL,PRIMARY KEY (reports_idx));"
        curs.execute(reports_q)
        companies_q = "CREATE TABLE companies(company VARCHAR(40) NOT NULL, code VARCHAR(6) UNIQUE NOT NULL, category VARCHAR(60), PRIMARY KEY (company));"
        curs.execute(companies_q)

    return conn
        


def CollectDatas():
    
    # 한경 컨센서스의 보고서에 올라온 기업과 관련된 정보를 탐색 및 SQL에 데이터 저장.
    
    today = datetime.today().date()
    
    # if db == mysql:
        
    conn = Initialize() 
        
    start_date = FindStartDate(conn)
    # start_date = "2022-08-01" # 테스트용 
    
    get_name = re.compile(".+?(?=\()") # .+만 쓰면 가장 큰 범위부터 탐색해서 매칭하면 끝남. ?을 붙여 reluctant를 이용한다.
    get_code = re.compile("([0-9]{6})")
    find_idx_code = re.compile('[0-9]+')
    
    # 220817 : Chrome Headless
    opt = webdriver.ChromeOptions()
    opt.add_argument('headless')
    
    with conn.cursor() as curs:
        with webdriver.Chrome('../chromedriver.exe', chrome_options = opt) as driver:
            driver.implicitly_wait(2)
            
            # print("시작 날짜 : ", start_date, "오늘 날짜 : ", today)
            
            # 페이지 갯수 얻고 시작
            exit_switch = False
            try:
                driver.get(f'http://hkconsensus.hankyung.com/apps.analysis/analysis.list?sdate={start_date}&edate={today}&now_page=1&search_value=&report_type=UP&pagenum=80&search_text=&business_code=')
                pages = driver.find_element(By.CSS_SELECTOR, 'div.paging>a.last').get_attribute('href')
                last_page = re.compile('(?<=now_page\=)[0-9]+').findall(pages)[0] # 후방탐색
            
            except NoSuchElementException: # 아무 데이터가 없다면 이 에러가 뜸 & 강제종료
                print("아무 데이터도 없어 프로그램을 종료함")
                exit_switch = True
                
            if exit_switch:
                sys.exit(0)
            
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
                    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    CollectDatas()

