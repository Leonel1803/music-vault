# Guía del equipo: cómo funciona Music Vault y qué decir en la presentación

Esta guía es para explicar el proyecto a quien no escribió el código. Es técnica pero se entiende sin ser experto. Los detalles finos están en los otros documentos de `docs/`.

## 1. La idea en 30 segundos

**Music Vault** es una biblioteca de música en la nube. Cualquier persona puede explorar y buscar canciones, artistas y álbumes. Quien inicia sesión además puede guardar **favoritos** y armar su **biblioteca personal**.

Todo corre en AWS con un enfoque **serverless** (sin servidores): no administramos máquinas, AWS ejecuta nuestro código solo cuando alguien hace una petición y cobra por uso. Para un proyecto escolar el costo es casi cero.

> Frase para la presentación: *"Construimos una aplicación web completa sin administrar un solo servidor: el frontend se sirve desde una CDN, la lógica corre en funciones bajo demanda y los datos viven en una base de datos administrada. Toda la infraestructura se crea con código."*

## 2. Vista general

```
Usuario (navegador)
   │
   ├─► CloudFront (CDN, HTTPS) ──► S3 privado: archivos del frontend (React)
   │
   ├─► Cognito (Hosted UI): registro e inicio de sesión → devuelve un token JWT
   │
   └─► API Gateway (HTTP API) ──► Lambda (Python) ──► DynamoDB
            │                          │
            └── valida el JWT          └── logs en CloudWatch
                en rutas /me/*
```

Todo se crea y se versiona con **Terraform** (carpeta `terraform/`).

## 3. Los componentes, uno por uno

| Pieza | Qué es | Qué hace aquí | Analogía |
|---|---|---|---|
| **S3** | Almacenamiento de archivos | Guarda el frontend compilado. Es **privado**. | Una bodega con llave |
| **CloudFront** | CDN | Entrega el frontend rápido, con HTTPS, y es la única puerta al bucket (Origin Access Control). | El mostrador de la tienda |
| **Cognito** | Servicio de usuarios | Registro, login, contraseñas y emisión de tokens. No guardamos contraseñas nosotros. | El guardia que revisa credenciales |
| **API Gateway** | Puerta de entrada de la API | Recibe las peticiones HTTP, valida el token en las rutas privadas y las manda a Lambda. | La recepción |
| **Lambda** | Funciones sin servidor | Ejecutan la lógica en Python solo cuando hay petición. | Un empleado que se contrata por minuto |
| **DynamoDB** | Base de datos NoSQL | Guarda catálogo, favoritos y biblioteca. Pago por petición. | Un archivero muy rápido |
| **CloudWatch** | Monitoreo | Guarda los logs de las Lambdas (7 días) y, si se activa, alarmas. | Las cámaras de seguridad |
| **IAM** | Permisos | Cada Lambda tiene su propio rol con solo lo que necesita. | Gafetes con acceso limitado |
| **Terraform** | Infraestructura como código | Crea todo lo anterior de forma repetible. | Los planos del edificio |

## 4. Qué pasa cuando alguien usa la app

### 4.1 Explorar el catálogo (sin iniciar sesión)
1. El navegador pide la página a CloudFront, que la toma de S3.
2. React llama por ejemplo a `GET /songs` o `GET /search?q=...`.
3. API Gateway enruta a la Lambda `catalog`.
4. La Lambda consulta DynamoDB y devuelve JSON.
5. React lo muestra con paginación (botón "cargar más").

Estas rutas son **públicas** porque el catálogo es de solo lectura.

### 4.2 Iniciar sesión
1. El botón de login redirige a la **Hosted UI de Cognito** (pantalla de login de AWS).
2. El usuario se registra o entra.
3. Cognito lo regresa a nuestra app con un código; la app lo cambia por tokens (flujo **Authorization Code**, el recomendado actualmente).
4. El **JWT** queda en la sesión y se envía en el encabezado `Authorization` en cada llamada privada.

