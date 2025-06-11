-- KOBIS 영화 데이터베이스 스키마
CREATE DATABASE IF NOT EXISTS kobis_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE kobis_db;

-- 1. 감독 테이블
CREATE TABLE directors (
                           director_id INT AUTO_INCREMENT PRIMARY KEY,
                           name VARCHAR(255) NOT NULL,
                           UNIQUE KEY idx_director_name (name),
                           INDEX idx_director_search (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 제작사 테이블
CREATE TABLE production_companies (
                                      company_id INT AUTO_INCREMENT PRIMARY KEY,
                                      name VARCHAR(255) NOT NULL,
                                      UNIQUE KEY idx_company_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 장르 마스터 테이블
CREATE TABLE genres (
                        genre_id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        UNIQUE KEY idx_genre_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 국가 마스터 테이블
CREATE TABLE countries (
                           country_id INT AUTO_INCREMENT PRIMARY KEY,
                           name VARCHAR(100) NOT NULL,
                           UNIQUE KEY idx_country_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 영화 기본 정보 테이블
CREATE TABLE movies (
                        movie_id INT AUTO_INCREMENT PRIMARY KEY,
                        title_ko VARCHAR(500) NOT NULL,
                        title_en VARCHAR(500),
                        production_year INT,
                        type VARCHAR(50),
                        production_status VARCHAR(50),
                        director_id INT,
                        company_id INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        INDEX idx_title_ko (title_ko),
                        INDEX idx_title_en (title_en),
                        INDEX idx_production_year (production_year),

                        FOREIGN KEY (director_id) REFERENCES directors(director_id) ON DELETE SET NULL,
                        FOREIGN KEY (company_id) REFERENCES production_companies(company_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 영화-장르 다대다 관계 테이블
CREATE TABLE movie_genres (
                              movie_id INT NOT NULL,
                              genre_id INT NOT NULL,
                              PRIMARY KEY (movie_id, genre_id),
                              FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
                              FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE,
                              INDEX idx_genre_movie (genre_id, movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 영화-국가 다대다 관계 테이블
CREATE TABLE movie_countries (
                                 movie_id INT NOT NULL,
                                 country_id INT NOT NULL,
                                 PRIMARY KEY (movie_id, country_id),
                                 FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
                                 FOREIGN KEY (country_id) REFERENCES countries(country_id) ON DELETE CASCADE,
                                 INDEX idx_country_movie (country_id, movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 원본 데이터 테이블 (1단계용)
CREATE TABLE movie_info (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            title_ko VARCHAR(500),
                            title_en VARCHAR(500),
                            production_year VARCHAR(50),
                            production_countries VARCHAR(500),
                            type VARCHAR(50),
                            genres VARCHAR(500),
                            production_status VARCHAR(50),
                            director VARCHAR(255),
                            production_company VARCHAR(255),
                            sheet_source VARCHAR(50),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                            INDEX idx_raw_title (title_ko),
                            INDEX idx_raw_director (director),
                            INDEX idx_raw_year (production_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;