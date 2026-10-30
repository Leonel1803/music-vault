# Biblioteca de Música

Aplicación web para descubrir música y administrar una biblioteca personal. La solución sigue la arquitectura serverless en AWS descrita en [AGENT.md](./AGENT.md): React con TypeScript, Amazon Cognito, API Gateway, AWS Lambda, DynamoDB, S3, CloudFront y Terraform.

## Alcance actual

Este repositorio parte de cero. La primera entrega establece el esqueleto ejecutable y documentado para el MVP:

- Frontend React/TypeScript con búsqueda y filtro de catálogo, y vistas explícitas de carga, error y vacío.
- API en Python para consultar artistas, álbumes y canciones, además de gestionar favoritos y biblioteca personal.
- Autenticación Cognito para rutas privadas; las rutas públicas de catálogo no requieren sesión.
- Terraform como infraestructura declarativa.
- Contratos, decisiones, configuración, pruebas y requisitos pendientes documentados en [`docs/`](./docs/).

La implementación inicial no afirma que todas las funciones del curso ya estén terminadas. La matriz de [`docs/requisitos.md`](./docs/requisitos.md) distingue lo implementado de lo pendiente y define las siguientes fases. En particular, calificaciones y reseñas quedan para la siguiente iteración; la búsqueda se apoya en índices de DynamoDB y no pretende reemplazar un motor de búsqueda de texto completo.

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

- [Guía del equipo y guion de presentación](./docs/guia-del-equipo.md)
- [Terraform explicado por qué cada recurso](./docs/terraform-explicado.md)
- [Arquitectura y decisiones](./docs/arquitectura.md)
- [Requisitos y estado de cumplimiento](./docs/requisitos.md)
- [Contrato REST](./docs/api.md)
- [Configuración, despliegue y operación](./docs/configuracion-y-despliegue.md)
- [Modelo de datos](./docs/modelo-de-datos.md)
- [Seguridad y observabilidad](./docs/seguridad-y-observabilidad.md)