### 4.3 Favoritos y biblioteca personal (rutas `/me/*`)
1. React manda la petición con el token.
2. **API Gateway valida el JWT antes de llamar a Lambda**: firma, caducidad y emisor. Sin token válido responde `401` y Lambda ni se ejecuta.
3. La Lambda `interactions` (favoritos, calificaciones, reseñas) o `library` lee el `sub` (identificador único del usuario) **del token ya validado**, nunca de lo que mande el cliente.
4. Guarda o consulta en DynamoDB usando ese `sub` como llave.

> Punto fuerte para presentar: un usuario **no puede ver ni modificar** datos de otro, porque la identidad viene del token y no de un parámetro que se pueda falsificar.

## 5. Los datos (DynamoDB)

Usamos **una sola tabla** (diseño *single-table*), con llaves `PK` y `SK`, y un índice secundario global (`GSI1`) para listar y filtrar.

| Qué guardamos | PK | SK |
|---|---|---|
| Artista / Álbum / Canción | `ARTIST#id` / `ALBUM#id` / `SONG#id` | `METADATA` |
| Canción por género | `GENRE#rock` | `SONG#id` |
| Favorito de un usuario | `USER#<sub>` | `FAVORITE#<songId>` |
| Biblioteca de un usuario | `USER#<sub>` | `LIBRARY#<songId>` |

**Por qué así:** DynamoDB es muy rápido cuando se consulta por llave. Con esta estructura, "todos los favoritos de un usuario" es una sola consulta, no un escaneo de toda la tabla. Facturación **on-demand**: pagamos por lectura/escritura, no por tener la tabla encendida.

**Limitación honesta:** la búsqueda es por **prefijo** (empieza con...), no de texto completo. Un buscador real requeriría OpenSearch, que es más caro y queda fuera del alcance.

## 6. El backend (Python)

Carpeta `backend/src/`:
- `handler.py`: puntos de entrada de las tres Lambdas (`catalog`, `interactions` y `library`); registra métricas EMF.
- `catalog.py`: lógica del catálogo y búsqueda.
- `interactions.py` y `library.py`: favoritos, calificaciones, reseñas y biblioteca.
- `common.py`: respuestas JSON, errores, CORS, paginación con cursor.

**Paginación:** cada respuesta trae un `cursor` opaco. Para la siguiente página, el cliente lo reenvía. Así no cargamos miles de registros de golpe.

**Pruebas:** hay 13 pruebas unitarias (`python -m unittest discover -s tests -v`, desde `backend/`).

## 7. El frontend (React + TypeScript)

Carpeta `frontend/src/`:
- `context/AuthContext.tsx`: maneja sesión y login con Cognito (librería Amplify).
- `services/api.ts`: único lugar que habla con la API y agrega el token.
- `components/Catalog.tsx`, `Browse.tsx` (artistas, álbumes, detalle de canción con calificación y reseñas) y `PersonalLibrary.tsx`: pantallas; `router.ts`: navegación por hash.

La configuración (URL de la API, IDs de Cognito) viene de variables `VITE_*`. Son públicas por diseño y **no contienen secretos**.

## 8. Seguridad (lo que conviene mencionar)

- Bucket S3 **privado**; solo CloudFront entra mediante OAC.
- HTTPS en todo.
- Autenticación delegada a Cognito; no manejamos contraseñas.
- JWT validado en API Gateway antes de tocar nuestro código.
- **Mínimo privilegio:** cada Lambda con su propio rol IAM.
- CORS limitado a los orígenes permitidos.
- Sin credenciales en el repositorio.

## 9. Costos (por qué es barato)

Decisiones tomadas para que cueste casi nada:
- Todo es pago por uso (Lambda, DynamoDB on-demand, HTTP API).
- Solo 2 Lambdas agrupando casos de uso.
- Logs a 7 días; alarmas y logs de acceso de API **apagados por defecto**.
- Sin Point-in-Time Recovery en DynamoDB.
- Índice con proyección parcial (menos almacenamiento).
- CloudFront con `PriceClass_100` (solo regiones más baratas).
- Estado de Terraform local (sin bucket ni tabla de bloqueo extra).
- `terraform destroy` al terminar para dejar el costo en cero.

