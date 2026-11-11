# Cómo leer el lenguaje de Terraform en Music Vault

Esta guía está dirigida al equipo que tiene que explicar el código de infraestructura y apenas empieza con Terraform. Usa ejemplos del proyecto; los valores como `music-vault-dev` son ilustrativos y dependen de la configuración aplicada.

Para entender los servicios de AWS y sus conexiones, consulta [Infraestructura para principiantes](./infraestructura-para-principiantes.md). Para ejecutar el despliegue, consulta [Configuración y despliegue](./configuracion-y-despliegue.md).

## 1. ¿Qué lenguaje usa Terraform?

Los archivos con extensión `.tf` usan **HCL** (*HashiCorp Configuration Language*). HCL permite declarar cómo queremos que sea la infraestructura: qué recursos existen, sus propiedades y cómo se relacionan.

La idea principal es **declarativa**:

```hcl
billing_mode = "PAY_PER_REQUEST"
```

Esta línea expresa el modo deseado para un recurso, no una instrucción paso a paso para hacer clic en la consola. Terraform calcula las operaciones necesarias al preparar el plan.

Un archivo `.tfvars` también usa sintaxis de HCL, pero se emplea para **asignar valores a variables**. No es lo mismo declarar una variable que darle un valor.

## 2. Cómo leer un bloque

En [`terraform/modules/dynamodb/main.tf`](../terraform/modules/dynamodb/main.tf) encontramos:

```hcl
resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"
}
```

El ejemplo omite el resto de la configuración de la tabla. Léelo así:

1. `resource` indica que se declara un recurso administrado por Terraform.
2. `"aws_dynamodb_table"` indica el **tipo de recurso**, proporcionado por el provider de AWS.
3. `"this"` es el **nombre local en Terraform**, no necesariamente el nombre visible de la tabla en AWS.
4. `{ ... }` delimita el cuerpo del bloque.
5. Cada línea `nombre = valor` asigna un **argumento**: por ejemplo, `hash_key = "PK"`.
6. `var.table_name` es una **referencia** a una variable, no el texto literal `"var.table_name"`.

Si `var.table_name` vale `music-vault-dev-data`, ese será el valor que reciba `name`. En el módulo, el recurso puede referenciarse como `aws_dynamodb_table.this`; los módulos tienen su propio espacio de nombres.

### Bloques dentro de bloques

El recurso también contiene bloques anidados:

```hcl
attribute {
  name = "PK"
  type = "S"
}
```

Este bloque describe un atributo clave de la tabla; `"S"` indica tipo string en DynamoDB. Su significado y los argumentos permitidos dependen del tipo de recurso y del provider. HCL aporta la sintaxis; el provider define qué configuraciones entiende.

Los comentarios empiezan, por ejemplo, con `#`:

```hcl
# Una aclaración para las personas que leen el código.
```

## 3. Tipos de valores

| Tipo | Ejemplo | Uso |
|---|---|---|
| Texto o `string` | `"us-east-2"` | Región, nombres, rutas. |
| Número | `7` | Por ejemplo, días de retención. |
| Booleano | `true` o `false` | Activar o desactivar una opción. No lleva comillas. |
| Lista | `["http://localhost:5173", "https://ejemplo.cloudfront.net"]` | Varios valores ordenados. |
| Objeto o mapa | `{ catalog = "lectura", library = "biblioteca" }` | Valores asociados a nombres o claves. |
| Valor nulo | `null` | Ausencia de valor; su efecto depende del argumento. |

`false` es un booleano; `"false"` es texto. Los corchetes `[]` agrupan elementos de una colección y las llaves `{}` pueden delimitar un bloque o un valor de tipo objeto, según el contexto.

## 4. Variables: declarar, asignar y usar

### 4.1 Declaración en `variables.tf`

En [`terraform/variables.tf`](../terraform/variables.tf) aparece:

```hcl
variable "environment" {
  type        = string
  description = "Ambiente aislado: dev, test o prod."
  default     = "dev"
}
```

- `variable "environment"` declara la entrada.
- `type = string` indica que espera texto; `string` es un tipo, no un valor de texto.
- `description` documenta su propósito.
- `default = "dev"` proporciona un valor si no se asigna otro de mayor prioridad.

Algunas variables no tienen `default`, como `cognito_domain_prefix`; hay que proporcionarles un valor de otra manera.

