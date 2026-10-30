# Seguridad y observabilidad

## Seguridad

- Cognito User Pool administra identidad. Los clientes usan Authorization Code + PKCE en Hosted UI; no se almacena client secret en el navegador.
- API Gateway valida issuer, audience y expiración de JWT para rutas privadas.
- Los datos personales se particionan por el claim verificado `sub`. No se acepta un user ID elegido por el cliente.
- Las entradas externas se validan en backend: forma de IDs, longitud, filtros, límites, cursores y JSON.
- El handler devuelve errores genéricos; logs no incluyen tokens, credenciales, email, reseñas ni payloads sensibles.
- Roles IAM de Lambda con mínimo privilegio y acceso solo a tabla/acciones necesarias.
- S3 sin acceso público; CloudFront OAC; TLS mínimo y redirección HTTP→HTTPS.
- No guardar secretos en Git, variables `VITE_*`, logs, imágenes ni estado Terraform en texto plano. Usar AWS Secrets Manager/Parameter Store cuando se requiera un secreto de servidor.
- Aplicar `terraform plan` y revisión de seguridad antes de `apply`. El proyecto escolar utiliza estado Terraform local para evitar recursos recurrentes de almacenamiento/bloqueo: mantenerlo privado, respaldarlo de forma segura y no eliminarlo mientras existan recursos. Si varias personas administran la infraestructura, migrar a backend remoto cifrado, versionado y bloqueado.

## Logs y métricas

Los logs usan JSON con `level`, `message`, `requestId`, `route` y `timestamp`. No registran el evento completo ni encabezados. Campos sensibles se excluyen por diseño.

Métricas base recomendadas:

- `Errors` y `Throttles` de Lambda/API Gateway.
- Duración p50/p95 y `IteratorAge` donde aplique.
- Latencia y errores 4xx/5xx de API Gateway.
- Throttling y consumo de lectura/escritura DynamoDB.
- Tasa de login fallido de Cognito.

Alarmas iniciales: errores Lambda/API 5xx sostenidos, throttles, latencia por encima del umbral acordado y falta de datos de métricas críticas. Los umbrales y notificaciones dependen del entorno y deben configurarse antes de producción.

Métricas propias (EMF, namespace `MusicVault`, dimensión `Service`): `Requests`, `ServerErrors`, `LatencyMs` y `Contributions` (calificaciones y reseñas). Son pocas para quedar dentro de la capa gratuita. El dashboard `music-vault-dev-overview` (Terraform, módulo `cloudwatch`) muestra Lambda, API Gateway, DynamoDB y estas métricas.

## Privacidad y retención

Definir retención de logs por ambiente. El contenido de reseñas no se registra. Revisar requisitos institucionales aplicables y ofrecer procedimiento de eliminación de cuenta/datos antes de producción.

## Checklist previo a producción

- [ ] MFA/políticas de contraseña y recuperación aprobadas.
- [ ] Dominios HTTPS, redirects y CORS restringidos a dominios esperados.
- [ ] Revisión IAM, Cognito, CloudFront y cifrado por ambiente.
- [ ] Backup/PITR, prueba de restauración y plan de incidentes.
- [ ] Alarmas con destino operativo y umbrales probados (desactivadas por defecto en el ambiente escolar).
- [ ] Protección contra abuso (rate limits/WAF según riesgo).
- [ ] Pruebas de autorización cruzada entre usuarios y análisis de dependencias.
- [ ] Retención y eliminación de datos definida.
