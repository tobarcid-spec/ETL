SELECT * from fb_video WHERE ETIQUETA='OBRERO';
SELECT * FROM c13_yt_metricas WHERE ETIQUETA='OBRERO';
SELECT * from tiktok_playlist_stats where playlist_name like '%OBRERO%'

-- 13GO
SELECT 
    v.video_key, 
    v.titulo, -- Asumiendo que existe un campo de nombre/título en la maestra
    SUM(m.plays) AS total_plays
FROM 
    c13_videos_rudo AS v
JOIN 
    c13_metricas_video AS m ON v.video_key = m.video_id
WHERE 
    m.fecha_consulta >= '2025-10-01' AND m.fecha_consulta <= '2026-03-10'
    and nombre_carpeta='EL OBRERO QUE ME ENAMORO'
GROUP BY 
    v.video_key, 
    v.titulo
ORDER BY 
    total_plays DESC