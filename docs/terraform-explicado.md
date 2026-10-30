# Terraform explicado: qué hace cada archivo y por qué

Guía para el equipo. Para cada pieza se responde: **qué es**, **qué hace** y **por qué lo decidimos así**. Todo vive en `terraform/`.

## 0. Conceptos básicos de Terraform

- **Resource:** un objeto real de AWS que Terraform crea (una tabla, una Lambda...).
- **Module:** una carpeta reutilizable que agrupa recursos relacionados. Cada servicio tiene el suyo.
- **Variable:** un valor configurable (por ejemplo, la región).
- **Output:** un dato que Terraform muestra al terminar (por ejemplo, la URL de la API).
- **Data source:** información que se *lee* de AWS, no se crea.
- **Estado (`terraform.tfstate`):** la "memoria" de Terraform sobre qué ya creó. Está en local para ahorrar costo.
- **Plan/Apply:** `plan` muestra qué cambiaría; `apply` lo ejecuta.

Estructura:

```
terraform/
├── versions.tf      # versiones y proveedor AWS
├── variables.tf     # parámetros configurables
├── main.tf          # conecta todos los módulos
├── outputs.tf       # datos finales
├── terraform.tfvars.example
└── modules/
    ├── dynamodb/    ├── cognito/      ├── lambda/
    ├── api_gateway/ ├── hosting/      └── cloudwatch/
```

Cada módulo repite el patrón `main.tf` (recursos), `variables.tf` (lo que recibe) y `outputs.tf` (lo que entrega).

## 1. `versions.tf`: versiones y proveedor

| Elemento | Qué hace | Por qué |
|---|---|---|
| `required_version >= 1.6.0` | Exige una versión mínima de Terraform | Evita que alguien con una versión vieja obtenga errores raros |
| Proveedor `aws ~> 5.0` | Plugin que habla con AWS | Fijar la versión mayor da resultados repetibles |
| Proveedor `archive` | Crea el `.zip` del backend | Lambda necesita el código empaquetado |
| `default_tags` | Etiqueta cada recurso con `Project`, `Environment`, `ManagedBy` | Permite ver en la facturación cuánto cuesta el proyecto y saber qué se creó con Terraform |

No hay bloque `backend`: el estado es **local**. Se eliminó el bucket remoto y la tabla de bloqueo porque cuestan y no se justifican para un proyecto escolar de una sola persona desplegando.

## 2. `variables.tf`: los parámetros

| Variable | Valor por defecto | Por qué existe |
|---|---|---|
| `project_name` | `music-vault` | Prefijo de todos los nombres |
| `environment` | `dev` | Permite separar ambientes (dev/test/prod) sin cambiar código |
| `aws_region` | `us-east-2` | Única región permitida por la organización de la cuenta (el SCP niega las demás); tiene todos los servicios usados |
| `cognito_domain_prefix` | **sin default** | Debe ser **único en todo el mundo**, no podemos adivinarlo; por eso es obligatorio. Tiene validación de formato (minúsculas, números, guiones) |
| `allowed_origins` | `http://localhost:5173` | Sitios autorizados para llamar la API (CORS) y para el login de Cognito. Se agrega el dominio de CloudFront después |
| `enable_point_in_time_recovery` | `false` | Respaldo continuo de DynamoDB; cuesta, no necesario en la escuela |
| `log_retention_days` | `7` | Los logs se borran a los 7 días para no pagar almacenamiento. Valida que sea un valor que CloudWatch acepte |
| `enable_api_access_logs` | `false` | Logs de cada petición a la API; generan costo por ingesta |
| `enable_alarms` | `false` | Alarmas de CloudWatch; apagadas por costo |
| `alarm_email` | vacío | Correo para avisos, solo si se activan alarmas |

**Idea clave:** casi todo lo "profesional pero caro" se dejó como interruptor apagado. Se puede encender sin tocar código.

## 3. `main.tf` (raíz): el director de orquesta

