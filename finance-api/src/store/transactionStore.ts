import type { Transaction, TransactionInput } from '../types/transaction.js'

const transactions: Transaction[] = []
let nextId = 1

export const listTransactions = (): Transaction[] => {
  return transactions.slice()
}

export const getTransaction = (id: number): Transaction | undefined => {
  return transactions.find((t) => t.id === id)
}

export const createTransaction = (input: TransactionInput): Transaction => {
  const transaction: Transaction = { id: nextId++, ...input }
  transactions.push(transaction)
  return transaction
}

export const updateTransaction = (
  id: number,
  input: TransactionInput,
): Transaction | undefined => {
  const index = transactions.findIndex((t) => t.id === id)
  if (index === -1) return undefined
  const updated: Transaction = { id, ...input }
  transactions[index] = updated
  return updated
}

export const deleteTransaction = (id: number): boolean => {
  const index = transactions.findIndex((t) => t.id === id)
  if (index === -1) return false
  transactions.splice(index, 1)
  return true
}
