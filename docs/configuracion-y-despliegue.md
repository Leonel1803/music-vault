# Configuración, despliegue y operación

## Requisitos

- AWS CLI v2 autenticado con rol de despliegue limitado.
- Terraform 1.6+.
- Python 3.12+, Node.js 20+ y npm.
- Un dominio verificado en Route 53/ACM si se desea dominio propio; CloudFront ACM requiere certificado en `us-east-1`. No se usa en este proyecto: la organización de la cuenta solo permite `us-east-2` y CloudFront usa su certificado por defecto.
- Región: la cuenta del proyecto solo permite `us-east-2` (un SCP niega las demás). Configúrala una vez con `aws configure set region us-east-2`; Terraform y el seed ya la usan por defecto.

No ejecutar despliegues en una cuenta compartida sin autorización y revisión de costos.

## Variables de frontend

Para desarrollo local, copia `frontend/.env.example` a `frontend/.env.local`. Para publicar con `npm run build`, configura los valores del despliegue en `frontend/.env.production.local`:

| Variable | Descripción |
|---|---|
| `VITE_API_BASE_URL` | URL base HTTPS de API Gateway. |
| `VITE_COGNITO_USER_POOL_ID` | ID público del User Pool. |
| `VITE_COGNITO_USER_POOL_CLIENT_ID` | App client público, sin client secret. |
| `VITE_COGNITO_DOMAIN` | Dominio Hosted UI, sin protocolo. |
| `VITE_COGNITO_REDIRECT_SIGN_IN` | URI de callback registrada en Cognito. |
| `VITE_COGNITO_REDIRECT_SIGN_OUT` | URI de salida registrada en Cognito. |

Las URLs de callback/salida deben coincidir exactamente con las configuradas en el App Client.

### Obtener valores para el frontend publicado

Después del primer `terraform apply`, ejecuta estos comandos desde la carpeta `frontend` para consultar los outputs del estado local de Terraform:

```powershell
terraform "-chdir=..\terraform" output -raw api_base_url
terraform "-chdir=..\terraform" output -raw cognito_user_pool_id
terraform "-chdir=..\terraform" output -raw cognito_app_client_id
terraform "-chdir=..\terraform" output -raw cognito_domain
terraform "-chdir=..\terraform" output -raw cloudfront_domain_name
```

Copia cada resultado a `frontend/.env.production.local` como sigue:

```dotenv
VITE_API_BASE_URL=<api_base_url>
VITE_COGNITO_USER_POOL_ID=<cognito_user_pool_id>
VITE_COGNITO_USER_POOL_CLIENT_ID=<cognito_app_client_id>
VITE_COGNITO_DOMAIN=<cognito_domain>
VITE_COGNITO_REDIRECT_SIGN_IN=https://<cloudfront_domain_name>/
VITE_COGNITO_REDIRECT_SIGN_OUT=https://<cloudfront_domain_name>/
```

Reemplaza los marcadores completos, incluidos `<` y `>`. El dominio de Cognito va sin `https://`; las URLs de retorno y salida incluyen `https://` y la barra final. El archivo es local: no lo subas a Git ni incluyas secretos en variables `VITE_`, ya que sus valores se incorporan al código público del navegador.

Antes de probar el inicio de sesión, añade `https://<cloudfront_domain_name>` **sin barra final** a `allowed_origins` en `terraform.tfvars`, conservando los otros orígenes necesarios, y ejecuta el segundo `terraform apply`. Terraform agrega la barra final al registrar las URLs de retorno y salida en Cognito.

Vite incorpora estas variables al construir el frontend. Después de cambiarlas, ejecuta de nuevo `npm run build`, publica `dist` e invalida CloudFront siguiendo los comandos de publicación. Las variables del entorno de PowerShell con el mismo nombre tienen prioridad sobre los archivos `.env`.

## Backend

`backend/src/handler.py` expone handlers que reciben evento HTTP API v2. Configurar `TABLE_NAME` y `LOG_LEVEL` desde Terraform. Para pruebas unitarias no se requiere AWS; para invocar DynamoDB localmente se puede usar un perfil AWS explícito o LocalStack (no se configura automáticamente).

### Carga del catálogo de prueba

Después de crear la tabla con Terraform, carga el catálogo ficticio de artistas, álbumes y canciones. Se necesitan credenciales AWS configuradas con permisos de escritura en la tabla. Desde la carpeta `frontend`, ejecuta:

```powershell
Set-Location ..\backend
python -m pip install -r requirements-dev.txt
python scripts\seed_catalog.py --table music-vault-dev-data --region us-east-2
```

El script muestra cuántos elementos cargó. Para verificar hasta diez elementos evaluados de la tabla:

```powershell
aws dynamodb scan --table-name music-vault-dev-data --region us-east-2 --limit 10
```

