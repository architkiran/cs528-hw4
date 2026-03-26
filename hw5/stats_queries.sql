USE hw5;

-- 1. Successful vs unsuccessful requests
SELECT 'successful' as type, COUNT(*) as count FROM requests
UNION
SELECT 'unsuccessful', COUNT(*) FROM errors;

-- 2. Requests from banned countries
SELECT COUNT(*) as banned_requests FROM requests WHERE is_banned = 1;

-- 3. Male vs Female requests
SELECT gender, COUNT(*) as count FROM requests GROUP BY gender;

-- 4. Top 5 countries
SELECT country, COUNT(*) as count FROM requests 
GROUP BY country ORDER BY count DESC LIMIT 5;

-- 5. Age group with most requests
SELECT 
  CASE 
    WHEN age BETWEEN 18 AND 25 THEN '18-25'
    WHEN age BETWEEN 26 AND 35 THEN '26-35'
    WHEN age BETWEEN 36 AND 50 THEN '36-50'
    WHEN age BETWEEN 51 AND 65 THEN '51-65'
    ELSE '65+' 
  END as age_group,
  COUNT(*) as count
FROM requests GROUP BY age_group ORDER BY count DESC;

-- 6. Income group with most requests
SELECT income, COUNT(*) as count FROM requests 
GROUP BY income ORDER BY count DESC;
