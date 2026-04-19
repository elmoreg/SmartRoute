import { serve } from '@hono/node-server'
import { Hono } from 'hono'
import transactions from './routes/transactions.js'

const app = new Hono()

app.get('/', (c) =>
  c.json({
    name: 'finance-api',
    description: 'Personal financial transactions API',
    endpoints: {
      list: 'GET /transactions',
      get: 'GET /transactions/:id',
      create: 'POST /transactions',
      update: 'PUT /transactions/:id',
      remove: 'DELETE /transactions/:id',
    },
  }),
)

app.route('/transactions', transactions)

app.notFound((c) => c.json({ error: 'Not found' }, 404))

app.onError((err, c) => {
  console.error(err)
  return c.json({ error: 'Internal server error' }, 500)
})

const port = Number(process.env.PORT ?? 3000)

serve({ fetch: app.fetch, port }, (info) => {
  console.log(`finance-api listening on http://localhost:${info.port}`)
})

export default app
