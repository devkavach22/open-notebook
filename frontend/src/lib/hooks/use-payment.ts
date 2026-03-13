/**
 * Payment Hooks for Razorpay Integration
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as paymentApi from '../api/payment'
import { useRazorpay } from './use-razorpay'
import { toast } from 'sonner'

// ==================== MUTATIONS ====================

/**
 * Create order mutation
 */
export const useCreateOrder = () => {
  return useMutation({
    mutationFn: paymentApi.createOrder,
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create order')
    },
  })
}

/**
 * Verify payment mutation
 */
export const useVerifyPayment = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: paymentApi.verifyPayment,
    onSuccess: (_, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['transactions', variables.user_id] })
      queryClient.invalidateQueries({ queryKey: ['subscription', variables.user_id] })
      queryClient.invalidateQueries({ queryKey: ['invoices', variables.user_id] })

      toast.success('Payment Successful! 🎉', {
        description: 'Your subscription has been activated.',
      })
    },
    onError: (error: any) => {
      toast.error('Payment Verification Failed', {
        description: error.message || 'Please contact support',
      })
    },
  })
}

/**
 * Create refund mutation (Admin only)
 */
export const useCreateRefund = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: paymentApi.createRefund,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['refunds', data.transaction_id] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })

      toast.success('Refund Created', {
        description: 'The refund has been processed successfully.',
      })
    },
    onError: (error: any) => {
      toast.error('Refund Failed', {
        description: error.message || 'Failed to process refund',
      })
    },
  })
}

// ==================== QUERIES ====================

/**
 * Get user transactions
 */
export const useTransactions = (userId: string, limit: number = 50) => {
  return useQuery({
    queryKey: ['transactions', userId, limit],
    queryFn: () => paymentApi.getTransactions(userId, limit),
    enabled: !!userId,
  })
}

/**
 * Get transaction by order ID
 */
export const useTransactionByOrder = (orderId: string) => {
  return useQuery({
    queryKey: ['transaction', 'order', orderId],
    queryFn: () => paymentApi.getTransactionByOrder(orderId),
    enabled: !!orderId,
  })
}

/**
 * Get user invoices
 */
export const useInvoices = (userId: string) => {
  return useQuery({
    queryKey: ['invoices', userId],
    queryFn: () => paymentApi.getInvoices(userId),
    enabled: !!userId,
  })
}

/**
 * Get specific invoice
 */
export const useInvoice = (invoiceId: string) => {
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => paymentApi.getInvoice(invoiceId),
    enabled: !!invoiceId,
  })
}

/**
 * Get refunds for transaction
 */
export const useRefunds = (transactionId: string) => {
  return useQuery({
    queryKey: ['refunds', transactionId],
    queryFn: () => paymentApi.getRefunds(transactionId),
    enabled: !!transactionId,
  })
}

// ==================== COMPLETE PAYMENT FLOW ====================

/**
 * Complete payment flow hook
 * Handles: Order creation → Razorpay checkout → Payment verification
 */
export const usePaymentFlow = () => {
  const { openCheckout } = useRazorpay()
  const createOrderMutation = useCreateOrder()
  const verifyPaymentMutation = useVerifyPayment()

  const initiatePayment = async (data: {
    user_id: string
    plan_id: string
    plan_name: string
    email: string
    phone: string
    name: string
    coupon_code?: string
  }) => {
    try {
      // Step 1: Create order
      const order = await createOrderMutation.mutateAsync({
        user_id: data.user_id,
        plan_id: data.plan_id,
        email: data.email,
        phone: data.phone,
        name: data.name,
        coupon_code: data.coupon_code,
      })

      // Step 2: Open Razorpay checkout
      openCheckout({
        key: order.key_id,
        amount: order.amount * 100, // Convert to paise
        currency: order.currency,
        name: 'Open Notebook',
        description: `Subscription to ${data.plan_name}`,
        order_id: order.order_id,
        prefill: {
          name: data.name,
          email: data.email,
          contact: data.phone,
        },
        theme: {
          color: '#3b82f6', // Tailwind blue-500
        },
        handler: async (response) => {
          // Step 3: Verify payment
          await verifyPaymentMutation.mutateAsync({
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
            user_id: data.user_id,
            plan_id: data.plan_id,
          })
        },
        modal: {
          ondismiss: () => {
            toast.info('Payment Cancelled', {
              description: 'You cancelled the payment process.',
            })
          },
        },
      })
    } catch (error: any) {
      toast.error('Payment Failed', {
        description: error.message || 'Something went wrong',
      })
    }
  }

  return {
    initiatePayment,
    isProcessing: createOrderMutation.isPending || verifyPaymentMutation.isPending,
  }
}
