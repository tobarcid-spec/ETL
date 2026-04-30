
# detalle tablas vinculada a 13 go  
# 13go_senales_live= guarda  estrucutura de las señales en vivo que estan en 13go
# 13go_programas_vod= guarda los programas en VOD que estan en 13go 


#query para saber que hay en el aire hoy con restriccion y sin ella
SELECT 
    id_original, 
    titulo, 
    CASE 
        WHEN restriction = '1' THEN 'Cerrado'
        WHEN restriction = '0' THEN 'Abierta'
        ELSE 'Sin definir' 
    END AS estado_restriccion,
       fecha_inicio
FROM 13go_senales_live 
WHERE fecha_fin IS NULL 
ORDER BY titulo ASC;

#query Ver el historial de cambios de una señal específica
SELECT titulo, imagen_url, fecha_inicio, fecha_fin 
FROM 13go_senales_live 
WHERE id_original = '13live' 
ORDER BY fecha_inicio DESC;

#query para buscar fecha especifica de la señales
SELECT * FROM 13go_senales_live 
WHERE  '2026-03-01 12:00:00' BETWEEN fecha_inicio AND COALESCE(fecha_fin, NOW());

#Query "Maestra" de Auditoría
SELECT 
    'Señales Live' AS tipo,
    COUNT(CASE WHEN fecha_fin IS NULL THEN 1 END) AS activos,
    COUNT(CASE WHEN fecha_fin IS NOT NULL THEN 1 END) AS historicos
FROM 13go_senales_live
UNION
SELECT 
    'Programas VOD' AS tipo,
    COUNT(CASE WHEN fecha_fin IS NULL THEN 1 END) AS activos,
    COUNT(CASE WHEN fecha_fin IS NOT NULL THEN 1 END) AS historicos
FROM 13go_programas_vod
UNION
SELECT 
    'Capítulos VOD' AS tipo,
    COUNT(CASE WHEN fecha_fin IS NULL THEN 1 END) AS activos,
    COUNT(CASE WHEN fecha_fin IS NOT NULL THEN 1 END) AS historicos
FROM 13go_capitulos_vod;

select * from 13go_programas_vod where fecha_fin is not  null;
select * from 13go_capitulos_vod where fecha_fin is not  null;

