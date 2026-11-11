# Infraestructura de Music Vault para principiantes

Esta guía explica cómo funciona la infraestructura del proyecto y cómo presentarla. No necesitas conocer AWS o Terraform de antemano. Los nombres de recursos son ejemplos del ambiente `dev`: podrían cambiar si se modifican las variables o se vuelve a crear la infraestructura.

Para aprender a leer los bloques, variables y expresiones HCL del proyecto, consulta [Cómo leer el lenguaje de Terraform](./lenguaje-terraform-para-principiantes.md). Para instrucciones de despliegue, consulta [Configuración y despliegue](./configuracion-y-despliegue.md). Para detalles técnicos, consulta [Arquitectura](./arquitectura.md), [Modelo de datos](./modelo-de-datos.md) y [Terraform explicado](./terraform-explicado.md).

## 1. La idea general

Music Vault es una aplicación web para consultar artistas, álbumes y canciones. Los usuarios que inician sesión también pueden guardar favoritos, formar una biblioteca, calificar y escribir reseñas.

La infraestructura son los servicios que permiten que la aplicación esté disponible, reciba peticiones, guarde datos y controle el acceso. En vez de instalar y administrar servidores propios, usamos servicios administrados de AWS. Terraform describe la configuración de esos servicios en archivos de código.

> **Para explicar al profesor:** «El navegador descarga la interfaz desde CloudFront. Cuando necesita datos, llama a una API que ejecuta funciones Lambda y consulta DynamoDB. Cognito administra el inicio de sesión; IAM limita permisos y CloudWatch permite observar la operación. Terraform define la infraestructura».

**Serverless** no significa que no existan servidores: significa que nosotros no administramos las máquinas que ejecutan estos servicios. Tampoco significa que sean gratuitos: AWS puede cobrar por recursos y uso.

## 2. Mapa de la aplicación

```text
                         ARCHIVOS DE LA APLICACIÓN
Navegador ── HTTPS ──> CloudFront ── acceso privado ──> S3
    │                   entrega el sitio                  guarda HTML, JS, CSS
    │
    │                    INICIO DE SESIÓN
    ├─────────────────> Cognito ──> regreso al navegador con sesión
    │
    │                    DATOS Y OPERACIONES
    └── petición HTTP ─> API Gateway ─> Lambda ─> DynamoDB
                         valida JWT       Python     datos
                         en rutas privadas

IAM limita lo que pueden hacer las funciones.
CloudWatch muestra métricas y logs.
Terraform define y conecta los recursos de AWS.
```

Las flechas son recorridos distintos: **CloudFront entrega el frontend**, mientras que **API Gateway recibe las solicitudes de datos**. No todas las acciones pasan por Cognito; consultar el catálogo es público.

## 3. Piezas básicas que conviene conocer

| Término | Significado en palabras sencillas |
|---|---|
| **Frontend** | Interfaz que ve el usuario en el navegador; aquí está hecha con React y TypeScript. |
| **Backend** | Código que procesa solicitudes y maneja datos; aquí está escrito en Python y se ejecuta en Lambda. |
| **API** | Conjunto de direcciones y reglas que el frontend usa para pedir o cambiar datos. |
| **Petición HTTP** | Mensaje a una dirección de la API. `GET` consulta, `PUT` crea o actualiza y `DELETE` elimina. |
| **JSON** | Formato de texto para intercambiar datos, por ejemplo `{"name": "Artista"}`. |
| **Región** | Ubicación de AWS para recursos regionales. En este proyecto se usa `us-east-2` (Ohio); CloudFront es un servicio global. |
| **Entorno** | Conjunto de recursos para un propósito. `dev` identifica este entorno de desarrollo y pruebas. |
| **ARN** | Identificador de un recurso en AWS; suele usarse en las políticas de permisos. |

## 4. Qué hace cada servicio

### 4.1 Amazon S3: dónde se guardan los archivos de la página

S3 es almacenamiento de objetos: guarda archivos dentro de un **bucket**. Después de `npm run build`, la carpeta `frontend/dist` contiene los archivos compilados que se suben al bucket del frontend.

En este proyecto el bucket bloquea el acceso público. No es la base de datos de canciones ni guarda las contraseñas: sus archivos son los que forman la página.

**Cómo se conecta:** CloudFront obtiene los archivos del bucket mediante **Origin Access Control (OAC)**, que permite dar acceso a la distribución sin hacer público el bucket.

**Para mostrarlo:** en AWS → S3 → bucket del frontend se pueden ver objetos como `index.html` y archivos del build. El nombre del bucket se obtiene con `terraform output -raw frontend_bucket_name`.