Aquí no se crean recursos pesados; se **conectan módulos** pasando las salidas de uno como entradas de otro.

- `locals.name = "music-vault-dev"`: un nombre base que se reutiliza para que todo tenga nombres coherentes.
- Orden implícito: Terraform deduce las dependencias. DynamoDB y Cognito se crean primero → Lambda necesita la tabla → API Gateway necesita Lambda y Cognito.
- **Callback/logout URLs de Cognito:** se arman añadiendo `/` a cada origen. Cognito exige coincidencia **exacta** con la URL de retorno (con `/` al final), mientras que CORS exige **sin** `/`. Por eso usamos la misma lista con dos formatos.
- **`aws_lambda_permission` (x2):** por defecto AWS no deja que API Gateway invoque una Lambda. Estos permisos autorizan explícitamente a `apigateway.amazonaws.com` a llamar cada función, limitado a nuestra API (`source_arn`).

## 4. Módulo `dynamodb`: la base de datos

| Configuración | Por qué |
|---|---|
| `billing_mode = PAY_PER_REQUEST` | Pagas por lectura/escritura, no por capacidad reservada. Con poco tráfico cuesta centavos |
| `hash_key = PK`, `range_key = SK` | Diseño *single-table*: toda la información en una sola tabla, distinguida por prefijos (`USER#`, `SONG#`...) |
| Atributos `GSI1PK` / `GSI1SK` | Llaves de un índice secundario para consultas alternativas (listar por tipo, filtrar por género) |
| `GSI1` con proyección `INCLUDE` | El índice solo copia los campos que la lista necesita (no todos). Menos almacenamiento = menos costo |
| `point_in_time_recovery` | Controlado por variable (apagado) |
| `server_side_encryption` | Cifrado en reposo; no cuesta extra y es buena práctica |

Solo se declaran como atributos las **llaves**: DynamoDB es sin esquema para el resto de los campos.

## 5. Módulo `cognito`: usuarios y login

| Recurso | Qué hace | Por qué |
|---|---|---|
| `aws_cognito_user_pool` | El directorio de usuarios | No guardamos contraseñas nosotros; es más seguro y gratis en este volumen |
| `username_attributes = email` + `auto_verified_attributes` | Se entra con correo y se verifica | Más simple para el usuario |
| `password_policy` | Mínimo 12 caracteres con mayúscula, minúscula, número y símbolo | Contraseñas robustas |
| `aws_cognito_user_pool_client` | La "aplicación" (nuestro frontend) registrada en Cognito | Define cómo se puede iniciar sesión |
| `generate_secret = false` | Sin secreto de cliente | Un frontend en el navegador **no puede guardar secretos**; se protege con PKCE |
| `allowed_oauth_flows = code` | Flujo *Authorization Code* | Es el flujo recomendado; evita exponer tokens en la URL |
| Scopes `openid email profile` | Datos que podemos leer del usuario | Solo lo necesario |
| `prevent_user_existence_errors` | No revela si un correo está registrado | Evita enumeración de usuarios |
| `callback_urls` / `logout_urls` | A dónde puede regresar Cognito | Evita que un atacante redirija el token a otro sitio |
| `aws_cognito_user_pool_domain` | Dirección de la pantalla de login (Hosted UI) | Nos ahorra programar el login y el registro |

Salida importante `issuer`: la URL que identifica quién emite los tokens. API Gateway la usa para validarlos.

## 6. Módulo `lambda`: la lógica

