import { Hono } from 'hono'
import type { TransactionInput, TransactionType } from '../types/transaction.js'
import {
  createTransaction,
  deleteTransaction,
  getTransaction,
  listTransactions,
  updateTransaction,
} from '../store/transactionStore.js'

const transactions = new Hono()

const parseId = (raw: string): number | null => {
  const id = Number(raw)
  if (!Number.isInteger(id) || id <= 0) return null
  return id
}

const parseBody = (body: unknown): TransactionInput | string => {
  if (typeof body !== 'object' || body === null) {
    return 'Body must be a JSON object'
  }
  const { description, amount, type } = body as Record<string, unknown>

  if (typeof description !== 'string' || description.trim() === '') {
    return 'description must be a non-empty string'
  }
  if (typeof amount !== 'number' || !Number.isFinite(amount)) {
    return 'amount must be a finite number'
  }
  if (type !== 'income' && type !== 'expense') {
    return "type must be 'income' or 'expense'"
  }

  return {
    description: description.trim(),
    amount,
    type: type as TransactionType,
  }
}

transactions.get('/', (c) => {
  return c.json(listTransactions())
})

transactions.get('/:id', (c) => {
  const id = parseId(c.req.param('id'))
  if (id === null) return c.json({ error: 'Invalid id' }, 400)
  const transaction = getTransaction(id)
  if (!transaction) return c.json({ error: 'Transaction not found' }, 404)
  return c.json(transaction)
})

transactions.post('/', async (c) => {
  let body: unknown
  try {
    body = await c.req.json()
  } catch {
    return c.json({ error: 'Invalid JSON body' }, 400)
  }
  const parsed = parseBody(body)
  if (typeof parsed === 'string') return c.json({ error: parsed }, 400)
  const created = createTransaction(parsed)
  return c.json(created, 201)
})

transactions.put('/:id', async (c) => {
  const id = parseId(c.req.param('id'))
  if (id === null) return c.json({ error: 'Invalid id' }, 400)
  let body: unknown
  try {
    body = await c.req.json()
  } catch {
    return c.json({ error: 'Invalid JSON body' }, 400)
  }
  const parsed = parseBody(body)
  if (typeof parsed === 'string') return c.json({ error: parsed }, 400)
  const updated = updateTransaction(id, parsed)
  if (!updated) return c.json({ error: 'Transaction not found' }, 404)
  return c.json(updated)
})

transactions.delete('/:id', (c) => {
  const id = parseId(c.req.param('id'))
  if (id === null) return c.json({ error: 'Invalid id' }, 400)
  const removed = deleteTransaction(id)
  if (!removed) return c.json({ error: 'Transaction not found' }, 404)
  return c.body(null, 204)
})

export default transactions