### 4.2 Amazon CloudFront: cómo llega la página al navegador

CloudFront es una red de distribución de contenido o **CDN**. Recibe las solicitudes del navegador, entrega archivos desde su caché cuando corresponde y, si los necesita, los obtiene de S3. En este proyecto usa una dirección `cloudfront.net` y redirige HTTP a HTTPS.

Una **distribución** es la configuración de CloudFront que conecta la dirección pública con el origen S3. Su *ID* sirve para administrarla; su *dominio* sirve para abrir la aplicación. La URL `Location` devuelta al crear una invalidación es de la API de AWS, no de la página.

**Caché:** CloudFront puede guardar una copia temporal de archivos. Después de subir una versión nueva a S3 se puede crear una **invalidación** para que deje de usar copias anteriores. `/*` indica todas las rutas; la operación puede tardar unos minutos y no sustituye subir los archivos.

**Para mostrarlo:** CloudFront → Distributions. Se puede consultar el dominio con `terraform output -raw cloudfront_domain_name`.

### 4.3 Amazon Cognito: usuarios e inicio de sesión

Cognito administra el registro y la autenticación de usuarios. En el proyecto:

- Un **User Pool** agrupa las cuentas. Se usa el correo como identificador, con verificación automática de correo.
- La política configurada exige al menos 12 caracteres, además de mayúscula, minúscula, número y símbolo.
- Un **App Client** representa al frontend ante Cognito. No tiene secreto de cliente: el código del navegador es público y no puede proteger uno.
- El **dominio de Cognito** identifica la página administrada de inicio de sesión o *Hosted UI*.
- Las **callback URLs** y **logout URLs** son direcciones permitidas para regresar a la aplicación tras iniciar o cerrar sesión.

Al iniciar sesión, el navegador va a Cognito, el usuario se autentica y vuelve al frontend. La aplicación usa el flujo OAuth de código y administra la sesión con la biblioteca Amplify. Para operaciones privadas envía un **access token**, un tipo de credencial temporal. No deben compartirse capturas que muestren su valor.

**Autenticación** responde «¿quién es el usuario?». **Autorización** responde «¿puede realizar esta operación?». Cognito participa en la primera; API Gateway e IAM participan en distintas partes de la segunda.

**Para mostrarlo:** Cognito → User pools → `music-vault-dev-users`; después, revisar inicio de sesión, política de contraseñas, dominio y cliente de aplicación.

### 4.4 API Gateway: la entrada para las peticiones de datos

API Gateway expone la API mediante HTTPS. Una **ruta** combina un método y una dirección, por ejemplo:

| Ruta | Uso | Acceso |
|---|---|---|
| `GET /songs` | Consultar canciones | Público |
| `GET /me/favorites` | Consultar favoritos del usuario | Requiere token |
| `GET /me/library` | Consultar biblioteca del usuario | Requiere token |
| `PUT /me/favorites/{songId}` | Guardar una canción como favorita | Requiere token |

Para las rutas privadas, un **autorizador JWT** verifica el token antes de enviar la petición a Lambda. Si falta o no es válido, la petición se rechaza; una petición sin token normalmente recibe `401 Unauthorized`.

**CORS** es una configuración que indica a los navegadores desde qué orígenes pueden hacer solicitudes a la API. Un origen combina protocolo, dominio y, si aplica, puerto; por ejemplo, `https://ejemplo.cloudfront.net`. CORS **no sustituye la autenticación** ni impide por sí solo que un cliente fuera del navegador llame a la API.

**Para mostrarlo:** API Gateway → API del proyecto → rutas y autorizador; en la configuración de la API también puede revisarse CORS.

### 4.5 AWS Lambda: el código que atiende la petición

Lambda ejecuta código cuando recibe una invocación. En vez de mantener un servidor propio encendido, se empaqueta el backend de Python y AWS ejecuta el handler correspondiente.

| Función | Responsabilidad |
|---|---|
| `music-vault-dev-catalog` | Consultas públicas de catálogo y búsqueda. |
| `music-vault-dev-interactions` | Favoritos, calificaciones y reseñas. |
| `music-vault-dev-library` | Biblioteca personal. |

Las tres funciones comparten el código base empaquetado, pero usan distintos puntos de entrada y roles IAM. La aplicación valida los datos que recibe; en las operaciones personales obtiene la identidad del usuario a partir de los datos del token validado, no de un ID elegido en el cuerpo de la petición.