| Elemento | Qué hace | Por qué |
|---|---|---|
| `archive_file` | Empaqueta `backend/` en un zip y excluye `scripts/`, `tests/` y `requirements-dev.txt` | Zip más pequeño y no se sube código que no corre en producción |
| `locals.functions` | Define tres funciones, `catalog`, `interactions` y `library`, con su handler y sus permisos | Un solo bloque genera las tres con `for_each`, sin repetir código |
| `aws_iam_role` (uno por función) | Identidad con la que corre cada Lambda | Mínimo privilegio y aislamiento |
| `aws_iam_role_policy` | Qué puede hacer ese rol | **`catalog` solo lee** (`GetItem`, `Query`). **`personal` además escribe y borra**. Ambas solo sobre nuestra tabla y sus índices, y solo escribir logs en su propio grupo |
| `aws_cloudwatch_log_group` | Grupo de logs de cada función con retención de 7 días | Lo creamos nosotros para controlar la retención; si no, AWS lo crea con retención infinita |
| `aws_lambda_function` | La función en sí | Ver parámetros abajo |

Parámetros de la función:
- `runtime = python3.12`: versión soportada y estable de Python.
- `timeout = 10`: una consulta a DynamoDB tarda milisegundos; 10 s evita que un error cobre minutos.
- `memory_size = 256`: balance costo/velocidad (más memoria también da más CPU).
- `source_code_hash`: hace que Terraform vuelva a desplegar solo cuando el código cambia.
- Variables de entorno `TABLE_NAME` y `LOG_LEVEL`: el código no tiene el nombre de la tabla escrito; lo recibe de afuera.

**Por qué tres funciones:** una por caso de uso (consulta del catálogo, interacciones del usuario y biblioteca). Cada una tiene su rol IAM con permisos mínimos; los endpoints del mismo dominio comparten función para no multiplicar recursos y arranques en frío.

## 7. Módulo `api_gateway`: la puerta de entrada

| Elemento | Qué hace | Por qué |
|---|---|---|
| `aws_apigatewayv2_api` (HTTP API) | La API pública | HTTP API es **más barata y rápida** que REST API y nos alcanza |
| `cors_configuration` | Permite llamadas solo desde `allowed_origins`, con métodos `GET/PUT/DELETE/OPTIONS` y encabezados `authorization` y `content-type` | El navegador bloquea llamadas entre sitios; esto lo autoriza solo para nuestro frontend |
| `aws_apigatewayv2_authorizer` (JWT) | Valida el token de Cognito (emisor, audiencia, firma, caducidad) | La validación ocurre **antes** de ejecutar Lambda: peticiones inválidas no consumen cómputo |
| Dos `integration` tipo `AWS_PROXY` | Conectan la API con cada Lambda | El evento HTTP completo pasa a la función |
| `aws_apigatewayv2_route` con `for_each` | Una ruta por cada endpoint de la lista `locals.routes` | Agregar un endpoint es agregar una línea |
| Regla de rutas | Cada ruta del mapa `routes` indica su función (`catalog`, `interactions` o `library`) y si exige JWT. Las `/me/*` exigen JWT; el resto son públicas | Catálogo abierto, datos personales protegidos |
| `aws_apigatewayv2_stage` `$default` con `auto_deploy` | Publica la API automáticamente | Sin pasos manuales de despliegue |
| `access_log_settings` (opcional) | Log de cada petición en JSON | Apagado por defecto por costo |

## 8. Módulo `hosting`: frontend en S3 + CloudFront

| Recurso | Qué hace | Por qué |
|---|---|---|
| `aws_s3_bucket` | Guarda los archivos del sitio. El nombre incluye el ID de cuenta | Los nombres de bucket son únicos globalmente; así se evitan colisiones |
| `public_access_block` | Bloquea cualquier acceso público | El bucket **nunca** debe ser público |
| `origin_access_control` (OAC) | Firma las peticiones de CloudFront a S3 | Es la forma moderna (reemplaza a OAI) de que solo CloudFront lea el bucket |
| `aws_cloudfront_distribution` | La CDN que sirve el sitio | HTTPS gratuito, caché global y velocidad |
| `default_root_object = index.html` | Archivo que se muestra en `/` | Página inicial |
| `viewer_protocol_policy = redirect-to-https` | Fuerza HTTPS | Seguridad |
| `compress = true` | Comprime archivos | Menos transferencia, más rápido y barato |
| `price_class = PriceClass_100` | Usa solo las ubicaciones más baratas (NA y Europa) | Ahorro de costo; para la escuela sobra |
| `custom_error_response` 403/404 → `/index.html` | Cualquier ruta desconocida devuelve la app | React maneja las rutas en el navegador (SPA); sin esto, recargar una ruta daría error |
| `viewer_certificate` por defecto | Certificado de `*.cloudfront.net` | Gratis; un dominio propio requeriría Route 53 y ACM |
| `aws_s3_bucket_policy` | Solo permite `s3:GetObject` a CloudFront, y únicamente a **nuestra** distribución (`AWS:SourceArn`) | Acceso mínimo y de solo lectura |

