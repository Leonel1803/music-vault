# Requisitos y estado de cumplimiento

El estado describe lo que esta entrega proporciona en el código y la infraestructura versionados. “Pendiente” no equivale a satisfecho por documentación. Cada RF/RNF del [`AGENT.md`](../AGENT.md) aparece aquí para facilitar seguimiento.

## Requisitos funcionales

| ID | Requisito | Estado | Evidencia / trabajo restante |
|---|---|---|---|
| RF-01 | Registro | Parcial | Cognito User Pool y flujo Hosted UI previstos; validar el flujo desplegado por ambiente. |
| RF-02 | Login/logout | Parcial | Cliente Amplify inicia/cierra sesión; falta validar callback y configuración real de Cognito. |
| RF-03 | Identificación de sesión activa | Implementado en cliente | `AuthContext` deriva estado de la sesión Amplify. |
| RF-04 | Restringir endpoints privados | Implementado en diseño/API | JWT authorizer para rutas privadas; verificar después de aplicar Terraform. |
| RF-05 | Listar artistas | Implementado | Endpoint y pantalla en el frontend (ver `docs/api.md`). |
| RF-06 | Detalle de artista | Implementado | Endpoint y pantalla en el frontend (ver `docs/api.md`). |
| RF-07 | Listar álbumes | Implementado | Endpoint y pantalla en el frontend (ver `docs/api.md`). |
| RF-08 | Detalle de álbum | Implementado | Endpoint y pantalla en el frontend (ver `docs/api.md`). |
| RF-09 | Listar canciones | Implementado | `GET /songs`, paginación, género y búsqueda por prefijo. |
| RF-10 | Detalle de canción | Implementado | Endpoint y pantalla en el frontend (ver `docs/api.md`). |
| RF-11 | Búsqueda global | Parcial | Prefijo en nombres de artistas, álbumes y canciones; no búsqueda por subcadena ni texto completo. |
| RF-12 | Filtrar por género | Implementado | El catálogo de canciones consulta el GSI por género. |
| RF-13 | Marcar/desmarcar favoritos | Implementado | `PUT`/`DELETE /me/favorites/{songId}`. |
| RF-14 | Calificar canciones (1–5) | Implementado | `PUT/GET/DELETE /me/ratings/{songId}`; una calificación por usuario, promedio y conteo en el detalle de la canción. |
| RF-15 | Escribir reseñas | Implementado | `PUT/DELETE /me/reviews/{songId}` (1–1000 caracteres, una por usuario). |
| RF-16 | Consultar reseñas | Implementado | `GET /songs/{songId}/reviews` paginado. |
| RF-17 | Favoritos del usuario | Implementado | `GET /me/favorites`. |
| RF-18 | Guardar canciones en biblioteca | Implementado | `PUT /me/library/{songId}`. |
| RF-19 | Eliminar canciones de biblioteca | Implementado | `DELETE /me/library/{songId}`. |
| RF-20 | Consultar biblioteca personal | Implementado | `GET /me/library`. |

## Requisitos no funcionales

| ID | Requisito | Estado | Evidencia / trabajo restante |
|---|---|---|---|
| RNF-01 | HTTPS en transmisión | Implementado en IaC | CloudFront HTTPS; endpoint de API usa HTTPS administrado por AWS. |
| RNF-02 | Autenticación delegada a Cognito | Implementado en arquitectura | User Pool y Hosted UI. Validar dominios/callbacks por entorno. |
| RNF-03 | Validación JWT en API Gateway | Implementado en IaC | Authorizer JWT con issuer/audience Cognito. |
| RNF-04 | Cero secretos en React | Implementado | Solo configuración pública `VITE_*`; no credenciales AWS. |
| RNF-05 | Validar/sanitizar entradas | Implementado en handlers | Validación de identificadores, paginación, query strings y JSON. |
| RNF-06 | Autoescalado nativo | Implementado por servicio | Lambda/DynamoDB on-demand; límites y costos deben revisarse en producción. |
| RNF-07 | Baja latencia | Parcial | Consultas por clave/GSI; no se define SLO ni medición de referencia. |
| RNF-08 | Paginación | Implementado | Límite y cursor opaco con `LastEvaluatedKey` codificado. |
| RNF-09 | Extensibilidad | Implementado en estructura | Módulos IaC y handlers por dominio. |
| RNF-10 | Entrega vía CloudFront | Implementado en IaC | Distribución CloudFront. |
| RNF-11 | Tolerancia a fallos parciales | Parcial | Servicios administrados y manejo explícito de errores; resiliencia/reintentos aún requieren pruebas. |
| RNF-12 | Disponibilidad | Parcial | Multi-AZ inherente a servicios administrados; no se define objetivo de disponibilidad. |
| RNF-13 | Logs JSON | Implementado | Logger estructurado en Lambda. |
| RNF-14 | Métricas custom | Implementado | Métricas EMF en el namespace `MusicVault` (Requests, ServerErrors, LatencyMs, Contributions). |
| RNF-15 | Dashboards | Implementado | Dashboard `music-vault-dev-overview` en Terraform (Lambda, API Gateway, DynamoDB y métricas propias). Alarmas opcionales, desactivadas por costo. |
| RNF-16 | TypeScript en frontend | Implementado | Vite + React + TypeScript. |
| RNF-17 | Arquitectura modular | Implementado | Componentes, contexto y servicios; backend dividido por dominios. |
| RNF-18 | Infraestructura declarativa | Implementado | Recursos del MVP en Terraform. |
| RNF-19 | Responsive mobile-first | Parcial | Layout flexible inicial; pruebas visuales en navegadores/tamaños pendientes. |
| RNF-20 | Navegadores modernos | Pendiente de validación | Matriz objetivo y pruebas automatizadas cross-browser pendientes. |
| RNF-21 | Carga/error/vacío en cada vista | Parcial | Estados incluidos en catálogo; añadir pruebas y aplicar patrón a vistas futuras. |

## Criterios de aceptación del MVP

- Catálogo muestra datos paginados y permite filtrar por prefijo/género.
- Sin datos se presenta un estado vacío; ante fallo se presenta error y reintento.
- Rutas personales exigen JWT válido; usuario se obtiene del claim verificado `sub`.
- Favoritos y biblioteca solo permiten leer/escribir datos del usuario autenticado.
- La infraestructura puede planearse por ambiente sin incluir secretos en el repositorio.
- Pruebas unitarias cubren validación, paginación y autorización de handlers.

## Fuera de alcance de esta entrega

- Moderación de reseñas (son de texto libre, una por usuario).
- Búsqueda de texto completo, stemming, ranking y sugerencias.
- Moderación, cargas masivas de catálogo y administración de contenido.
- Operación de un entorno productivo real, porque requiere cuenta AWS, DNS, presupuesto y valores de callback aportados por el operador.