## 10. Infraestructura como código (Terraform)

Carpeta `terraform/`, dividida en módulos: `dynamodb`, `cognito`, `lambda`, `api_gateway`, `hosting`, `cloudwatch`. El archivo `main.tf` los conecta entre sí.

Ciclo: `terraform plan` (muestra qué va a crear) → `terraform apply` (lo crea) → `terraform destroy` (lo borra).

**Ventaja:** cualquiera del equipo puede recrear exactamente el mismo entorno con tres comandos. Detalle del despliegue en [configuracion-y-despliegue.md](./configuracion-y-despliegue.md).

## 11. Qué está hecho y qué no (sé honesto en la presentación)

**Hecho:** catálogo, búsqueda por prefijo, filtro por género, favoritos, biblioteca personal, calificaciones y reseñas, páginas de detalle y listados de artistas/álbumes, métricas personalizadas (EMF) y dashboard en CloudWatch, autenticación, hosting con CDN, infraestructura completa en Terraform, pruebas unitarias.

**Pendiente / parcial:** búsqueda solo por prefijo, respaldos y alarmas apagados por costo, validación visual en varios navegadores. Ver [requisitos.md](./requisitos.md).

**Desviación consciente:** el requisito pide una Lambda por caso de uso; agrupamos en dos para reducir costo y complejidad. Se justifica en [arquitectura.md](./arquitectura.md).

## 12. Guion sugerido (≈ 8 minutos, 4 personas)

| Parte | Quién | Contenido | Tiempo |
|---|---|---|---|
| 1 | Persona A | Problema, idea y vista general (sección 1 y 2) | 1.5 min |
| 2 | Persona B | Frontend, login con Cognito y JWT (secciones 4.2, 7) | 2 min |
| 3 | Persona C | API, Lambda y DynamoDB, modelo de datos (4.1, 4.3, 5, 6) | 2.5 min |
| 4 | Persona D | Terraform, seguridad, costos y pendientes (8 a 11) + demo | 2 min |

**Demo recomendada:** abrir la app, buscar una canción, filtrar por género, iniciar sesión, agregar un favorito y recargar para mostrar que persiste. Opcional: mostrar `GET /me/favorites` sin token y que responda `401`.

## 13. Preguntas probables del profesor

**¿Por qué serverless?** No administramos servidores, escala solo y pagamos por uso, ideal para carga baja e impredecible.

**¿Por qué DynamoDB y no SQL?** Los accesos son por llave (por usuario, por género). Escala sin administración y el costo on-demand es mínimo. Para relaciones complejas SQL sería mejor.

**¿Cómo evitan que alguien vea los favoritos de otro?** La identidad sale del JWT validado por API Gateway, no del cliente, y la llave en DynamoDB incluye ese `sub`.

**¿Dónde guardan las contraseñas?** En Cognito; nosotros nunca las vemos.

**¿Qué pasa si hay mucho tráfico?** Lambda, API Gateway y DynamoDB on-demand escalan automáticamente; CloudFront absorbe el frontend. El límite práctico serían las cuotas de la cuenta.

**¿Cómo lo despliegan otra vez?** Con `terraform apply`; la infraestructura es reproducible.

**¿Qué mejorarían?** Búsqueda de texto completo, más catálogo (`seed_catalog.py --data`), CI/CD y estado remoto de Terraform para trabajo en equipo.

## 14. Glosario rápido

- **Serverless:** el proveedor administra los servidores; tú solo subes código.
- **CDN:** red que entrega archivos desde puntos cercanos al usuario.
- **JWT:** token firmado que prueba quién eres sin consultar una base de datos.
- **CORS:** regla del navegador que define qué sitios pueden llamar a la API.
- **IAM:** sistema de permisos de AWS.
- **IaC:** infraestructura definida en archivos de código.
- **On-demand:** se paga por uso real, no por capacidad reservada.
