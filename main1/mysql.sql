-- 테이블 작성 쿼리 (실행 : MySQL 8.0 Command Line Client)

-- 테이블 1 : reports (id, 상향 대상 기업명,보고서 올라온 날짜, 보고서를 쓴 증권사)
CREATE TABLE reports(id INT NOT NULL AUTO_INCREMENT,
    company VARCHAR(40) NOT NULL,
    date DATE NOT NULL,
    written_by VARCHAR(20) NOT NULL,
    PRIMARY KEY (id),
    );

-- 테이블 1 복붙 편한 버전
CREATE TABLE reports(id INT NOT NULL AUTO_INCREMENT,company VARCHAR(40) NOT NULL,date DATE NOT NULL,written_by VARCHAR(20) NOT NULL,PRIMARY KEY (id)); 

-- 테이블 2 : companies (기업명, 코드, 사업 분야)
CREATE TABLE companies(
    -> company VARCHAR(40) NOT NULL,
    -> code VARCHAR(6) UNIQUE NOT NULL, -- 코드 int로 받으면 안됨 : 0으로 시작하는 숫자들도 있음
    -> category VARCHAR(60),
    -> PRIMARY KEY (company)
    -> );

-- 테이블 2 복붙 편한 버전
CREATE TABLE companies(company VARCHAR(40) NOT NULL, code VARCHAR(6) UNIQUE NOT NULL, category VARCHAR(60), PRIMARY KEY (company));