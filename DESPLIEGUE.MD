Antes de darte los pasos, corrijo un fallo que rompería el login. Cognito exige que la URL de callback coincida exactamente, con `/` final, pero CORS la necesita sin `/`.

Edit 

Ran terminal command: Set-Location C:\Users\leotr\music_vault\terraform; terraform validate; aws --version; aws sts get-caller-identity 2>&1 | Select-Object -First 3
Tool execution failed with exit code 254

Corregí el callback de Cognito. Lo que falta es tuyo: el AWS CLI está instalado, pero **tus credenciales AWS expiraron** (`ExpiredToken`), así que no puedo desplegar por ti.

## Pasos para montarlo (PowerShell)

**1. Renueva credenciales** (si usas AWS Academy/Learner Lab, copia las credenciales nuevas desde "AWS Details"). Comprueba con:
```powershell
aws sts get-caller-identity
```

**2. Configura Terraform**
```powershell
cd C:\Users\leotr\music_vault\terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```
Edita `terraform.tfvars` y cambia `cognito_domain_prefix` por algo único, por ejemplo `musicvault-leo-2026`. Usa solo minúsculas, números y guiones.

**3. Crea la infraestructura**
```powershell
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```
Revisa el plan antes de aplicar. Si usas Learner Lab, puede bloquear la creación de algún rol IAM o recurso. Si pasa, mándame el error.

**4. Carga datos de prueba**
```powershell
cd ..\backend
python -m pip install -r requirements-dev.txt
python scripts/seed_catalog.py --table music-vault-dev-data
```

**5. Configura el frontend.** Crea `frontend\.env.local` con los valores de:
```powershell
terraform "-chdir=..\terraform" output
```
Usa estas equivalencias:
- `api_base_url` → `VITE_API_BASE_URL`
- `cognito_user_pool_id` → `VITE_COGNITO_USER_POOL_ID`
- `cognito_app_client_id` → `VITE_COGNITO_USER_POOL_CLIENT_ID`
- `cognito_domain` → `VITE_COGNITO_DOMAIN`
- Las dos URLs de redirección pueden quedar con `http://localhost:5173/` para probar local.

**6. Prueba local**
```powershell
cd ..\frontend
npm run dev
```
Abre `http://localhost:5173`, regístrate e inicia sesión.

**7. Publica en CloudFront (opcional)**
1. Toma `cloudfront_domain_name` de los outputs.
2. En `terraform.tfvars`, agrega `"https://<dominio>"` a `allowed_origins`.
3. Ejecuta `terraform apply`.
4. En `.env.local`, cambia ambas redirecciones a `https://<dominio>/`.
5. Ejecuta:
```powershell
cd frontend
npm run build
$bucket = terraform "-chdir=..\terraform" output -raw frontend_bucket_name
aws s3 sync .\dist "s3://$bucket" --delete
$dist = terraform "-chdir=..\terraform" output -raw cloudfront_distribution_id
aws cloudfront create-invalidation --distribution-id $dist --paths "/*"
```

**8. Al terminar la presentación**
```powershell
cd terraform
terraform destroy
```
Esto borra también los datos de DynamoDB. Revisa el plan antes de confirmar.

Si algún paso falla, pégame el error y lo reviso.