Estos comandos usan el nombre de tabla del entorno `dev`; ajústalo si cambiaste el nombre del proyecto o el entorno. El script es idempotente para los IDs de muestra, pero sobrescribe los elementos existentes con las mismas claves. Úsalo solo en desarrollo, no para poblar ambientes productivos.

## Terraform

Para este proyecto individual de escuela Terraform usa **estado local**: no crea un bucket S3 ni una tabla DynamoDB solo para guardar el estado.

1. Copia `terraform/terraform.tfvars.example` como `terraform/terraform.tfvars` y reemplaza el prefijo Cognito con uno globalmente único. No subir el archivo local.
2. Inicializa, valida y revisa el plan:

   ```powershell
   Set-Location terraform
   terraform init
   terraform fmt -check -recursive
   terraform validate
   terraform plan -out=tfplan
   ```

3. Revisa recursos y costo estimado antes de aplicar. `terraform apply tfplan` crea recursos facturables. El estado local (`terraform.tfstate`) está ignorado por Git; consérvalo en una ubicación privada, no lo compartas y no lo elimines mientras administras recursos existentes.
4. Tras conocer el dominio CloudFront, añade `https://<dominio-cloudfront>` a `allowed_origins` en `terraform.tfvars` y aplica Terraform otra vez para registrar los callback/logout de Cognito y permitir el origen en API Gateway. No retires el callback local mientras lo uses en desarrollo.
5. Copia los outputs de Cognito y API Gateway a `frontend/.env.production.local` como se describe en **Obtener valores para el frontend publicado**.
6. Despliega el frontend: `npm run build`, sincroniza `frontend/dist` con el bucket privado mediante el flujo de publicación autorizado y realiza invalidación CloudFront cuando corresponda.
7. Ejecuta las pruebas de humo descritas abajo y elimina recursos de desarrollo con `terraform destroy` solo tras revisar el plan de destrucción y preservar datos necesarios.

Comandos de publicación desde PowerShell, una vez que `terraform apply` haya terminado:

```powershell
Set-Location ..\frontend
npm run build
$bucket = terraform "-chdir=..\terraform" output -raw frontend_bucket_name
aws s3 sync .\dist "s3://$bucket" --delete
$distribution = terraform "-chdir=..\terraform" output -raw cloudfront_distribution_id
aws cloudfront create-invalidation --distribution-id $distribution --paths "/*"

$domain = terraform "-chdir=..\terraform" output -raw cloudfront_domain_name
"https://$domain"
```

La SPA debe construirse y subirse después de configurar los valores de producción.

## Verificación de humo

- Abrir el dominio CloudFront, confirmar HTTPS y carga de la SPA.
- Confirmar que `GET /songs` responde con lista paginada o lista vacía válida.
- Ejecutar la carga ficticia de desarrollo si se requiere comprobar resultados no vacíos.
- Confirmar que una ruta `/me/*` sin JWT devuelve 401/403.
- Con dos usuarios de prueba, verificar que favoritos/biblioteca no se cruzan.
- Verificar error, vacío, carga y reintento del frontend.
- Confirmar logs JSON en CloudWatch sin tokens ni datos personales.

## Incidentes y recuperación

1. Revisar métricas/logs por `requestId`, sin copiar tokens o datos personales.
2. Confirmar estado de Cognito, API Gateway, Lambda y DynamoDB en la región.
3. Revertir artefacto frontend o release Lambda mediante el pipeline/versionado; evitar cambios manuales no trazados.
4. Si hay corrupción de catálogo, restaurar desde backup/PITR según el procedimiento aprobado y ensayar en ambiente no productivo primero.

## Costos y ambientes

Usar solo un ambiente `dev` para la entrega. Los valores de bajo costo por defecto son: DynamoDB on-demand sin PITR, GSI con proyección `INCLUDE` solo de los atributos mostrados, paquete Lambda sin tests/scripts de desarrollo, logs Lambda con retención de 7 días, sin logs de acceso API Gateway y sin alarmas/SNS. API Gateway HTTP API, Lambda, S3/CloudFront y Cognito permanecen porque representan la arquitectura evaluada y cobran según uso. DynamoDB on-demand evita pagar capacidad provisionada en periodos sin tráfico, pero las lecturas/escrituras y el almacenamiento siguen teniendo costo.

No ejecutar `terraform apply` salvo que necesites demostrar AWS. Para una demo local basta con frontend y pruebas; no se incurre en cargos AWS. Si despliegas, elimina los recursos después de la presentación y verifica la consola de facturación unos días después. `terraform destroy` destruye también la tabla de datos; exporta cualquier evidencia necesaria antes.

PITR, alarmas y logs de acceso pueden activarse temporalmente en `terraform.tfvars` (`enable_point_in_time_recovery`, `enable_alarms`, `enable_api_access_logs`), sabiendo que aumentan costo. Si habilitas alarmas sin `alarm_email`, se crearán alarmas sin notificación.