## 9. Módulo `cloudwatch`: alarmas (opcional)

Todo está condicionado a `enable_alarms` (apagado). Si se enciende:

| Recurso | Qué hace |
|---|---|
| Alarma `errors` por Lambda | Se dispara si hay ≥1 error en dos periodos de 5 min seguidos (evita falsas alarmas por un error aislado) |
| Alarma `throttles` por Lambda | Se dispara si AWS limita las ejecuciones |
| `treat_missing_data = notBreaching` | Sin tráfico no es una falla |
| `aws_sns_topic` + suscripción por correo | Envía el aviso al correo, solo si se configuró `alarm_email` |

Por qué apagadas: cada alarma tiene costo mensual, y en una app escolar sin tráfico no aportan. Para demostrar observabilidad se pueden encender antes de presentar.

## 10. `outputs.tf`: datos finales

Son los valores que necesitamos después del `apply`:

| Output | Para qué |
|---|---|
| `api_base_url` | URL de la API para el frontend |
| `cognito_user_pool_id`, `cognito_app_client_id`, `cognito_domain` | Configuración del login en el frontend (son públicos, no secretos) |
| `frontend_bucket_name` | Destino del `aws s3 sync` |
| `cloudfront_domain_name` | URL pública del sitio y valor para `allowed_origins` |
| `cloudfront_distribution_id` | Para invalidar la caché después de publicar |

## 11. Flujo de dependencias (resumen visual)

```
dynamodb ─────────────┐
                      ├─► lambda ──┐
cognito ──────────────┼────────────┼─► api_gateway ─► lambda_permission
                      │            │
hosting (independiente)            └─► cloudwatch (alarmas, opcional)
```

## 12. Resumen de decisiones de costo

| Decisión | Ahorro |
|---|---|
| DynamoDB on-demand, sin PITR, índice parcial | Sin cargos fijos |
| HTTP API en vez de REST | Aprox. 70 % más barata |
| 2 Lambdas, 256 MB, timeout 10 s | Menos cómputo |
| Logs a 7 días, access logs y alarmas apagados | Sin ingesta ni alarmas |
| CloudFront `PriceClass_100` y certificado por defecto | Sin dominio ni certificados de pago |
| Estado local | Sin bucket ni tabla de bloqueo |

## 13. Preguntas probables

**¿Por qué Terraform y no crear todo en la consola?** Es repetible, versionable y se destruye con un comando. Evita errores manuales y deja documentación ejecutable.

**¿Qué pasa si alguien borra algo a mano?** `terraform plan` detecta la diferencia y `apply` lo restaura.

**¿Por qué módulos?** Cada servicio queda aislado y legible; el archivo principal solo los conecta.

**¿Por qué hay dos pasadas de `apply`?** El dominio de CloudFront solo se conoce después de la primera. Hay que agregarlo a `allowed_origins` y aplicar otra vez para que CORS y Cognito lo acepten.

**¿Es seguro mostrar los IDs de Cognito y la URL de la API?** Sí, son públicos por diseño. La seguridad está en el JWT y los permisos IAM, no en ocultar esos valores.

**¿Y si perdemos `terraform.tfstate`?** Terraform no sabrá qué creó y habría que importarlo o borrar los recursos a mano. Por eso hay que conservarlo hasta el `destroy`.
