SELECT 
    MONTH(m.fecha_consulta) AS mes_numero,
    CASE MONTH(m.fecha_consulta)
        WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo' 
        WHEN 4 THEN 'Abril' WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre' 
        WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' WHEN 12 THEN 'Diciembre'
    END AS mes_nombre,
    SUM(m.plays) AS total_plays,
    -- 1. Cálculo de total de minutos (tu lógica original)
    ROUND(SUM(
        COALESCE(CAST(NULLIF(REGEXP_SUBSTR(m.time_total, '[0-9]+(?= m)'), '') AS UNSIGNED), 0) * 2592000 +
        COALESCE(CAST(NULLIF(REGEXP_SUBSTR(m.time_total, '[0-9]+(?= d)'), '') AS UNSIGNED), 0) * 86400 +
        COALESCE(CAST(SUBSTRING_INDEX(REGEXP_SUBSTR(m.time_total, '[0-9]{1,2}:[0-9]{2}:[0-9]{2}'), ':', 1) AS UNSIGNED), 0) * 3600 +
        COALESCE(CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(REGEXP_SUBSTR(m.time_total, '[0-9]{1,2}:[0-9]{2}:[0-9]{2}'), ':', 2), ':', -1) AS UNSIGNED), 0) * 60 +
        COALESCE(CAST(SUBSTRING_INDEX(REGEXP_SUBSTR(m.time_total, '[0-9]{1,2}:[0-9]{2}:[0-9]{2}'), ':', -1) AS UNSIGNED), 0)
    ) / 60, 2) AS total_minutos_mensuales,
    -- 2. Cálculo del promedio de minutos por vista
    ROUND(
        (SUM(
            COALESCE(CAST(NULLIF(REGEXP_SUBSTR(m.time_total, '[0-9]+(?= m)'), '') AS UNSIGNED), 0) * 2592000 +
            COALESCE(CAST(NULLIF(REGEXP_SUBSTR(m.time_total, '[0-9]+(?= d)'), '') AS UNSIGNED), 0) * 86400 +
            COALESCE(CAST(SUBSTRING_INDEX(REGEXP_SUBSTR(m.time_total, '[0-9]{1,2}:[0-9]{2}:[0-9]{2}'), ':', 1) AS UNSIGNED), 0) * 3600 +
            COALESCE(CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(REGEXP_SUBSTR(m.time_total, '[0-9]{1,2}:[0-9]{2}:[0-9]{2}'), ':', 2), ':', -1) AS UNSIGNED), 0) * 60 +
            COALESCE(CAST(SUBSTRING_INDEX(REGEXP_SUBSTR(m.time_total, '[0-9]{1,2}:[0-9]{2}:[0-9]{2}'), ':', -1) AS UNSIGNED), 0)
        ) / 60) 
        / NULLIF(SUM(m.plays), 0) -- Evita división por cero
    , 2) AS promedio_minutos_por_play
FROM 
    T13_metricas_video AS m
WHERE 
    m.fecha_consulta BETWEEN '2026-01-01' AND '2026-03-31'
GROUP BY 
    MONTH(m.fecha_consulta),
    mes_nombre 
ORDER BY 
    mes_numero ASC;