**Para mostrarlo:** Lambda → Functions → seleccionar una función y revisar configuración, monitorización y rol de ejecución.

### 4.6 Amazon DynamoDB: dónde se guardan los datos

DynamoDB es una base de datos NoSQL administrada. Este proyecto usa una tabla por entorno, normalmente `music-vault-dev-data`, para entidades del catálogo e interacciones. Funciona en modo **bajo demanda**: la capacidad no se reserva manualmente y los cargos dependen del uso y almacenamiento.

Un **ítem** es un registro y un **atributo** es un dato de ese registro. DynamoDB exige definir las claves, pero los demás atributos pueden variar entre ítems.

| Clave | Función | Ejemplo |
|---|---|---|
| `PK` | Clave de partición de la tabla: agrupa registros relacionados. | `USER#<sub>` |
| `SK` | Clave de orden de la tabla: distingue registros dentro de esa partición. | `FAVORITE#<songId>` |
| `GSI1PK` | Clave de partición de un índice secundario global. | `ENTITY#SONG` |
| `GSI1SK` | Clave de orden del índice; permite consultas ordenadas y por prefijo. | `<título-normalizado>#<id>` |

Por ejemplo, los favoritos de una persona se consultan con su `PK` de usuario y el prefijo `FAVORITE#` en `SK`. **GSI1** permite otras formas de consulta, como listar canciones o buscar por prefijo. No es un buscador de texto completo: encontrar una palabra en cualquier parte del título no es lo mismo que buscar por su inicio.

El script `seed_catalog.py` carga datos ficticios para pruebas. No crea usuarios de Cognito. Algunas filas de relación apoyan las consultas y no son canciones adicionales.

**Para mostrarlo:** DynamoDB → Tables → tabla → claves, índices y **Explore table items**. Recuerda que mostrar la tabla no demuestra por sí solo que las rutas privadas estén protegidas.

### 4.7 IAM: permisos para los servicios

IAM administra identidades y permisos en AWS. Un **rol** es una identidad que un servicio puede asumir; una **política** indica acciones permitidas y recursos sobre los que se permiten.

Cada Lambda tiene su propio rol. En la política definida por Terraform:

| Función | Acciones sobre DynamoDB |
|---|---|
| `catalog` | `GetItem`, `Query` |
| `interactions` | `GetItem`, `Query`, `PutItem`, `DeleteItem`, `UpdateItem` |
| `library` | `GetItem`, `Query`, `PutItem`, `DeleteItem` |

Estas acciones se limitan a la tabla del proyecto y sus índices. Cada rol también puede crear streams y enviar eventos al grupo de logs de su función. El principio es **mínimo privilegio**: conceder lo necesario para la tarea, no permisos generales a toda la cuenta. Para comprobar los permisos efectivos también hay que revisar si existen otras políticas o restricciones externas.

Además, una política de recursos autoriza a API Gateway a invocar cada Lambda. Es diferente del rol que permite a Lambda acceder a DynamoDB.

**Para mostrarlo:** Lambda → función → Configuración → Permisos → rol de ejecución → políticas en IAM.

### 4.8 CloudWatch: observar lo que ocurre

CloudWatch reúne **logs**, registros detallados de eventos, y **métricas**, números agregados en el tiempo, como invocaciones, errores y duración.

Terraform define el dashboard `music-vault-dev-overview`, que incluye gráficas de Lambda, API Gateway, DynamoDB y métricas propias `MusicVault`. Basta con tráfico de prueba para generar actividad; puede haber un retraso antes de verla. Una gráfica vacía no demuestra por sí misma que todo funcione.

En la configuración escolar **por defecto**, los logs Lambda se conservan siete días; las alarmas y los logs de acceso de API Gateway están desactivados. Son opciones configurables. El dashboard se crea independientemente de las alarmas. No afirmes que se probó una alarma si no se activó y comprobó.

**Para mostrarlo:** CloudWatch → Dashboards → `music-vault-dev-overview`; elige la última hora y genera algunas consultas a la app. Para logs, entra a Log groups y busca el grupo de la Lambda correspondiente.

## 5. Qué es Terraform y cómo se organiza

Terraform es una herramienta de **infraestructura como código**: en vez de configurar manualmente cada servicio, describimos la configuración deseada en archivos `.tf`. Terraform compara esa configuración con su estado y los recursos que administra, y propone cambios.

