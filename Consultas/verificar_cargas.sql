INSERT INTO RRSS_diarias (alcance_face,clics_face,fecha) VALUES ( 2589113, 46809,'2026-02-05');
INSERT INTO RRSS_diarias (alcance_face,clics_face,fecha) VALUES (  2044213,52959,'2026-01-31');
INSERT INTO RRSS_diarias (alcance_face,clics_face,fecha) VALUES (  2322341,61746,'2026-02-01');


#verificar carga de datos automaticos
#esta bien que lo de mango sea del dia anterior

SELECT 'C13 Articulos(notas)' AS tabla, COUNT(*), DATE(fecha) AS dia
FROM c13_articulos 
WHERE DATE(fecha) = (SELECT MAX(DATE(fecha)) FROM c13_articulos)
GROUP BY dia

UNION ALL

SELECT ' C13 Live Video (mango vivo)', COUNT(*), DATE(fecha_consulta)
FROM c13_live_video 
WHERE DATE(fecha_consulta) = (SELECT MAX(DATE(fecha_consulta)) FROM c13_live_video)
GROUP BY DATE(fecha_consulta)

UNION ALL

SELECT 'C13 Métricas (notas GA4)', COUNT(*), DATE(fecha_hora_actualizacion)
FROM c13_metricas 
WHERE DATE(fecha_hora_actualizacion) = (SELECT MAX(DATE(fecha_hora_actualizacion)) FROM c13_metricas)
GROUP BY DATE(fecha_hora_actualizacion)

UNION ALL

SELECT 'C13 Métricas Video (mango vod)', COUNT(*), DATE(fecha_consulta)
FROM c13_metricas_video 
WHERE DATE(fecha_consulta) = (SELECT MAX(DATE(fecha_consulta)) FROM c13_metricas_video)
GROUP BY DATE(fecha_consulta)

UNION ALL

SELECT 'C13 Videos Rudo (rudo vod)', COUNT(*), DATE(fecha)
FROM c13_videos_rudo 
WHERE DATE(fecha) = (SELECT MAX(DATE(fecha)) FROM c13_videos_rudo)
GROUP BY DATE(fecha)

UNION ALL

SELECT 'T13 Videos Rudo (rudovod)', COUNT(*), DATE(fecha)
FROM T13_videos_rudo 
WHERE DATE(fecha) = (SELECT MAX(DATE(fecha)) FROM T13_videos_rudo)
GROUP BY DATE(fecha)

UNION ALL

SELECT 'T13 Métricas Video (mango vod)', COUNT(*), DATE(fecha_consulta)
FROM T13_metricas_video 
WHERE DATE(fecha_consulta) = (SELECT MAX(DATE(fecha_consulta)) FROM T13_metricas_video)
GROUP BY DATE(fecha_consulta)

UNION ALL

SELECT ' Fast Live Video (mango vivo)', COUNT(*), DATE(fecha_consulta)
FROM Fast_live_video 
WHERE DATE(fecha_consulta) = (SELECT MAX(DATE(fecha_consulta)) FROM Fast_live_video)
GROUP BY DATE(fecha_consulta)

UNION ALL

SELECT ' T13 Live Video (mango vivo) ', COUNT(*), DATE(fecha_consulta)
FROM T13_live_video 
WHERE DATE(fecha_consulta) = (SELECT MAX(DATE(fecha_consulta)) FROM T13_live_video)
GROUP BY DATE(fecha_consulta)

UNION ALL

SELECT 'T13 Articulos(notas)' AS tabla, COUNT(*), DATE(fecha) AS dia
FROM T13_articulos 
WHERE DATE(fecha) = (SELECT MAX(DATE(fecha)) FROM T13_articulos)
GROUP BY dia

UNION ALL

SELECT 'T13 Métricas (notas GA4)', COUNT(*), DATE(fecha_hora_actualizacion)
FROM T13_metricas 
WHERE DATE(fecha_hora_actualizacion) = (SELECT MAX(DATE(fecha_hora_actualizacion)) FROM T13_metricas)
GROUP BY DATE(fecha_hora_actualizacion);


SELECT 
    canal, 
    MAX(fecha_consulta) AS max_fecha
FROM Fast_live_video
GROUP BY canal;
