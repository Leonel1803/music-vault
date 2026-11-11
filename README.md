# Biblioteca de Música

Aplicación web para descubrir música y administrar una biblioteca personal. La solución sigue la arquitectura serverless en AWS descrita en [AGENT.md](./AGENT.md): React con TypeScript, Amazon Cognito, API Gateway, AWS Lambda, DynamoDB, S3, CloudFront y Terraform.

## Alcance actual

La aplicación implementa catálogo de artistas, álbumes y canciones; búsqueda por prefijo y filtro por género; páginas de detalle; favoritos y biblioteca personal; y calificaciones y reseñas por usuario. El frontend está construido con React/TypeScript. Cognito autentica las rutas privadas y el backend Python expone la API mediante API Gateway y tres Lambdas (`catalog`, `interactions`, `library`).

La infraestructura AWS está definida con Terraform. La matriz de [`docs/requisitos.md`](./docs/requisitos.md) registra el estado de cada requisito. La búsqueda usa índices de DynamoDB y es por prefijo; no sustituye un motor de búsqueda de texto completo. La moderación de reseñas, los respaldos y las alarmas operativas siguen fuera del alcance de la configuración escolar de bajo costo.

## Estructura

```text
.
├── backend/
│   ├── src/                 # Handlers y utilidades Python para Lambda
│   └── tests/               # Pruebas unitarias sin acceso a AWS
├── docs/                    # Arquitectura, API, requisitos y operación
├── frontend/
│   └── src/                 # React + TypeScript
└── terraform/               # Infraestructura AWS con Terraform
```

## Desarrollo local

Requisitos: Python 3.12+, Node.js 20+, npm y Terraform 1.6+ (solo para IaC).

### Backend

```powershell
cd backend
python -m unittest discover -s tests -v
```

El handler espera un evento compatible con API Gateway HTTP API. Para ejecutar la aplicación conectada a AWS, configura las variables descritas en [`docs/configuracion-y-despliegue.md`](./docs/configuracion-y-despliegue.md) y despliega primero la infraestructura. No se incluyen credenciales ni datos de producción.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Crea `frontend/.env.local` a partir de `frontend/.env.example`. Los valores `VITE_COGNITO_*` y `VITE_API_BASE_URL` son identificadores/configuración pública, no secretos. Nunca guardes claves privadas o credenciales AWS en el bundle.

## Infraestructura

Consulta [`docs/configuracion-y-despliegue.md`](./docs/configuracion-y-despliegue.md) antes de aplicar Terraform. Los recursos facturables y públicos deben revisarse en el plan. El bucket de frontend permanece privado y CloudFront accede mediante Origin Access Control.

El perfil predeterminado es para una entrega escolar de bajo tráfico: estado Terraform local, DynamoDB bajo demanda sin PITR, logs Lambda de 7 días y alarmas/logs de acceso API desactivados. La infraestructura AWS sigue generando cargos por uso; para solo mostrar la app, ejecútala localmente y no apliques Terraform.

## Documentación

- [Infraestructura para principiantes](./docs/infraestructura-para-principiantes.md)
- [Lenguaje de Terraform para principiantes](./docs/lenguaje-terraform-para-principiantes.md)
- [Guía del equipo y guion de presentación](./docs/guia-del-equipo.md)
- [Terraform explicado por qué cada recurso](./docs/terraform-explicado.md)
- [Arquitectura y decisiones](./docs/arquitectura.md)
- [Requisitos y estado de cumplimiento](./docs/requisitos.md)
- [Contrato REST](./docs/api.md)
- [Configuración, despliegue y operación](./docs/configuracion-y-despliegue.md)
- [Modelo de datos](./docs/modelo-de-datos.md)
- [Seguridad y observabilidad](./docs/seguridad-y-observabilidad.md)