| Concepto | Qué significa en este proyecto |
|---|---|
| **Provider** | Complemento que permite a Terraform trabajar con AWS; `archive` prepara el paquete del backend. |
| **Resource** | Objeto que Terraform administra, como un bucket o una función Lambda. |
| **Module** | Carpeta que agrupa recursos relacionados, como `modules/cognito` o `modules/hosting`. |
| **Variable** | Valor configurable, como la región o `allowed_origins`. |
| **Output** | Dato que Terraform expone, como el dominio de CloudFront o la URL de la API. |
| **State / estado** | Archivo que relaciona la configuración con los recursos administrados. Aquí se usa estado local. |

Archivos importantes:

- `terraform/main.tf`: conecta los módulos y define los permisos para que API Gateway invoque las funciones.
- `terraform/variables.tf`: declara variables y valores predeterminados.
- `terraform/outputs.tf`: declara valores que necesitamos consultar después del despliegue.
- `terraform/versions.tf`: configura los proveedores y la versión mínima de Terraform.
- `terraform/modules/`: contiene las definiciones de cada grupo de servicios.
- `terraform/terraform.tfvars`: puede proporcionar valores locales. Otros archivos `*.auto.tfvars` también se cargan automáticamente y pueden sobrescribir valores de `terraform.tfvars`. Evita definir la misma variable en varios archivos sin saber cuál tiene prioridad.

### Comandos principales

Ejecutados desde la carpeta `terraform`:

| Comando | Acción |
|---|---|
| `terraform init` | Prepara el directorio y los proveedores necesarios. |
| `terraform validate` | Revisa la validez de la configuración; no demuestra que la aplicación funcione. |
| `terraform plan` | Muestra cambios propuestos sin aplicarlos. |
| `terraform apply` | Propone y aplica cambios tras confirmación. Pueden generar cargos. |
| `terraform output` | Muestra los outputs disponibles del estado. |
| `terraform destroy` | Propone eliminar recursos administrados y pide confirmación; puede borrar datos. |

El estado local puede contener información sensible. Consérvalo privado y no lo elimines mientras administras recursos. No lo compartan ni ejecuten cambios simultáneos sin coordinación; para trabajo conjunto se necesita una estrategia adecuada de estado remoto y bloqueo.

## 6. Recorridos para explicar en la presentación

### A. Una persona abre la página

1. El navegador solicita el dominio de CloudFront por HTTPS.
2. CloudFront entrega los archivos del frontend desde caché o los obtiene del bucket S3 privado.
3. El navegador ejecuta React y muestra la interfaz.

**Idea clave:** S3 almacena los archivos; CloudFront los entrega. Ninguno reemplaza a la base de datos.

### B. Una persona consulta canciones

1. React solicita `GET /songs` a API Gateway; no necesita inicio de sesión.
2. API Gateway envía la solicitud a la Lambda `catalog`.
3. Lambda consulta DynamoDB y devuelve una respuesta JSON.
4. React presenta los resultados; pueden estar vacíos si no hay catálogo cargado.

**Idea clave:** la página y los datos recorren caminos diferentes.

### C. Una persona inicia sesión y consulta favoritos

1. La aplicación redirige a la pantalla de Cognito.
2. Tras autenticarse, Cognito devuelve al navegador a una URL de retorno permitida y se establece la sesión.
3. React solicita `GET /me/favorites` y envía el access token en `Authorization`.
4. API Gateway valida el token. Si es aceptado, invoca `interactions`.
5. Lambda usa el identificador `sub` del usuario validado para consultar sus favoritos en DynamoDB.
6. La respuesta llega a React, que muestra la lista.

**Idea clave:** la identidad usada para los datos privados proviene del token validado, no de un usuario indicado libremente por quien llama.

## 7. Cómo se publica el frontend

La secuencia completa y comandos están en [Configuración y despliegue](./configuracion-y-despliegue.md). En términos generales:

1. Terraform crea la infraestructura. En el primer despliegue se obtiene el dominio de CloudFront después del primer `apply`.
2. Se agrega el origen `https://<dominio>` **sin barra final** a `allowed_origins` y se hace otro `apply`: se actualizan CORS y las URL permitidas de Cognito. Terraform añade la barra final a estas últimas.
3. Se configuran en `frontend/.env.production.local` la URL de la API, identificadores y dominio de Cognito, y URLs de retorno y salida. Estas últimas deben coincidir exactamente con las registradas en Cognito.
4. `npm run build` incorpora las variables `VITE_` al frontend. Son **públicas**: nunca deben contener contraseñas ni claves de AWS.
5. Se sincroniza `dist` al bucket S3 y se invalida CloudFront para que deje de entregar archivos antiguos.
6. Se abre la URL de CloudFront y se comprueban catálogo, inicio de sesión y rutas privadas.

