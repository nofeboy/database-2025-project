#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOBIS 영화 검색 시스템 - Flask 웹 애플리케이션 (업그레이드 버전)
"""

from flask import Flask, render_template_string, request, jsonify
import mysql.connector
from mysql.connector import Error
import json

app = Flask(__name__)

# 데이터베이스 설정
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '!@jinsw1006!@',  # MySQL 비밀번호
    'database': 'kobis_db',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_db_connection():
    """데이터베이스 연결"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"데이터베이스 연결 오류: {e}")
        return None

def get_filter_options():
    """검색 필터 옵션 가져오기"""
    connection = get_db_connection()
    if not connection:
        return {}

    cursor = connection.cursor()
    options = {}

    try:
        # 장르 목록
        cursor.execute("SELECT DISTINCT name FROM genres ORDER BY name")
        options['genres'] = [row[0] for row in cursor.fetchall()]

        # 국가 목록 (대륙별로 분류)
        cursor.execute("SELECT DISTINCT name FROM countries ORDER BY name")
        all_countries = [row[0] for row in cursor.fetchall() if row[0]]

        # 대륙별 국가 분류
        continent_mapping = {
            '아시아': ['한국', '일본', '중국', '대만', '홍콩', '태국', '인도', '말레이시아', '싱가포르', '필리핀', '인도네시아', '베트남', '미얀마', '이란', '이스라엘', '터키', '아랍에미리트', '카자흐스탄', '우즈베키스탄', '아프가니스탄', '파키스탄', '네팔', '방글라데시', '스리랑카', '몽골', '브루나이', '요르단', '레바논', '시리아', '이라크', '카타르', '사우디아라비아', '예멘', '오만', '바레인', '쿠웨이트', '동티모르', '라오스', '캄보디아', '부탄'],
            '북미주': ['미국', '캐나다', '멕시코'],
            '유럽': ['영국', '프랑스', '독일', '이탈리아', '스페인', '러시아', '네덜란드', '벨기에', '스위스', '오스트리아', '덴마크', '스웨덴', '노르웨이', '핀란드', '폴란드', '체코', '헝가리', '그리스', '포르투갈', '루마니아', '불가리아', '크로아티아', '세르비아', '슬로바키아', '슬로베니아', '리투아니아', '라트비아', '에스토니아', '아일랜드', '아이슬란드', '룩셈부르크', '모나코', '몰타', '키프로스', '알바니아', '북마케도니아', '몰도바', '보스니아헤르체고비나', '코소보', '몬테네그로', '우크라이나', '벨라루스', '조지아', '아르메니아', '아제르바이잔'],
            '남미주': ['브라질', '아르헨티나', '칠레', '페루', '콜롬비아', '베네수엘라', '우루과이', '파라과이', '에콰도르', '볼리비아', '가이아나', '수리남'],
            '아프리카': ['남아프리카공화국', '이집트', '모로코', '나이지리아', '케냐', '가나', '에티오피아', '튀니지', '알제리', '우간다', '짐바브웨', '카메룬', '세네갈', '마다가스카르', '앙골라', '모잠비크', '탄자니아', '코트디부아르', '수단', '리비아'],
            '오세아니아': ['호주', '뉴질랜드', '피지', '파푸아뉴기니', '사모아']
        }

        options['countries_by_continent'] = {}
        for continent, continent_countries in continent_mapping.items():
            options['countries_by_continent'][continent] = [c for c in all_countries if c in continent_countries]

        # 기타 국가들 (분류되지 않은)
        classified_countries = set()
        for countries in continent_mapping.values():
            classified_countries.update(countries)

        other_countries = [c for c in all_countries if c not in classified_countries]
        if other_countries:
            options['countries_by_continent']['기타'] = other_countries

        # 제작상태 목록
        cursor.execute("SELECT DISTINCT production_status FROM movies WHERE production_status IS NOT NULL ORDER BY production_status")
        options['production_status'] = [row[0] for row in cursor.fetchall() if row[0]]

        # 유형 목록
        cursor.execute("SELECT DISTINCT type FROM movies WHERE type IS NOT NULL ORDER BY type")
        options['types'] = [row[0] for row in cursor.fetchall() if row[0]]

    except Error as e:
        print(f"필터 옵션 로드 오류: {e}")
    finally:
        cursor.close()
        connection.close()

    return options

def get_chosung(text):
    """한글 초성 추출 함수"""
    CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    if not text:
        return ""

    first_char = text[0]

    # 한글인지 확인
    if '가' <= first_char <= '힣':
        char_code = ord(first_char) - ord('가')
        chosung_index = char_code // 588  # 588 = 21(중성) * 28(종성)
        return CHOSUNG_LIST[chosung_index]

    return first_char

