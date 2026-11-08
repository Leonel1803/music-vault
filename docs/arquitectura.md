# Arquitectura

## Objetivo y alcance

La aplicación es un catálogo de artistas, álbumes y canciones con búsqueda, filtros, páginas de detalle y colecciones privadas por usuario. Cognito autentica las operaciones privadas. Los usuarios pueden guardar favoritos y canciones en su biblioteca, calificar canciones y publicar una reseña por canción.

## Componentes y flujo

1. El navegador descarga la SPA desde CloudFront.
2. CloudFront entrega los archivos desde un bucket S3 privado mediante Origin Access Control. HTTPS es obligatorio.
3. La SPA usa Cognito Hosted UI/OAuth para registro e inicio de sesión. La biblioteca JavaScript de Amplify administra la sesión y entrega el access token; el hosting no usa Amplify Hosting.
4. El cliente llama a API Gateway HTTP API. El JWT authorizer de Cognito valida issuer, audiencia y firma antes de permitir rutas privadas.
5. API Gateway enruta al handler Lambda Python correspondiente. Los handlers validan el evento y el identificador de usuario procede exclusivamente de los claims validados por el authorizer.
6. Lambda consulta o modifica DynamoDB con permisos IAM limitados a la tabla del entorno.
7. CloudWatch recibe logs JSON y métricas de los servicios.

## Decisiones de diseño

| Tema | Decisión | Motivo / consecuencia |
|---|---|---|
| Runtime backend | Python 3.12 en Lambda | Elección del usuario; el SDK AWS disponible en Lambda evita dependencias externas para DynamoDB. |
| API | API Gateway HTTP API | Menor complejidad y costo para REST; JWT authorizer integrado con Cognito. |
| Persistencia | Tabla DynamoDB única con claves compuestas e índices secundarios | Permite consultas por entidad, género y usuario; requiere preservar los patrones de acceso documentados. |
| Búsqueda | Prefijo por nombre normalizado mediante GSI | La búsqueda funciona por prefijo; búsqueda arbitraria/subcadena y relevancia quedan fuera del MVP. Para eso evaluar OpenSearch u otro índice administrado. |
| Hosting | S3 privado + CloudFront OAC | No se publica el bucket; CloudFront entrega la SPA por HTTPS. |
| IaC | Terraform por módulos | Recursos, permisos, outputs y parámetros quedan versionados y reproducibles. |
| Separación | Tres funciones Lambda por caso de uso: `catalog` (lectura pública), `interactions` (favoritos, calificaciones, reseñas) y `library` (biblioteca) | Cada una tiene su propio rol IAM con solo las acciones de DynamoDB que necesita (p. ej. solo `interactions` puede hacer `UpdateItem`). |

## Desviaciones explícitas del diseño objetivo

- Las funciones Lambda están separadas por caso de uso (catálogo, interacciones y biblioteca), todas con el mismo código base y distinto handler y rol IAM. Los endpoints de un mismo dominio comparten función para mantener bajo el costo y la cantidad de recursos.
- La búsqueda de MVP es por prefijo y tiene un máximo de resultados; no sustituye búsqueda de texto completo.
- La distribución usa el dominio `cloudfront.net` administrado por AWS. Dominio propio, ACM, DNS y políticas WAF quedan a configurar por ambiente.

## Límites de confianza

- El cliente es no confiable: todo dato se valida en backend. Los IDs de usuario no se aceptan desde body/query para operaciones personales.
- API Gateway autoriza rutas privadas antes de invocar Lambda. Lambda vuelve a validar la presencia del claim `sub` para fallar de forma cerrada si el evento está mal formado.
- Los roles Lambda solo deben permitir las acciones DynamoDB necesarias sobre la tabla declarada.
- El bucket S3 no tiene acceso público; solo CloudFront tiene permiso de lectura.
- Las variables frontend con prefijo `VITE_` se consideran públicas.

## Modos de fallo y UX

- Fallo de API: mostrar mensaje y acción de reintento; no simular respuesta exitosa.
- Catálogo sin resultados: mostrar estado vacío distinto de error.
- Carga inicial o cambio de filtro: mostrar indicador de carga.
- Sesión expirada: limpiar la sesión local y dirigir al usuario al flujo de autenticación.
- En el perfil escolar, los logs de aplicación se conservan 7 días; los logs de acceso API y alarmas CloudWatch/SNS están desactivados por defecto para limitar cargos. Pueden activarse temporalmente cuando se necesite demostrar observabilidad.

## Evolución

1. MVP implementado: catálogo, búsqueda por prefijo, filtro de género, autenticación, favoritos, biblioteca personal, calificaciones y reseñas.
2. Mejoras de contenido: moderación de reseñas, administración de catálogo y búsqueda de texto completo.
3. Producción: pipeline CI/CD, protección de despliegues, alarmas/SLO, pruebas de carga, recuperación y escaneo de dependencias.

## Diagrama

El diagrama entregado en el repositorio está en [`arquitectura.png`](../arquitectura.png). La implementación mantiene el flujo CloudFront → S3 para la SPA y Cognito → API Gateway → Lambda → DynamoDB para el backend.