### 4.2 Asignación en un archivo `.tfvars`

El ejemplo del proyecto, [`terraform.tfvars.example`](../terraform/terraform.tfvars.example), contiene asignaciones como:

```hcl
project_name = "music-vault"
environment  = "dev"
aws_region   = "us-east-2"
```

Estos valores no crean recursos por sí solos. Se usan al evaluar los archivos `.tf`. El archivo de ejemplo no se carga automáticamente como variables: se copia y configura según la guía de despliegue.

Terraform carga automáticamente `terraform.tfvars` y archivos terminados en `.auto.tfvars`. Si la misma variable aparece en ambos, el valor de `.auto.tfvars` prevalece sobre el de `terraform.tfvars`; cuando hay varios archivos automáticos, se procesan en orden léxico. También existen valores desde variables de entorno `TF_VAR_...` y opciones `-var` / `-var-file`; las opciones de línea de comandos tienen prioridad sobre los archivos automáticos. Eviten duplicar valores para no confundirse.

### 4.3 Uso con `var.`

En el módulo raíz, `var.environment` significa «valor de la variable `environment` de este módulo». Cada módulo declara sus propias variables: las variables del módulo raíz no aparecen automáticamente dentro de un módulo hijo, hay que pasarlas como argumentos.

Por ejemplo:

```hcl
module "cognito" {
  source = "./modules/cognito"
  name   = local.name
  # Se omiten los demás argumentos.
}
```

Aquí el módulo raíz pasa el valor de `local.name` a la entrada `name` del módulo Cognito. Dentro de ese módulo se usa como `var.name`.

## 5. Valores locales e interpolación de texto

En [`terraform/main.tf`](../terraform/main.tf):

```hcl
locals {
  name = "${var.project_name}-${var.environment}"
}
```

`locals` define valores calculados dentro del módulo. `${...}` inserta el resultado de una expresión dentro de un texto. Si `project_name` vale `music-vault` y `environment` vale `dev`:

```text
local.name → music-vault-dev
```

Luego se puede construir otro texto:

```hcl
table_name = "${local.name}-data"
```

Resultado con esos valores: `music-vault-dev-data`. Los valores locales son distintos de las variables de entrada: se calculan a partir de expresiones de la configuración, en lugar de asignarlos directamente en `.tfvars`.

## 6. Referencias y dependencias

Un valor puede venir de una variable, un local, un recurso, un módulo o una fuente de datos:

| Expresión | Cómo leerla |
|---|---|
| `var.environment` | Variable `environment` del módulo actual. |
| `local.name` | Valor local `name` del módulo actual. |
| `aws_dynamodb_table.this.arn` | Atributo `arn` del recurso `this` en el módulo actual. |
| `module.dynamodb.table_arn` | Output `table_arn` del módulo hijo `dynamodb`. |
| `data.archive_file.backend.output_path` | Atributo de la fuente de datos `archive_file.backend`. |

Por ejemplo, el módulo Lambda recibe el ARN que entrega el módulo DynamoDB:

```hcl
table_arn = module.dynamodb.table_arn
```

Esta referencia también ayuda a Terraform a **inferir una dependencia**: necesita el valor de la tabla para configurar lo que lo utiliza. Terraform construye un grafo de dependencias; no depende solo del orden visual de los bloques en los archivos.

En algunos casos se usa una dependencia explícita:

```hcl
depends_on = [aws_cloudwatch_log_group.lambda, aws_iam_role_policy.lambda]
```

El proyecto la usa en el recurso Lambda para indicar que depende también de esos recursos. `depends_on` no reemplaza los argumentos y referencias necesarios; se usa cuando la dependencia no queda suficientemente expresada por los valores.

Algunos valores no se conocen hasta el `apply`. El plan puede mostrarlos como **`(known after apply)`**: significa que Terraform aún no puede mostrar el valor, no necesariamente que haya un error.

## 7. Módulos: pasar datos entre carpetas

Un módulo es una agrupación de archivos Terraform. La carpeta `terraform` es el **módulo raíz**; `terraform/modules/dynamodb` es un módulo hijo.

Fragmento real del módulo raíz:

```hcl
module "dynamodb" {
  source                        = "./modules/dynamodb"
  table_name                    = "${local.name}-data"
  enable_point_in_time_recovery = var.enable_point_in_time_recovery
}
```