def search_movies(params):
    """영화 검색 쿼리 실행"""
    connection = get_db_connection()
    if not connection:
        return {'results': [], 'total': 0, 'page': 1, 'per_page': 20, 'total_pages': 0}

    cursor = connection.cursor(dictionary=True)

    # 기본 쿼리
    query = """
        SELECT DISTINCT
            m.movie_id,
            m.title_ko,
            m.title_en,
            m.production_year,
            m.type,
            m.production_status,
            d.name AS director_name,
            pc.name AS company_name,
            GROUP_CONCAT(DISTINCT g.name ORDER BY g.name SEPARATOR ', ') AS genres,
            GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') AS countries
        FROM movies m
        LEFT JOIN directors d ON m.director_id = d.director_id
        LEFT JOIN production_companies pc ON m.company_id = pc.company_id
        LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
        LEFT JOIN genres g ON mg.genre_id = g.genre_id
        LEFT JOIN movie_countries mc ON m.movie_id = mc.movie_id
        LEFT JOIN countries c ON mc.country_id = c.country_id
        WHERE 1=1
    """

    query_params = []

    # 영화명 검색
    if params.get('movieTitle'):
        query += " AND (m.title_ko LIKE %s OR m.title_en LIKE %s)"
        search_term = f"%{params['movieTitle']}%"
        query_params.extend([search_term, search_term])

    # 감독명 검색
    if params.get('directorName'):
        query += " AND d.name LIKE %s"
        query_params.append(f"%{params['directorName']}%")

    # 제작연도 검색
    if params.get('yearFrom') and params['yearFrom'] != '--전체--':
        query += " AND m.production_year >= %s"
        query_params.append(int(params['yearFrom']))

    if params.get('yearTo') and params['yearTo'] != '--전체--':
        query += " AND m.production_year <= %s"
        query_params.append(int(params['yearTo']))

    # 제작상태 검색 (복수 선택)
    if params.get('productionStatus') and len(params.get('productionStatus', [])) > 0:
        placeholders = ', '.join(['%s'] * len(params['productionStatus']))
        query += f" AND m.production_status IN ({placeholders})"
        query_params.extend(params['productionStatus'])

    # 유형 검색 (복수 선택)
    if params.get('movieType') and len(params.get('movieType', [])) > 0:
        placeholders = ', '.join(['%s'] * len(params['movieType']))
        query += f" AND m.type IN ({placeholders})"
        query_params.extend(params['movieType'])

    # 장르 검색 (복수 선택)
    if params.get('genre') and len(params.get('genre', [])) > 0:
        genre_conditions = []
        for _ in params['genre']:
            genre_conditions.append("EXISTS (SELECT 1 FROM movie_genres mg2 JOIN genres g2 ON mg2.genre_id = g2.genre_id WHERE mg2.movie_id = m.movie_id AND g2.name = %s)")
        query += f" AND ({' OR '.join(genre_conditions)})"
        query_params.extend(params['genre'])

    # 국가 검색 (복수 선택)
    if params.get('country') and len(params.get('country', [])) > 0:
        country_conditions = []
        for _ in params['country']:
            country_conditions.append("EXISTS (SELECT 1 FROM movie_countries mc2 JOIN countries c2 ON mc2.country_id = c2.country_id WHERE mc2.movie_id = m.movie_id AND c2.name = %s)")
        query += f" AND ({' OR '.join(country_conditions)})"
        query_params.extend(params['country'])

    # 영화명 인덱싱
    if params.get('titleIndex'):
        # 한글 자음인 경우
        if params['titleIndex'] in ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']:
            # 해당 초성으로 시작하는 모든 한글 범위
            chosung_ranges = {
                'ㄱ': ('가', '깋'),
                'ㄴ': ('나', '닣'),
                'ㄷ': ('다', '딯'),
                'ㄹ': ('라', '맇'),
                'ㅁ': ('마', '밓'),
                'ㅂ': ('바', '빟'),
                'ㅅ': ('사', '싷'),
                'ㅇ': ('아', '잏'),
                'ㅈ': ('자', '짛'),
                'ㅊ': ('차', '칳'),
                'ㅋ': ('카', '킿'),
                'ㅌ': ('타', '팋'),
                'ㅍ': ('파', '핗'),
                'ㅎ': ('하', '힣')
            }

            if params['titleIndex'] in chosung_ranges:
                start_char, end_char = chosung_ranges[params['titleIndex']]
                query += " AND m.title_ko >= %s AND m.title_ko < %s"
                query_params.extend([start_char, chr(ord(end_char) + 1)])
        else:
            # 알파벳인 경우
            query += " AND (m.title_ko LIKE %s OR m.title_en LIKE %s)"
            index_term = f"{params['titleIndex']}%"
            query_params.extend([index_term, index_term])

    # GROUP BY 추가
    query += " GROUP BY m.movie_id"

    # 정렬
    query += " ORDER BY m.production_year DESC, m.title_ko"

    # 페이지네이션
    page = int(params.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"

    try:
        cursor.execute(query, query_params)
        results = cursor.fetchall()

        # 전체 개수 구하기 (수정된 쿼리)
        count_query = """
            SELECT COUNT(DISTINCT m.movie_id) as total
            FROM movies m
            LEFT JOIN directors d ON m.director_id = d.director_id
            LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
            LEFT JOIN genres g ON mg.genre_id = g.genre_id
            LEFT JOIN movie_countries mc ON m.movie_id = mc.movie_id
            LEFT JOIN countries c ON mc.country_id = c.country_id
            WHERE 1=1
        """

        # 동일한 조건 적용
        count_params = []

        if params.get('movieTitle'):
            count_query += " AND (m.title_ko LIKE %s OR m.title_en LIKE %s)"
            search_term = f"%{params['movieTitle']}%"
            count_params.extend([search_term, search_term])

        if params.get('directorName'):
            count_query += " AND d.name LIKE %s"
            count_params.append(f"%{params['directorName']}%")

        if params.get('yearFrom') and params['yearFrom'] != '--전체--':
            count_query += " AND m.production_year >= %s"
            count_params.append(int(params['yearFrom']))

        if params.get('yearTo') and params['yearTo'] != '--전체--':
            count_query += " AND m.production_year <= %s"
            count_params.append(int(params['yearTo']))

        if params.get('productionStatus') and len(params.get('productionStatus', [])) > 0:
            placeholders = ', '.join(['%s'] * len(params['productionStatus']))
            count_query += f" AND m.production_status IN ({placeholders})"
            count_params.extend(params['productionStatus'])

        if params.get('movieType') and len(params.get('movieType', [])) > 0:
            placeholders = ', '.join(['%s'] * len(params['movieType']))
            count_query += f" AND m.type IN ({placeholders})"
            count_params.extend(params['movieType'])

        if params.get('genre') and len(params.get('genre', [])) > 0:
            genre_conditions = []
            for _ in params['genre']:
                genre_conditions.append("EXISTS (SELECT 1 FROM movie_genres mg2 JOIN genres g2 ON mg2.genre_id = g2.genre_id WHERE mg2.movie_id = m.movie_id AND g2.name = %s)")
            count_query += f" AND ({' OR '.join(genre_conditions)})"
            count_params.extend(params['genre'])

        if params.get('country') and len(params.get('country', [])) > 0:
            country_conditions = []
            for _ in params['country']:
                country_conditions.append("EXISTS (SELECT 1 FROM movie_countries mc2 JOIN countries c2 ON mc2.country_id = c2.country_id WHERE mc2.movie_id = m.movie_id AND c2.name = %s)")
            count_query += f" AND ({' OR '.join(country_conditions)})"
            count_params.extend(params['country'])

        if params.get('titleIndex'):
            # 한글 자음인 경우
            if params['titleIndex'] in ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']:
                chosung_ranges = {
                    'ㄱ': ('가', '깋'),
                    'ㄴ': ('나', '닣'),
                    'ㄷ': ('다', '딯'),
                    'ㄹ': ('라', '맇'),
                    'ㅁ': ('마', '밓'),
                    'ㅂ': ('바', '빟'),
                    'ㅅ': ('사', '싷'),
                    'ㅇ': ('아', '잏'),
                    'ㅈ': ('자', '짛'),
                    'ㅊ': ('차', '칳'),
                    'ㅋ': ('카', '킿'),
                    'ㅌ': ('타', '팋'),
                    'ㅍ': ('파', '핗'),
                    'ㅎ': ('하', '힣')
                }

                if params['titleIndex'] in chosung_ranges:
                    start_char, end_char = chosung_ranges[params['titleIndex']]
                    count_query += " AND m.title_ko >= %s AND m.title_ko < %s"
                    count_params.extend([start_char, chr(ord(end_char) + 1)])
            else:
                # 알파벳인 경우
                count_query += " AND (m.title_ko LIKE %s OR m.title_en LIKE %s)"
                index_term = f"{params['titleIndex']}%"
                count_params.extend([index_term, index_term])

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']

        return {
            'results': results,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        }

    except Error as e:
        print(f"검색 오류: {e}")
        return {'results': [], 'total': 0, 'page': 1, 'per_page': 20, 'total_pages': 0}
    finally:
        cursor.close()
        connection.close()

# HTML 템플릿
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>영화 검색 시스템</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1 {
            margin-bottom: 30px;
            color: #2c3e50;
        }
        
        .search-form {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .form-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .form-group {
            display: flex;
            align-items: center;
        }
        
        .form-group label {
            width: 100px;
            font-weight: 500;
            color: #555;
        }
        
        .form-group input,
        .form-group select {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #4A90E2;
        }
        
        .year-group, .date-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .year-group select {
            flex: 1;
        }
        
        .more-options-toggle {
            text-align: center;
            margin: 20px 0;
        }
        
        .more-options-btn {
            background: none;
            border: none;
            color: #4A90E2;
            cursor: pointer;
            font-size: 14px;
            padding: 5px 15px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        .more-options-btn:hover {
            text-decoration: underline;
        }
        
        .arrow {
            font-size: 12px;
            transition: transform 0.3s;
        }
        
        .arrow.up {
            transform: rotate(180deg);
        }
        
        .more-options {
            display: none;
            border-top: 1px solid #e0e0e0;
            padding-top: 20px;
            margin-top: 20px;
        }
        
        .more-options.show {
            display: block;
        }
        
        .index-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 10px;
        }
        
        .index-btn {
            padding: 5px 10px;
            border: 1px solid #ddd;
            background: white;
            cursor: pointer;
            font-size: 14px;
            border-radius: 3px;
            transition: all 0.3s;
        }
        
        .index-btn:hover {
            background-color: #f0f0f0;
            border-color: #4A90E2;
        }
        
        .index-btn.active {
            background-color: #4A90E2;
            color: white;
            border-color: #4A90E2;
        }
        
        .button-group {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 20px;
        }
        
        .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background-color: #4A90E2;
            color: white;
        }
        
        .btn-primary:hover {
            background-color: #357ABD;
        }
        
        .btn-secondary {
            background-color: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background-color: #5a6268;
        }
        
        .results {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .results-header {
            padding: 15px 20px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            font-size: 14px;
            color: #666;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background-color: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
            font-size: 14px;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
            font-size: 14px;
        }
        
        tbody tr:hover {
            background-color: #f8f9fa;
        }
        
        .text-center {
            text-align: center;
        }
        
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 5px;
            padding: 20px;
        }
        
        .page-btn {
            padding: 6px 12px;
            border: 1px solid #ddd;
            background: white;
            color: #333;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .page-btn:hover {
            background-color: #f8f9fa;
            border-color: #4A90E2;
        }
        
        .page-btn.active {
            background-color: #4A90E2;
            color: white;
            border-color: #4A90E2;
        }
        
        .page-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #666;
        }
        
        .stats {
            background: #e3f2fd;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .stat-item {
            color: #1976d2;
        }
        
        .stat-item strong {
            color: #0d47a1;
        }
        
        .filter-input {
            cursor: pointer !important;
            background-color: white !important;
            color: #333;
        }
        
        .filter-input:hover {
            background-color: #f8f9fa !important;
        }
        
        .filter-input:focus {
            outline: none;
            border-color: #4A90E2;
            background-color: #f8f9fa !important;
        }
        
        /* ---------- modal 기본 레이아웃 ---------- */
        .modal-overlay {
            position: fixed;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            backdrop-filter: blur(2px);
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        }
        
        .modal-overlay.show {
            opacity: 1;
            visibility: visible;
        }
        
        .modal-container {
            width: 600px;
            max-height: 80vh;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            position: relative;
            display: flex;
            flex-direction: column;
            transform: scale(0.9);
            transition: transform 0.3s ease;
        }
        
        .modal-overlay.show .modal-container {
            transform: scale(1);
        }        
        
        /* 헤더 · 닫기버튼 등 디테일 */
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 24px;
            border-bottom: 1px solid #f0f0f0;
            background-color: #fafafa;
            border-radius: 12px 12px 0 0;
        }
        
        .modal-header h3 {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
            margin: 0;
        }        
        
        .modal-close {
            background: none;
            border: none;
            font-size: 28px;
            cursor: pointer;
            line-height: 1;
            color: #666;
            transition: color 0.2s;
            padding: 0;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
        }
        
        .modal-close:hover {
            background-color: #f0f0f0;
            color: #333;
        }
        
        .modal-body {
            padding: 0;
            overflow-y: auto;
            flex: 1;
        }
        
        /* 검색바 스타일 */
        .modal-search-bar {
            padding: 16px 24px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .modal-search-bar label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #495057;
            cursor: pointer;
            font-weight: 500;
        }
        
        .modal-search-bar input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        .modal-btn-confirm {
            margin-left: auto;
            padding: 8px 20px;
            background-color: #4A90E2;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        .modal-btn-confirm:hover {
            background-color: #357ABD;
        }
        
        /* 컨텐츠 영역 */
        .modal-content {
            padding: 20px 24px;
        }
        
        /* 대륙별 제목 */
        .modal-subtitle {
            font-size: 15px;
            font-weight: 600;
            color: #495057;
            margin-bottom: 12px;
            padding: 8px 0;
            border-bottom: 2px solid #e9ecef;
        }
        
        .modal-subtitle:not(:first-child) {
            margin-top: 24px;
        }
        
        
        /* 체크박스 그리드(2열‧3열) */
        .modal-checkbox-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0;
        }
        .country-modal-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0;
            margin-bottom: 20px;
        }
        
        .modal-checkbox-item {
            padding: 12px 16px;
            border-bottom: 1px solid #f0f0f0;
            border-right: 1px solid #f0f0f0;
            transition: background-color 0.2s;
        }
        
        .modal-checkbox-item:hover {
            background-color: #f8f9fa;
        }
        
        /* 마지막 행의 border-bottom 제거 */
        .modal-checkbox-grid .modal-checkbox-item:nth-last-child(-n+2) {
            border-bottom: none;
        }
        
        .country-modal-grid .modal-checkbox-item:nth-last-child(-n+3) {
            border-bottom: none;
        }
        
        /* 우측 border 제거 */
        .modal-checkbox-grid .modal-checkbox-item:nth-child(2n) {
            border-right: none;
        }
        
        .country-modal-grid .modal-checkbox-item:nth-child(3n) {
            border-right: none;
        }
        
        .modal-checkbox-item label {
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            font-size: 14px;
            color: #495057;
            margin: 0;
        }
        
        .modal-checkbox-item input[type="checkbox"] {
            width: 16px;
            height: 16px;
            cursor: pointer;
            flex-shrink: 0;
        }
        
        /* 체크박스 스타일 개선 */
        input[type="checkbox"] {
            accent-color: #4A90E2;
        }

        @media (max-width: 768px) {
            .modal-container {
                width: 95%;
                max-height: 95vh;
            }
            
            .country-modal-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
        
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 영화 검색 시스템</h1>
        
        <div class="stats" id="stats">
            <div class="stat-item">총 영화 수: <strong id="totalMovies">-</strong>개</div>
        </div>
        
        <div class="search-form">
            <div class="form-grid">
                <div class="form-group">
                    <label>• 영화명</label>
                    <input type="text" id="movieTitle" placeholder="영화명을 입력하세요">
                </div>
                
                <div class="form-group">
                    <label>• 감독명</label>
                    <input type="text" id="directorName" placeholder="감독명을 입력하세요">
                </div>
                
                <div class="form-group">
                    <label>• 제작연도</label>
                    <div class="year-group">
                        <select id="yearFrom">
                            <option value="--전체--">--전체--</option>
                        </select>
                        <span>~</span>
                        <select id="yearTo">
                            <option value="--전체--">--전체--</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <!-- 더보기 버튼 -->
            <div class="more-options-toggle">
                <button class="more-options-btn" onclick="toggleMoreOptions()">
                    더보기 <span class="arrow" id="arrow">▼</span>
                </button>
            </div>
            
            <!-- 추가 검색 옵션 -->
            <div class="more-options" id="moreOptions">
                <div class="form-grid">
                    <div class="form-group">
                        <label>• 제작상태</label>
                        <input type="text" id="productionStatus" readonly 
                               placeholder="전체" 
                               onclick="openModal('productionStatus')"
                               class="filter-input">
                    </div>
                    
                    <div class="form-group">
                        <label>• 유형</label>
                        <input type="text" id="movieType" readonly 
                               placeholder="전체" 
                               onclick="openModal('movieType')"
                               class="filter-input">
                    </div>
                    
                    <div class="form-group">
                        <label>• 장르별</label>
                        <input type="text" id="genre" readonly 
                               placeholder="전체" 
                               onclick="openModal('genre')"
                               class="filter-input">
                    </div>
                    
                    <div class="form-group">
                        <label>• 국적별</label>
                        <input type="text" id="country" readonly 
                               placeholder="전체" 
                               onclick="openModal('country')"
                               class="filter-input">
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <label style="font-weight: 500; color: #555;">• 영화명 인덱싱</label>
                    <div class="index-buttons">
                        <button class="index-btn" onclick="setTitleIndex('ㄱ')">ㄱ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㄴ')">ㄴ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㄷ')">ㄷ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㄹ')">ㄹ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅁ')">ㅁ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅂ')">ㅂ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅅ')">ㅅ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅇ')">ㅇ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅈ')">ㅈ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅊ')">ㅊ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅋ')">ㅋ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅌ')">ㅌ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅍ')">ㅍ</button>
                        <button class="index-btn" onclick="setTitleIndex('ㅎ')">ㅎ</button>
                        <button class="index-btn" onclick="setTitleIndex('A')">A</button>
                        <button class="index-btn" onclick="setTitleIndex('B')">B</button>
                        <button class="index-btn" onclick="setTitleIndex('C')">C</button>
                        <button class="index-btn" onclick="setTitleIndex('D')">D</button>
                        <button class="index-btn" onclick="setTitleIndex('E')">E</button>
                        <button class="index-btn" onclick="setTitleIndex('F')">F</button>
                        <button class="index-btn" onclick="setTitleIndex('G')">G</button>
                        <button class="index-btn" onclick="setTitleIndex('H')">H</button>
                        <button class="index-btn" onclick="setTitleIndex('I')">I</button>
                        <button class="index-btn" onclick="setTitleIndex('J')">J</button>
                        <button class="index-btn" onclick="setTitleIndex('K')">K</button>
                        <button class="index-btn" onclick="setTitleIndex('L')">L</button>
                        <button class="index-btn" onclick="setTitleIndex('M')">M</button>
                        <button class="index-btn" onclick="setTitleIndex('N')">N</button>
                        <button class="index-btn" onclick="setTitleIndex('O')">O</button>
                        <button class="index-btn" onclick="setTitleIndex('P')">P</button>
                        <button class="index-btn" onclick="setTitleIndex('Q')">Q</button>
                        <button class="index-btn" onclick="setTitleIndex('R')">R</button>
                        <button class="index-btn" onclick="setTitleIndex('S')">S</button>
                        <button class="index-btn" onclick="setTitleIndex('T')">T</button>
                        <button class="index-btn" onclick="setTitleIndex('U')">U</button>
                        <button class="index-btn" onclick="setTitleIndex('V')">V</button>
                        <button class="index-btn" onclick="setTitleIndex('W')">W</button>
                        <button class="index-btn" onclick="setTitleIndex('X')">X</button>
                        <button class="index-btn" onclick="setTitleIndex('Y')">Y</button>
                        <button class="index-btn" onclick="setTitleIndex('Z')">Z</button>
                    </div>
                </div>
            </div>
            
            <div class="button-group">
                <button class="btn btn-primary" onclick="searchMovies()">🔍 조회</button>
                <button class="btn btn-secondary" onclick="resetForm()">↻ 초기화</button>
            </div>
        </div>
        
        <div id="resultsContainer"></div>
    </div>
    
    <!-- 모달 창 -->
    <div id="modalOverlay" class="modal-overlay" onclick="closeModalOverlay(event)">
        <div class="modal-container">
            <div class="modal-header">
                <h3 id="modalTitle">코드 검색결과</h3>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body">
                <div class="modal-search-bar">
                    <input type="checkbox" id="modalSelectAll" onchange="toggleAllModalCheckboxes()">
                    <label for="modalSelectAll">전체 선택</label>
                    <button class="modal-btn-confirm" onclick="confirmSelection()">확인</button>
                </div>
                <div class="modal-content" id="modalContent">
                    <!-- 동적으로 생성됨 -->
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentTitleIndex = '';
        
        // 페이지 로드 시 초기화
        window.onload = function() {
            initYearSelects();
            loadStats();
            loadFilterOptions();
        };
        
        // 연도 선택 옵션 초기화
        function initYearSelects() {
            const yearFrom = document.getElementById('yearFrom');
            const yearTo = document.getElementById('yearTo');
            
            for (let year = 2025; year >= 1925; year--) {
                const option1 = new Option(year, year);
                const option2 = new Option(year, year);
                yearFrom.add(option1);
                yearTo.add(option2);
            }
        }
        
        let currentModalType = '';
        let selectedValues = {
            productionStatus: [],
            movieType: [],
            genre: [],
            country: []
        };
        
        // 필터 옵션 로드
        function loadFilterOptions() {
            fetch('/api/filter-options')
                .then(response => response.json())
                .then(data => {
                    window.filterOptions = data;
                })
                .catch(error => {
                    console.error('필터 옵션 로드 실패:', error);
                });
        }
        
        // 모달 열기
        function openModal(type) {
            currentModalType = type;
            const modal = document.getElementById('modalOverlay');
            const modalContainer = modal.querySelector('.modal-container');
            const modalTitle = document.getElementById('modalTitle');
            const modalContent = document.getElementById('modalContent');
            
            // 제목 설정
            modalTitle.textContent = '코드 검색결과';
            
            // 국가 선택일 경우 모달 크기 확대
            if (type === 'country') {
                modalContainer.style.maxWidth = '800px';
            } else {
                modalContainer.style.maxWidth = '600px';
            }
            
            // 내용 생성
            modalContent.innerHTML = '';
            
            if (type === 'country') {
                // 국가는 대륙별로 표시
                for (const [continent, countries] of Object.entries(window.filterOptions.countries_by_continent || {})) {
                    if (countries.length > 0) {
                        const gridHtml = countries.map((country, index) => {
                            const isLastRow = index >= countries.length - (countries.length % 3 || 3);
                            return `
                                <div class="modal-checkbox-item" style="${isLastRow ? 'border-bottom: none;' : ''}">
                                    <label>
                                        <input type="checkbox" name="${type}" value="${country}" 
                                            ${selectedValues[type].includes(country) ? 'checked' : ''}>
                                        ${country}
                                    </label>
                                </div>
                            `;
                        }).join('');
                        
                        modalContent.innerHTML += `
                            <div class="modal-subtitle">${continent}</div>
                            <div class="country-modal-grid">
                                ${gridHtml}
                            </div>
                        `;
                    }
                }
            } else {
                // 나머지는 2열 그리드로 표시
                const items = window.filterOptions[type === 'productionStatus' ? 'production_status' : 
                             type === 'movieType' ? 'types' : 
                             type === 'genre' ? 'genres' : ''] || [];
                
                const gridHtml = items.map((item, index) => {
                    const isLastRow = index >= items.length - (items.length % 2 || 2);
                    return `
                        <div class="modal-checkbox-item" style="${isLastRow ? 'border-bottom: none;' : ''}">
                            <label>
                                <input type="checkbox" name="${type}" value="${item}" 
                                    ${selectedValues[type].includes(item) ? 'checked' : ''}>
                                ${item}
                            </label>
                        </div>
                    `;
                }).join('');
                
                modalContent.innerHTML = `
                    <div class="modal-checkbox-grid">
                        ${gridHtml}
                    </div>
                `;
            }
            
            // 전체 선택 체크박스 상태 업데이트
            updateSelectAllCheckbox();
            
            // 모달 표시
            modal.classList.add('show');
        }
        
        // 모달 닫기
        function closeModal() {
            document.getElementById('modalOverlay').classList.remove('show');
        }
        
        // 모달 오버레이 클릭 시 닫기
        function closeModalOverlay(event) {
            if (event.target === event.currentTarget) {
                closeModal();
            }
        }
        
        // 전체 선택/해제
        function toggleAllModalCheckboxes() {
            const selectAll = document.getElementById('modalSelectAll');
            const checkboxes = document.querySelectorAll(`#modalContent input[name="${currentModalType}"]`);
            
            checkboxes.forEach(cb => {
                cb.checked = selectAll.checked;
            });
        }
        
        // 전체 선택 체크박스 상태 업데이트
        function updateSelectAllCheckbox() {
            const checkboxes = document.querySelectorAll(`#modalContent input[name="${currentModalType}"]`);
            const selectAll = document.getElementById('modalSelectAll');
            const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
            
            selectAll.checked = checkedCount === checkboxes.length && checkboxes.length > 0;
            selectAll.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
        }
        
        // 선택 확인
        function confirmSelection() {
            const checkboxes = document.querySelectorAll(`#modalContent input[name="${currentModalType}"]:checked`);
            selectedValues[currentModalType] = Array.from(checkboxes).map(cb => cb.value);
            
            // 입력 필드 업데이트
            const input = document.getElementById(currentModalType);
            if (selectedValues[currentModalType].length === 0) {
                input.value = '';
                input.placeholder = '전체';
            } else {
                input.value = selectedValues[currentModalType].join(', ');
            }
            
            closeModal();
        }
        
        // 개별 체크박스 변경 시
        document.addEventListener('change', function(e) {
            if (e.target.type === 'checkbox' && e.target.name && e.target !== document.getElementById('modalSelectAll')) {
                updateSelectAllCheckbox();
            }
        });
        
        // 더보기 토글
        function toggleMoreOptions() {
            const moreOptions = document.getElementById('moreOptions');
            const arrow = document.getElementById('arrow');
            
            if (moreOptions.classList.contains('show')) {
                moreOptions.classList.remove('show');
                arrow.classList.remove('up');
            } else {
                moreOptions.classList.add('show');
                arrow.classList.add('up');
            }
        }
        
        // 영화명 인덱싱 설정 (토글 기능)
        function setTitleIndex(index) {
            // 이미 선택된 인덱스를 다시 클릭하면 취소
            if (currentTitleIndex === index) {
                currentTitleIndex = '';
                event.target.classList.remove('active');
            } else {
                // 새로운 인덱스 선택
                currentTitleIndex = index;
                
                // 모든 버튼의 active 클래스 제거
                document.querySelectorAll('.index-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // 클릭된 버튼에 active 클래스 추가
                event.target.classList.add('active');
            }
        }
        
        // 통계 로드
        function loadStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('totalMovies').textContent = data.total_movies ? data.total_movies.toLocaleString() : '0';
                })
                .catch(error => {
                    console.error('통계 로드 실패:', error);
                });
        }
        
        // 영화 검색
        function searchMovies(page = 1) {
            const params = {
                movieTitle: document.getElementById('movieTitle').value,
                directorName: document.getElementById('directorName').value,
                yearFrom: document.getElementById('yearFrom').value,
                yearTo: document.getElementById('yearTo').value,
                productionStatus: selectedValues.productionStatus,
                movieType: selectedValues.movieType,
                genre: selectedValues.genre,
                country: selectedValues.country,
                titleIndex: currentTitleIndex,
                page: page
            };
            
            const resultsContainer = document.getElementById('resultsContainer');
            resultsContainer.innerHTML = '<div class="loading">검색 중...</div>';
            
            fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(params)
            })
            .then(response => response.json())
            .then(data => {
                displayResults(data);
            })
            .catch(error => {
                resultsContainer.innerHTML = '<div class="loading">❌ 오류가 발생했습니다.</div>';
                console.error('Error:', error);
            });
        }
        
        // 검색 결과 표시
        function displayResults(data) {
            const resultsContainer = document.getElementById('resultsContainer');
            
            if (!data.results || data.results.length === 0) {
                resultsContainer.innerHTML = '<div class="loading">검색 결과가 없습니다.</div>';
                return;
            }
            
            let html = `
                <div class="results">
                    <div class="results-header">
                        총 ${data.total.toLocaleString()}개의 영화가 검색되었습니다. 
                        (${data.page}/${data.total_pages} 페이지)
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th class="text-center">번호</th>
                                <th>영화명</th>
                                <th>영화명(영문)</th>
                                <th class="text-center">제작연도</th>
                                <th>제작국가</th>
                                <th>유형</th>
                                <th>장르</th>
                                <th>감독</th>
                                <th>제작사</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            data.results.forEach((movie, index) => {
                const rowNumber = (data.page - 1) * data.per_page + index + 1;
                html += `
                    <tr>
                        <td class="text-center">${rowNumber}</td>
                        <td>${movie.title_ko || ''}</td>
                        <td>${movie.title_en || ''}</td>
                        <td class="text-center">${movie.production_year || ''}</td>
                        <td>${movie.countries || ''}</td>
                        <td>${movie.type || ''}</td>
                        <td>${movie.genres || ''}</td>
                        <td>${movie.director_name || ''}</td>
                        <td>${movie.company_name || ''}</td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                    ${generatePagination(data)}
                </div>
            `;
            
            resultsContainer.innerHTML = html;
        }
        
        // 페이지네이션 생성
        function generatePagination(data) {
            if (data.total_pages <= 1) return '';
            
            let html = '<div class="pagination">';
            
            // 이전 버튼
            if (data.page > 1) {
                html += `<button class="page-btn" onclick="searchMovies(${data.page - 1})">이전</button>`;
            } else {
                html += `<button class="page-btn" disabled>이전</button>`;
            }
            
            // 페이지 번호
            let startPage = Math.max(1, data.page - 5);
            let endPage = Math.min(data.total_pages, startPage + 9);
            
            if (startPage > 1) {
                html += `<button class="page-btn" onclick="searchMovies(1)">1</button>`;
                if (startPage > 2) html += `<span>...</span>`;
            }
            
            for (let i = startPage; i <= endPage; i++) {
                if (i === data.page) {
                    html += `<button class="page-btn active">${i}</button>`;
                } else {
                    html += `<button class="page-btn" onclick="searchMovies(${i})">${i}</button>`;
                }
            }
            
            if (endPage < data.total_pages) {
                if (endPage < data.total_pages - 1) html += `<span>...</span>`;
                html += `<button class="page-btn" onclick="searchMovies(${data.total_pages})">${data.total_pages}</button>`;
            }
            
            // 다음 버튼
            if (data.page < data.total_pages) {
                html += `<button class="page-btn" onclick="searchMovies(${data.page + 1})">다음</button>`;
            } else {
                html += `<button class="page-btn" disabled>다음</button>`;
            }
            
            html += '</div>';
            return html;
        }
        
        // 폼 초기화
        function resetForm() {
            document.getElementById('movieTitle').value = '';
            document.getElementById('directorName').value = '';
            document.getElementById('yearFrom').value = '--전체--';
            document.getElementById('yearTo').value = '--전체--';
            
            // 선택값 초기화
            selectedValues = {
                productionStatus: [],
                movieType: [],
                genre: [],
                country: []
            };
            
            // 입력 필드 초기화
            document.getElementById('productionStatus').value = '';
            document.getElementById('productionStatus').placeholder = '전체';
            document.getElementById('movieType').value = '';
            document.getElementById('movieType').placeholder = '전체';
            document.getElementById('genre').value = '';
            document.getElementById('genre').placeholder = '전체';
            document.getElementById('country').value = '';
            document.getElementById('country').placeholder = '전체';
            
            currentTitleIndex = '';
            document.querySelectorAll('.index-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            document.getElementById('resultsContainer').innerHTML = '';
            
            // 더보기 섹션 닫기
            const moreOptions = document.getElementById('moreOptions');
            const arrow = document.getElementById('arrow');
            moreOptions.classList.remove('show');
            arrow.classList.remove('up');
        }
        
        // Enter 키로 검색, ESC 키로 모달 닫기
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !document.getElementById('modalOverlay').classList.contains('show')) {
                searchMovies();
            } else if (e.key === 'Escape' && document.getElementById('modalOverlay').classList.contains('show')) {
                closeModal();
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """메인 페이지"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/search', methods=['POST'])
def search():
    """검색 API"""
    params = request.get_json()
    results = search_movies(params)
    return jsonify(results)

@app.route('/api/stats')
def stats():
    """통계 API"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'})

    cursor = connection.cursor(dictionary=True)

    try:
        # 전체 영화 수
        cursor.execute("SELECT COUNT(*) as count FROM movies")
        total_movies = cursor.fetchone()['count']

        # 전체 감독 수
        cursor.execute("SELECT COUNT(*) as count FROM directors")
        total_directors = cursor.fetchone()['count']

        # 전체 장르 수
        cursor.execute("SELECT COUNT(*) as count FROM genres")
        total_genres = cursor.fetchone()['count']

        return jsonify({
            'total_movies': total_movies,
            'total_directors': total_directors,
            'total_genres': total_genres
        })
    except Error as e:
        return jsonify({'error': str(e)})
    finally:
        cursor.close()
        connection.close()

@app.route('/api/filter-options')
def filter_options():
    """필터 옵션 API"""
    options = get_filter_options()
    return jsonify(options)

if __name__ == '__main__':
    print("=" * 50)
    print("🎬 영화 검색 시스템 시작!")
    print("=" * 50)
    print("웹 브라우저에서 http://localhost:5000 으로 접속하세요.")
    print("종료하려면 Ctrl+C를 누르세요.")
    print("=" * 50)

    # Flask 앱 실행
    app.run(debug=True, host='0.0.0.0', port=5000)