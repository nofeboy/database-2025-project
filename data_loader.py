#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOBIS 영화 데이터베이스 로더
엑셀 파일에서 데이터를 읽어 MySQL 데이터베이스에 삽입
"""

import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
import sys

class KobisDBLoader:
    def __init__(self, host='localhost', user='root', password='!tpgus1260!', database='kobis_db'):
        """데이터베이스 연결 초기화"""
        self.connection = None
        try:
            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            self.cursor = self.connection.cursor()
            print("✅ MySQL 데이터베이스 연결 성공")
        except Error as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            raise

    def load_excel_data(self, file_path):
        """엑셀 파일에서 데이터 로드"""
        print(f"\n📂 엑셀 파일 로드 중: {file_path}")

        try:
            # 첫 번째 시트 읽기
            df1 = pd.read_excel(file_path, sheet_name=0, header=4)
            df1['sheet_source'] = 'sheet1'
            print(f"  - 첫 번째 시트: {len(df1)}개 행")

            # 두 번째 시트 읽기
            df2 = pd.read_excel(file_path, sheet_name=1, header=None)
            df2.columns = ['영화명', '영화명(영문)', '제작연도', '제작국가', '유형',
                           '장르', '제작상태', '감독', '제작사']
            df2['sheet_source'] = 'sheet2'
            print(f"  - 두 번째 시트: {len(df2)}개 행")

            # 데이터 합치기
            all_data = pd.concat([df1, df2], ignore_index=True)
            all_data = all_data.fillna('')

            print(f"\n✅ 총 {len(all_data)}개의 영화 데이터 로드 완료")
            return all_data

        except Exception as e:
            print(f"❌ 엑셀 파일 로드 실패: {e}")
            raise

    def step1_load_raw_data(self, df):
        """1단계: 원본 데이터를 movie_info 테이블에 삽입"""
        print("\n📥 1단계: 원본 데이터 삽입 시작")

        # 기존 데이터 삭제
        try:
            self.cursor.execute("DELETE FROM movie_info")
            self.connection.commit()
            print("  - 기존 데이터 삭제 완료")
        except:
            pass

        insert_query = """
        INSERT INTO movie_info 
        (title_ko, title_en, production_year, production_countries, 
         type, genres, production_status, director, production_company, sheet_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        batch_size = 1000
        total_rows = len(df)

        for i in range(0, total_rows, batch_size):
            batch_data = []
            for _, row in df.iloc[i:i+batch_size].iterrows():
                batch_data.append((
                    str(row['영화명']),
                    str(row['영화명(영문)']),
                    str(row['제작연도']),
                    str(row['제작국가']),
                    str(row['유형']),
                    str(row['장르']),
                    str(row['제작상태']),
                    str(row['감독']),
                    str(row['제작사']),
                    str(row['sheet_source'])
                ))

            try:
                self.cursor.executemany(insert_query, batch_data)
                self.connection.commit()
                progress = min(i+batch_size, total_rows)
                percent = (progress / total_rows) * 100
                print(f"  - 진행: {progress:,}/{total_rows:,} ({percent:.1f}%)")
            except Error as e:
                print(f"❌ 배치 삽입 오류: {e}")
                self.connection.rollback()

        print("✅ 1단계 완료!")

    def step2_normalize_data(self):
        """2단계: 데이터 정규화 및 관계 테이블 구축"""
        print("\n🔄 2단계: 데이터 정규화 시작")

        # 기존 데이터 정리
        tables_to_clear = [
            'movie_countries', 'movie_genres', 'movies',
            'directors', 'production_companies', 'genres', 'countries'
        ]

        for table in tables_to_clear:
            try:
                self.cursor.execute(f"DELETE FROM {table}")
                self.connection.commit()
            except:
                pass

        # 1. 감독 데이터 정규화
        print("  - 감독 데이터 정규화 중...")
        self.cursor.execute("""
        INSERT IGNORE INTO directors (name)
        SELECT DISTINCT TRIM(director) 
        FROM movie_info 
        WHERE director IS NOT NULL AND director != ''
        """)
        self.connection.commit()

        # 2. 제작사 데이터 정규화
        print("  - 제작사 데이터 정규화 중...")
        self.cursor.execute("""
        INSERT IGNORE INTO production_companies (name)
        SELECT DISTINCT TRIM(production_company) 
        FROM movie_info 
        WHERE production_company IS NOT NULL AND production_company != ''
        """)
        self.connection.commit()


        # 3. 장르 마스터 데이터 생성
        print("  - 장르 마스터 데이터 생성 중...")
        self.cursor.execute("SELECT DISTINCT genres FROM movie_info WHERE genres != ''")
        all_genres = set()
        for (genres,) in self.cursor.fetchall():
            genre_list = [g.strip() for g in genres.split(',')]
            all_genres.update(genre_list)

        for genre in all_genres:
            if genre:
                self.cursor.execute("INSERT IGNORE INTO genres (name) VALUES (%s)", (genre,))
        self.connection.commit()

        # 4. 국가 마스터 데이터 생성
        print("  - 국가 마스터 데이터 생성 중...")
        self.cursor.execute("SELECT DISTINCT production_countries FROM movie_info WHERE production_countries != ''")
        all_countries = set()
        for (countries,) in self.cursor.fetchall():
            country_list = [c.strip() for c in countries.split(',')]
            all_countries.update(country_list)

        for country in all_countries:
            if country:
                self.cursor.execute("INSERT IGNORE INTO countries (name) VALUES (%s)", (country,))
        self.connection.commit()

        # 5. 영화 기본 정보 삽입
        print("  - 영화 기본 정보 삽입 중...")
        self.cursor.execute("""
        INSERT INTO movies (title_ko, title_en, production_year, type, production_status, director_id, company_id)
        SELECT 
            mi.title_ko,
            mi.title_en,
            CASE 
                WHEN mi.production_year REGEXP '^[0-9]{4}$' THEN CAST(mi.production_year AS UNSIGNED)
                ELSE NULL
            END,
            mi.type,
            mi.production_status,
            d.director_id,
            pc.company_id
        FROM movie_info mi
        LEFT JOIN directors d ON TRIM(mi.director) = d.name
        LEFT JOIN production_companies pc ON TRIM(mi.production_company) = pc.name
        """)
        self.connection.commit()

        # 6. 영화-장르 관계 설정
        print("  - 영화-장르 관계 설정 중...")
        self.cursor.execute("""
        SELECT m.movie_id, mi.genres
        FROM movies m
        JOIN movie_info mi ON m.title_ko = mi.title_ko
        WHERE mi.genres != ''
        LIMIT 50000
        """)

        movie_genres_data = []
        for movie_id, genres in self.cursor.fetchall():
            genre_list = [g.strip() for g in genres.split(',')]
            for genre in genre_list:
                if genre:
                    self.cursor.execute("SELECT genre_id FROM genres WHERE name = %s", (genre,))
                    result = self.cursor.fetchone()
                    if result:
                        movie_genres_data.append((movie_id, result[0]))

        if movie_genres_data:
            batch_size = 5000
            for i in range(0, len(movie_genres_data), batch_size):
                batch = movie_genres_data[i:i+batch_size]
                self.cursor.executemany(
                    "INSERT IGNORE INTO movie_genres (movie_id, genre_id) VALUES (%s, %s)",
                    batch
                )
                self.connection.commit()

        # 7. 영화-국가 관계 설정
        print("  - 영화-국가 관계 설정 중...")
        self.cursor.execute("""
        SELECT m.movie_id, mi.production_countries
        FROM movies m
        JOIN movie_info mi ON m.title_ko = mi.title_ko
        WHERE mi.production_countries != ''
        LIMIT 50000
        """)

        movie_countries_data = []
        for movie_id, countries in self.cursor.fetchall():
            country_list = [c.strip() for c in countries.split(',')]
            for country in country_list:
                if country:
                    self.cursor.execute("SELECT country_id FROM countries WHERE name = %s", (country,))
                    result = self.cursor.fetchone()
                    if result:
                        movie_countries_data.append((movie_id, result[0]))

        if movie_countries_data:
            batch_size = 5000
            for i in range(0, len(movie_countries_data), batch_size):
                batch = movie_countries_data[i:i+batch_size]
                self.cursor.executemany(
                    "INSERT IGNORE INTO movie_countries (movie_id, country_id) VALUES (%s, %s)",
                    batch
                )
                self.connection.commit()

        print("✅ 2단계 데이터 정규화 완료!")

    def get_statistics(self):
        """데이터베이스 통계 출력"""
        print("\n📊 데이터베이스 통계")

        stats_queries = [
            ("총 영화 수", "SELECT COUNT(*) FROM movies"),
            ("총 감독 수", "SELECT COUNT(*) FROM directors"),
            ("총 제작사 수", "SELECT COUNT(*) FROM production_companies"),
            ("총 장르 수", "SELECT COUNT(*) FROM genres"),
            ("총 국가 수", "SELECT COUNT(*) FROM countries")
        ]

        for label, query in stats_queries:
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                print(f"  - {label}: {result[0]:,}개")

    def close(self):
        """데이터베이스 연결 종료"""
        if self.connection:
            self.cursor.close()
            self.connection.close()
            print("\n✅ 데이터베이스 연결 종료")

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("KOBIS 영화 데이터베이스 구축 프로그램")
    print("=" * 50)

    # 엑셀 파일 경로 확인
    excel_file = 'data/영화정보 리스트_20250601.xls'

    if not os.path.exists(excel_file):
        print(f"\n❌ 엑셀 파일을 찾을 수 없습니다!")
        print(f"   경로: {os.path.abspath(excel_file)}")
        print(f"   'data' 폴더에 '영화정보 리스트_20250601.xls' 파일을 넣어주세요.")
        input("\nEnter를 누르면 종료합니다...")
        return

    try:
        # 로더 초기화
        loader = KobisDBLoader(password='!@jinsw1006!@')  # MySQL 비밀번호 수정

        # 엑셀 데이터 로드
        df = loader.load_excel_data(excel_file)

        # 1단계: 원본 데이터 삽입
        loader.step1_load_raw_data(df)

        # 2단계: 데이터 정규화
        loader.step2_normalize_data()

        # 통계 출력
        loader.get_statistics()

        print("\n✅ 모든 작업이 완료되었습니다!")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
    finally:
        if 'loader' in locals():
            loader.close()

    input("\nEnter를 누르면 종료합니다...")

if __name__ == "__main__":
    main()