1. `module "dynamodb"` le da un nombre local a esta instancia del módulo.
2. `source` indica dónde está su código.
3. `table_name` y `enable_point_in_time_recovery` pasan valores a las variables declaradas por el módulo hijo.
4. El módulo hijo usa esos valores al configurar la tabla.
5. Sus outputs permiten que el módulo raíz entregue resultados a otros módulos.

El módulo no es un servicio adicional de AWS: es una forma de organizar el código Terraform.

## 8. Outputs: devolver valores útiles

En [`terraform/outputs.tf`](../terraform/outputs.tf):

```hcl
output "cloudfront_domain_name" {
  description = "Dominio HTTPS de distribución CloudFront."
  value       = module.hosting.cloudfront_domain_name
}
```

El bloque expone en el módulo raíz un valor recibido del módulo `hosting`. Después de aplicar la infraestructura se puede consultar desde `terraform`:

```powershell
terraform output -raw cloudfront_domain_name
```

`-raw` imprime el texto directamente, sin el formato de representación habitual de Terraform. El dominio no es lo mismo que el ID de la distribución; el proyecto expone ambos.

Los outputs dependen del estado actual. No es adecuado publicarlos indiscriminadamente: algunos proyectos pueden tener outputs sensibles, y el estado también puede contener datos sensibles.

## 9. Colecciones, `for` y condiciones

### 9.1 Transformar una lista con `for`

El módulo raíz forma las direcciones para Cognito:

```hcl
callback_urls = [for origin in var.allowed_origins : "${origin}/"]
```

Se lee: «para cada `origin` de `allowed_origins`, crea un texto con ese origen y una barra al final». Ejemplo:

```text
Entrada: ["http://localhost:5173", "https://ejemplo.cloudfront.net"]
Salida:  ["http://localhost:5173/", "https://ejemplo.cloudfront.net/"]
```

Esto construye una lista; no ejecuta una petición web. Por eso los orígenes del proyecto se escriben sin barra final y las URLs de Cognito resultantes incluyen una.

### 9.2 Elegir un valor con una condición

En el módulo API Gateway se usa una expresión condicional:

```hcl
authorization_type = each.value.auth ? "JWT" : "NONE"
```

La estructura es `condición ? valor_si_verdadero : valor_si_falso`. Para una ruta cuyo `auth` sea `true` se usa `"JWT"`; para una pública con `false`, `"NONE"`. Una condición elige un valor: no es una instrucción `if` tradicional con líneas que se ejecutan una por una.

## 10. `for_each` y `count`: varias instancias

### 10.1 `for_each` por nombre

En el módulo Lambda se define un mapa local de funciones, abreviado aquí:

```hcl
locals {
  functions = {
    catalog = {
      handler = "src.handler.catalog_lambda_handler"
      actions = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    # También se definen interactions y library.
  }
}
```

Luego un bloque de rol lo utiliza:

```hcl
resource "aws_iam_role" "lambda" {
  for_each = local.functions
  name     = "${var.name}-${each.key}-lambda"
  # Se omite la política de confianza.
}
```

Terraform crea una instancia del rol por cada clave del mapa. Por ejemplo, para la entrada `catalog`:

- `each.key` vale `catalog`.
- `each.value` contiene el objeto asociado, incluidos `handler` y `actions`.
- Si `var.name` vale `music-vault-dev`, el nombre del rol resulta `music-vault-dev-catalog-lambda`.

Cada instancia tiene una dirección Terraform identificada por su clave, como `aws_iam_role.lambda["catalog"]`. Una referencia como `aws_iam_role.lambda[each.key].arn` selecciona el rol correspondiente a esa misma clave.

### 10.2 `count` para una cantidad

En CloudWatch, la suscripción de correo usa:

```hcl
count = local.alarms_on && var.alarm_email != "" ? 1 : 0
```

`&&` significa «y» y `!=` significa «es distinto de». Si las alarmas están activadas **y** el correo no está vacío, el resultado es `1`; de lo contrario es `0`. Así se solicita una instancia o ninguna. Las instancias con `count` se identifican con índices numéricos, como `[0]`.

## 11. Funciones incorporadas y fuentes de datos

### Funciones

Las funciones reciben valores y producen otro valor. Por ejemplo:

```hcl
lambda_names = values(module.lambda.function_names)
```