Si cambia el dominio de CloudFront, hay que actualizar los orígenes y las URLs del frontend y volver a construirlo y publicarlo. No se requieren dos `apply` por cada cambio visual; se vuelve a aplicar Terraform cuando cambia la infraestructura.

## 8. Demostraciones y evidencia

No es necesario causar errores reales ni tener muchos usuarios. Registrar solo lo que se haya comprobado.

| Qué demostrar | Cómo | Qué sí demuestra |
|---|---|---|
| Página publicada | Abrir el dominio CloudFront. | Que el navegador recibió la interfaz. |
| API pública | Consultar `GET /songs` desde la app o terminal. | Que esa ruta respondió; una lista vacía puede ser válida. |
| Ruta privada sin sesión | Solicitar `GET /me/favorites` sin token y observar `401`. | Que esa petición fue rechazada; por sí solo no prueba ausencia de invocación Lambda. |
| Ruta privada con sesión | Iniciar sesión y revisar la respuesta de favoritos en Network. | Que esa petición autenticada respondió; ocultar el token en la evidencia. |
| Base de datos | Mostrar claves, `GSI1` y algunos ítems en DynamoDB. | La configuración y los datos visibles en ese momento. |
| Permisos | Mostrar rol y políticas de cada Lambda en IAM. | Las políticas que se revisaron; comprobar también si hay otras. |
| Observabilidad | Generar tráfico y abrir el dashboard de CloudWatch. | Las métricas efectivamente visibles durante el intervalo elegido. |

Para explorar la API sin autenticación, desde `frontend`:

```powershell
$api = terraform "-chdir=..\terraform" output -raw api_base_url
curl.exe -i "$api/songs"
curl.exe -i "$api/me/favorites"
```

Se espera que la primera responda con el catálogo y la segunda con `401`. Verifica los resultados reales antes de reportarlos. Evita capturar tokens, correos de usuarios o credenciales.

## 9. Preguntas frecuentes para el equipo

**¿Por qué usar S3 y CloudFront juntos?** S3 guarda los archivos; CloudFront los distribuye por HTTPS y usa caché. El bucket no necesita ser público.

**¿Cognito guarda las canciones?** No. Administra usuarios y autenticación; los datos de la aplicación están en DynamoDB.

**¿Por qué usar tres Lambdas?** Separan responsabilidades y permiten dar permisos diferentes. Cada una atiende varias rutas relacionadas.

**¿Por qué IAM si ya usamos Cognito?** Cognito autentica a personas que usan la app; IAM controla, entre otras cosas, qué recursos AWS puede usar cada Lambda.

**¿Qué pasa si alguien no envía token en una ruta privada?** API Gateway debe rechazar la petición antes de enviarla a Lambda. Se puede probar con una solicitud sin `Authorization`; revisar logs o métricas ayuda a estudiar las invocaciones.

**¿DynamoDB tiene tablas como SQL?** Tiene tablas, pero es NoSQL: aquí usamos una sola tabla con distintos tipos de ítems y claves diseñadas para las consultas de la aplicación.

**¿Por qué no se ven datos en alguna gráfica?** Puede no haber ocurrido ese tipo de operación, el intervalo puede ser incorrecto o los datos pueden tardar en aparecer. Revisa antes de concluir que hay un error.

**¿Está lista para producción?** Es una configuración escolar de bajo costo. Antes de usar datos importantes se deben evaluar, entre otros, respaldos y restauración, alarmas, protección contra abuso, manejo de estado compartido y procedimientos operativos.

**¿Qué pasa al destruir la infraestructura?** `terraform destroy` puede eliminar recursos y datos, incluida la tabla. Algunos recursos, como un bucket con objetos, pueden impedir que termine. Antes de destruir, revisa el plan, conserva los datos necesarios y cuenta con autorización.

## 10. Guion breve para presentar

1. «La interfaz React se publica en S3 y se entrega por CloudFront con HTTPS».
2. «El catálogo se consulta a través de API Gateway, una función Lambda y DynamoDB».
3. «Para favoritos y biblioteca, Cognito autentica al usuario y API Gateway valida el token».
4. «Cada Lambda usa un rol IAM con permisos limitados; CloudWatch permite observar el tráfico y errores».
5. «Terraform documenta y administra los recursos. Usamos una configuración de desarrollo con costos y funciones opcionales que debemos revisar».

Pueden acompañar cada punto con una captura de la consola o una prueba real, indicando qué se comprobó y qué no.
