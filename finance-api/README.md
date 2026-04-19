# Finance API

API REST para gestión de transacciones financieras personales (ingresos y egresos).
Datos almacenados en memoria.

## Stack

- [Hono](https://hono.dev/) sobre **Node.js**
- **TypeScript**
- Package manager: **yarn**

## Requisitos

- Node.js 18 o superior
- Yarn 1.x

## Instalación

```bash
cd finance-api
yarn install
```

## Scripts

```bash
yarn dev         # arranca el server en modo watch (tsx)
yarn build       # compila a dist/
yarn start       # ejecuta dist/index.js
yarn typecheck   # validación de tipos sin emitir
```

El servidor escucha en `http://localhost:3000` (o `PORT` del entorno).

## Modelo

```ts
type Transaction = {
  id: number
  description: string
  amount: number
  type: 'income' | 'expense'
}
```

## Endpoints

| Método | Ruta                | Descripción                     |
| ------ | ------------------- | ------------------------------- |
| GET    | `/transactions`     | Listar todas las transacciones  |
| GET    | `/transactions/:id` | Obtener una transacción por id  |
| POST   | `/transactions`     | Crear una nueva transacción     |
| PUT    | `/transactions/:id` | Actualizar una transacción      |
| DELETE | `/transactions/:id` | Eliminar una transacción        |

### Request body (POST / PUT)

```json
{
  "description": "Sueldo abril",
  "amount": 1500000,
  "type": "income"
}
```

### Ejemplos con curl

```bash
# Crear
curl -X POST http://localhost:3000/transactions \
  -H "Content-Type: application/json" \
  -d '{"description":"Sueldo","amount":1500000,"type":"income"}'

# Listar
curl http://localhost:3000/transactions

# Obtener por id
curl http://localhost:3000/transactions/1

# Actualizar
curl -X PUT http://localhost:3000/transactions/1 \
  -H "Content-Type: application/json" \
  -d '{"description":"Sueldo abril","amount":1600000,"type":"income"}'

# Eliminar
curl -X DELETE http://localhost:3000/transactions/1
```

## Estructura

```
finance-api/
  src/
    index.ts                    # Entrypoint Hono + @hono/node-server
    routes/
      transactions.ts           # CRUD endpoints
    store/
      transactionStore.ts       # Estado en memoria
    types/
      transaction.ts            # Tipos de dominio
  package.json
  tsconfig.json
  .gitignore
```