`values(...)` obtiene los valores del mapa de nombres de funciones. Otra función usada en IAM es `jsonencode(...)`, que convierte un valor de Terraform en una cadena JSON para la política:

```hcl
assume_role_policy = jsonencode({
  Version = "2012-10-17"
  # Se omiten los statements.
})
```

No hace falta escribir las comillas y escapes de todo el documento JSON manualmente.

### Fuentes de datos

Una declaración `data` obtiene o calcula información mediante un provider. En el módulo Lambda:

```hcl
data "archive_file" "backend" {
  type       = "zip"
  source_dir = var.source_dir
  # Se omiten otras opciones.
}
```

Esta fuente, del provider `archive`, empaqueta el backend; no es una función Lambda ni un recurso de AWS. Sus resultados se usan mediante expresiones como `data.archive_file.backend.output_path`.

## 12. Providers y versiones

En [`terraform/versions.tf`](../terraform/versions.tf):

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

- `required_version` restringe la versión de Terraform CLI.
- `required_providers` indica los complementos y sus restricciones de versión.
- `~> 5.0` permite versiones desde `5.0` hasta antes de `6.0`, no cualquier versión.
- El bloque `provider "aws"` configura el provider, incluida la región, usando `var.aws_region`.

Terraform instala providers durante `terraform init`. El archivo de bloqueo de dependencias registra selecciones y verificaciones; no es lo mismo que el estado de infraestructura.

## 13. Del código a los recursos: ciclo de trabajo

1. **Configuración:** escribimos los bloques y definimos valores de variables.
2. **`terraform init`:** prepara el directorio, módulos y providers.
3. **`terraform validate`:** verifica la configuración sin demostrar que el despliegue o la aplicación funcionen.
4. **`terraform plan`:** consulta información necesaria, compara la configuración con el estado y recursos administrados, y propone cambios. No aplica esos cambios.
5. **`terraform apply`:** ejecuta el plan tras confirmación y actualiza el estado. Puede crear, modificar o eliminar recursos.
6. **`terraform output`:** muestra valores guardados en el estado.

El plan puede mostrar `+` para creación, `~` para cambios y `-` para eliminación; algunas modificaciones requieren reemplazar un recurso. Lee el detalle y el resumen antes de confirmar. `0 added, 0 changed, 0 destroyed` significa que ese plan no tenía cambios que aplicar; si esperaban cambios, comprueben los valores y archivos de variables que se están usando.

`terraform.tfstate` es el registro local de qué recursos administra Terraform y sus atributos. **No lo borren para «empezar de nuevo»**: eso no borra los recursos de AWS y puede dificultar administrarlos. Tampoco es un respaldo de los datos de DynamoDB.

## 14. Practicar sin cambiar infraestructura

Desde PowerShell, ubicados en la carpeta `terraform`:

```powershell
terraform fmt -check -recursive
terraform validate
terraform output
```

`fmt -check` comprueba formato sin reescribir los archivos. `validate` requiere un directorio inicializado; `output` necesita un estado que contenga esos valores.

Para evaluar expresiones con los valores disponibles:

```powershell
"var.allowed_origins" | terraform console
"local.name" | terraform console
```

`terraform console` evalúa expresiones; no aplica cambios. Puede requerir inicialización, configuración de variables y acceso al estado o providers según la expresión. No compartan salidas sensibles.

## 15. Ejercicio para exponer

Sigan este recorrido en el código:

1. En [`variables.tf`](../terraform/variables.tf), encuentren la declaración de `project_name` y su valor por defecto.
2. En [`main.tf`](../terraform/main.tf), expliquen cómo `locals` combina proyecto y entorno.
3. En el mismo archivo, señalen cómo el módulo DynamoDB recibe `table_name`.
4. En [`modules/dynamodb/main.tf`](../terraform/modules/dynamodb/main.tf), muestren cómo la variable se asigna al `name` de la tabla y dónde están las claves.
5. Expliquen que el output del módulo DynamoDB pasa el ARN al módulo Lambda y permite establecer permisos.
6. Abran [`outputs.tf`](../terraform/outputs.tf) y expliquen por qué el dominio de CloudFront se puede consultar con `terraform output`.

**Frase para la presentación:** «Terraform usa HCL para declarar recursos. Pasamos variables a módulos, los conectamos mediante referencias y outputs, y revisamos el plan antes de aplicar cambios. El estado registra los recursos administrados».
