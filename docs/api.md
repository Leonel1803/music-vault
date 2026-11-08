# Contrato REST

Base local/de despliegue: `VITE_API_BASE_URL` (sin `/` final). Formato JSON UTF-8. Todas las rutas responden `Cache-Control: no-store`; catálogo podrá habilitar caché pública en una fase posterior.

## Autenticación

Las rutas `/me/*` requieren `Authorization: Bearer <Cognito access token>`. API Gateway valida JWT. El backend usa exclusivamente `requestContext.authorizer.jwt.claims.sub` como propietario.

## Endpoints del MVP

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/artists` | No | Lista artistas. Query: `q`, `limit`, `cursor`. |
| GET | `/artists/{artistId}` | No | Detalle de artista. |
| GET | `/albums` | No | Lista álbumes. Query: `q`, `limit`, `cursor`. |
| GET | `/albums/{albumId}` | No | Detalle de álbum. |
| GET | `/songs` | No | Lista canciones. Query: `genre`, `q`, `limit`, `cursor`. |
| GET | `/songs/{songId}` | No | Detalle de canción. |
| GET | `/search` | No | Busca prefijos en artistas, álbumes y canciones. Query: `q`, `genre` (opcional, limita solo canciones), `limit`. |
| GET | `/artists/{artistId}/albums` | No | Álbumes de un artista. |
| GET | `/albums/{albumId}/songs` | No | Canciones de un álbum. |
| GET | `/songs/{songId}/reviews` | No | Reseñas de una canción (paginado). Muestra `authorName`, `text` y fechas; nunca el `sub`. |
| GET | `/me/ratings/{songId}` | Sí | Tu calificación (`item` o `null`). |
| PUT | `/me/ratings/{songId}` | Sí | Body `{"rating": 1-5}`. Una por usuario; devuelve `ratingAverage` y `ratingCount`. |
| DELETE | `/me/ratings/{songId}` | Sí | Quita tu calificación. |
| GET | `/me/reviews/{songId}` | Sí | Tu reseña. |
| PUT | `/me/reviews/{songId}` | Sí | Body `{"text": 1-1000 caracteres, "authorName": opcional, máx. 40}`. |
| DELETE | `/me/reviews/{songId}` | Sí | Elimina tu reseña. |
| GET | `/me/favorites` | Sí | Lista favoritos. |
| PUT | `/me/favorites/{songId}` | Sí | Marca favorito; idempotente. |
| DELETE | `/me/favorites/{songId}` | Sí | Quita favorito; idempotente. |
| GET | `/me/library` | Sí | Lista canciones guardadas. |
| PUT | `/me/library/{songId}` | Sí | Agrega canción; idempotente. |
| DELETE | `/me/library/{songId}` | Sí | Elimina canción; idempotente. |

## Paginación

Listados aceptan `limit` entero de 1 a 100 (predeterminado 25) y `cursor` opaco. La respuesta es:

```json
{
  "items": [],
  "nextCursor": null
}
```

`nextCursor` es Base64 URL-safe de `LastEvaluatedKey`. El backend rechaza cursores inválidos. Clientes deben tratarlo como opaco y volver a enviarlo sin modificar.

## Búsqueda y género

`q` se recorta y normaliza a minúsculas; consulta prefijos de nombre indexados. Se requiere un mínimo de 2 caracteres. Búsqueda global en UI combina consultas de artistas, álbumes y canciones. `genre` se compara por igualdad normalizada. No se soportan subcadenas ni búsqueda tolerante a errores.

La ruta `/search` es una búsqueda acotada del MVP: `limit` limita la respuesta combinada, no ofrece cursor de continuación todavía. Los listados por entidad sí usan paginación completa.

Los elementos de `/search` incluyen `entityType` (`artists`, `albums` o `songs`) y `displayName` para que el cliente pueda distinguir el tipo de coincidencia.

## Errores

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "El parámetro limit debe estar entre 1 y 100."
  }
}
```

| HTTP | Código | Uso |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Query, ruta, cursor o JSON inválidos. |
| 401 | `UNAUTHORIZED` | Claim `sub` ausente en ruta privada (normalmente API Gateway responde antes). |
| 404 | `NOT_FOUND` | Entidad de catálogo inexistente. |
| 500 | `INTERNAL_ERROR` | Error no esperado; detalle solo en logs, nunca al cliente. |

## Ejemplos

```http
GET /songs?genre=Jazz&limit=25
GET /songs?q=blue&cursor=eyJQS1...
PUT /me/favorites/song-123
Authorization: Bearer <token>
```

Para marcar/quitar favoritos y biblioteca, el cuerpo de `PUT` es vacío. La escritura de calificación y de su agregado son operaciones DynamoDB separadas, por lo que un fallo entre ambas puede dejar el promedio y conteo temporalmente inconsistentes; véase [modelo de datos](./modelo-de-datos.md).
