/**
 * Payment API Client for Razorpay Integration
 */

import { apiClient } from './client'

// ==================== TYPES ====================

export interface CreateOrderRequest {
  user_id: string
  plan_id: string
  email: string
  phone: string
  name: string
  coupon_code?: string
}

export interface CreateOrderResponse {
  order_id: string
  amount: number
  currency: string
  transaction_id: string
  key_id: string
}

export interface VerifyPaymentRequest {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
  user_id: string
  plan_id: string
}

export interface VerifyPaymentResponse {
  success: boolean
  transaction_id: string
  subscription_id: string
  message: string
}

export interface Transaction {
  id: string
  user_id: string
  subscription_id?: string
  amount: number
  currency: string
  status: string
  razorpay_order_id?: string
  razorpay_payment_id?: string
  payment_method?: string
  description: string
  metadata?: Record<string, any>
  created: string
  updated: string
}

export interface Invoice {
  id: string
  user_id: string
  subscription_id?: string
  transaction_id?: string
  invoice_number: string
  amount: number
  currency: string
  tax_amount: number
  status: string
  due_date: string
  paid_date?: string
  line_items: Array<{
    description: string
    amount: number
    quantity: number
    tax_rate?: number
    tax_amount?: number
  }>
  pdf_url?: string
  razorpay_invoice_id?: string
  created: string
  updated: string
}

export interface Refund {
  id: string
  transaction_id: string
  user_id: string
  amount: number
  currency: string
  reason: string
  status: string
  razorpay_refund_id?: string
  speed: string
  created: string
  updated: string
}

// ==================== API FUNCTIONS ====================

/**
 * Create Razorpay order for payment
 */
export const createOrder = async (
  data: CreateOrderRequest
): Promise<CreateOrderResponse> => {
  const response = await apiClient.post('/payment/create-order', data)
  return response.data
}

/**
 * Verify payment after Razorpay checkout
 */
export const verifyPayment = async (
  data: VerifyPaymentRequest
): Promise<VerifyPaymentResponse> => {
  const response = await apiClient.post('/payment/verify', data)
  return response.data
}

/**
 * Get transaction history for a user
 */
export const getTransactions = async (
  userId: string,
  limit: number = 50
): Promise<Transaction[]> => {
  const response = await apiClient.get(`/payment/transactions/${userId}`, {
    params: { limit }
  })
  return response.data
}

/**
 * Get transaction by Razorpay order ID
 */
export const getTransactionByOrder = async (
  orderId: string
): Promise<Transaction> => {
  const response = await apiClient.get(`/payment/transactions/order/${orderId}`)
  return response.data
}

/**
 * Get all invoices for a user
 */
export const getInvoices = async (userId: string): Promise<Invoice[]> => {
  const response = await apiClient.get(`/payment/invoices/${userId}`)
  return response.data
}

/**
 * Get a specific invoice
 */
export const getInvoice = async (invoiceId: string): Promise<Invoice> => {
  const response = await apiClient.get(`/payment/invoices/detail/${invoiceId}`)
  return response.data
}

/**
 * Download invoice as PDF
 */
export const downloadInvoice = async (invoiceId: string) => {
  const response = await apiClient.get(
    `/payment/invoices/${invoiceId}/download`,
    {
      responseType: 'blob',
    }
  )

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `invoice-${invoiceId}.pdf`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

/**
 * Create a refund (Admin only)
 */
export const createRefund = async (data: {
  transaction_id: string
  amount?: number
  reason: string
  speed?: 'normal' | 'optimum'
}): Promise<Refund> => {
  const response = await apiClient.post('/payment/refunds', data)
  return response.data
}

/**
 * Get refunds for a transaction
 */
export const getRefunds = async (transactionId: string): Promise<Refund[]> => {
  const response = await apiClient.get(`/payment/refunds/${transactionId}`)
  return response.data
}
