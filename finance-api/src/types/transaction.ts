export type TransactionType = 'income' | 'expense'

export type Transaction = {
  id: number
  description: string
  amount: number
  type: TransactionType
}

export type TransactionInput = {
  description: string
  amount: number
  type: TransactionType
}
