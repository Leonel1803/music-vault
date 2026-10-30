# Modelo de datos DynamoDB

## Tabla única

Una tabla por ambiente, modo on-demand, clave primaria `PK` (partition key) + `SK` (sort key). `GSI1` y `GSI2` sostienen los patrones de consulta. Los atributos de índice se omiten cuando no aplican.

| Tipo | PK | SK | GSI1PK / GSI1SK | Datos principales |
|---|---|---|---|---|
| Artista | `ARTIST#<artistId>` | `METADATA` | `ENTITY#ARTIST` / `<nombre-normalizado>#<id>` | `name`, `bio`, `imageUrl` |
| Álbum | `ALBUM#<albumId>` | `METADATA` | `ENTITY#ALBUM` / `<título-normalizado>#<id>` | `title`, `artistId`, `releaseDate`, `coverUrl` |
| Canción | `SONG#<songId>` | `METADATA` | `ENTITY#SONG` / `<título-normalizado>#<id>` | `title`, `albumId`, `artistId`, `genre`, `durationSeconds` |
| Canción por género | `GENRE#<género-normalizado>` | `SONG#<id>` | `GENRE#<género-normalizado>` / `<título-normalizado>#<id>` | Proyección de canción; permite lista y filtro de prefijo por género |
| Favorito/biblioteca | `USER#<sub>` | `FAVORITE#<songId>` o `LIBRARY#<songId>` | `GSI2PK=USER#<sub>#FAVORITES/LIBRARY`, `GSI2SK=<fecha>#<songId>` | `songId`, `createdAt` |
| Álbumes de un artista | `ARTIST#<artistId>` | `ALBUM#<albumId>` | — | Resumen del álbum (relación) |
| Canciones de un álbum | `ALBUM#<albumId>` | `SONG#<songId>` | — | Resumen de la canción (relación) |
| Calificación | `SONG#<songId>` | `RATING#<sub>` | — | `rating` (1–5); el `METADATA` de la canción guarda `ratingSum` y `ratingCount` (se actualizan con `UpdateItem ADD`) |
| Reseña | `SONG#<songId>` | `REVIEW#<sub>` | — | `text`, `authorName`, `createdAt`, `updatedAt` |

La API nunca devuelve `PK`, `SK`, `GSI1PK` ni `GSI1SK`; `ratingSum/ratingCount` se exponen como `ratingAverage` y `ratingCount`. `seed_catalog.py` escribe las filas de relación y acepta `--data archivo.json` para cargar más catálogo.

Para evitar duplicar metadatos de canción en una sola clave, el índice de género se modela como item de relación en la misma tabla: `PK=GENRE#...`, `SK=SONG#...`, con los atributos de resumen necesarios para presentar el listado. La escritura de catálogo debe mantener el ítem `SONG` y la relación de género juntos mediante `TransactWriteItems` o proceso idempotente.

## Patrones de acceso

1. Detalle de entidad: `GetItem(PK=<tipo>#id, SK=METADATA)`.
2. Lista/búsqueda por prefijo: `Query(GSI1PK=ENTITY#tipo, begins_with(GSI1SK, prefijo))`.
3. Lista por género: `Query(GSI1PK=GENRE#género, begins_with(GSI1SK, prefijo-opcional))`.
4. Favoritos/biblioteca: `Query(GSI2PK=USER#sub#tipo)`.
5. Cambiar favorito/biblioteca: `PutItem`/`DeleteItem` con clave `USER#sub` y prefijo del tipo.

## Reglas y evolución

- Los IDs son estables y se generan en proceso de carga/administración del catálogo.
- `normalizedName` se normaliza al escribir. La lectura no realiza `Scan`; toda colección debe usar `Query` con clave/índice.
- La clave `sub` jamás se recibe del body; proviene del JWT validado por API Gateway.
- Límite de página: máximo 100; cursor basado en `ExclusiveStartKey`.
- Ítems de rating/review están documentados como fase siguiente. Antes de agregarlos, fijar transacciones para promedio y conteo, GSI para consulta por canción, TTL solo si hay una política de retención aprobada.
- DynamoDB usa cifrado administrado por AWS. PITR y alarmas son opcionales y se dejan desactivados por defecto en el entorno escolar para evitar costos recurrentes adicionales; actívalos antes de almacenar datos importantes.
