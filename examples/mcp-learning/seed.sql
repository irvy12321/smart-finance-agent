CREATE DATABASE IF NOT EXISTS db_mcp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_mcp;

DROP TABLE IF EXISTS chinese_movie_ratings;
CREATE TABLE chinese_movie_ratings (
    id        INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    title     VARCHAR(128) NOT NULL          COMMENT '电影名称',
    year      INT                            COMMENT '上映年份',
    director  VARCHAR(64)                    COMMENT '导演',
    rating    DECIMAL(3,1)                   COMMENT '评分(0-10)',
    votes     INT                            COMMENT '评价人数'
) COMMENT='中国电影评分示例表';

INSERT INTO chinese_movie_ratings (title, year, director, rating, votes) VALUES
('霸王别姬',        1993, '陈凯歌',   9.6, 2100000),
('活着',            1994, '张艺谋',   9.3, 800000),
('大话西游之大圣娶亲', 1995, '刘镇伟', 9.2, 1500000),
('让子弹飞',        2010, '姜文',     9.0, 1700000),
('饮食男女',        1994, '李安',     9.1, 400000),
('鬼子来了',        2000, '姜文',     9.3, 600000),
('无间道',          2002, '刘伟强',   9.3, 1100000),
('阳光灿烂的日子',  1994, '姜文',     8.9, 500000),
('喜剧之王',        1999, '周星驰',   8.8, 900000),
('春光乍泄',        1997, '王家卫',   8.9, 450000),
('重庆森林',        1994, '王家卫',   8.8, 700000),
('卧虎藏龙',        2000, '李安',     8.6, 480000),
('一一',            2000, '杨德昌',   9.1, 220000),
('天下无贼',        2004, '冯小刚',   8.6, 650000),
('英雄',            2002, '张艺谋',   7.6, 520000),
('唐伯虎点秋香',    1993, '李力持',   8.6, 800000),
('功夫',            2004, '周星驰',   8.7, 1000000),
('国产凌凌漆',      1994, '周星驰',   8.6, 400000),
('甲方乙方',        1997, '冯小刚',   8.4, 300000),
('暴裂无声',        2017, '忻钰坤',   8.3, 350000),
('我不是药神',      2018, '文牧野',   9.0, 2200000),
('流浪地球',        2019, '郭帆',     7.9, 1500000),
('哪吒之魔童降世',  2019, '饺子',     8.4, 1900000),
('白日焰火',        2014, '刁亦男',   7.4, 300000),
('地久天长',        2019, '王小帅',   8.0, 120000);

ALTER USER 'root'@'localhost' IDENTIFIED BY 'root';
FLUSH PRIVILEGES;
