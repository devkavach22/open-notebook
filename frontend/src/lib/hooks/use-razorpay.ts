/**
 * Razorpay Checkout Hook
 */

import { useState } from 'react'
import { toast } from 'sonner'

// Extend Window interface for Razorpay
declare global {
  interface Window {
    Razorpay: any
  }
}

export interface RazorpayOptions {
  key: string
  amount: number
  currency: string
  name: string
  description: string
  order_id: string
  prefill?: {
    name?: string
    email?: string
    contact?: string
  }
  theme?: {
    color?: string
  }
  handler: (response: RazorpayResponse) => void
  modal?: {
    ondismiss?: () => void
  }
}

export interface RazorpayResponse {
  razorpay_payment_id: string
  razorpay_order_id: string
  razorpay_signature: string
}

export const useRazorpay = () => {
  const [isProcessing, setIsProcessing] = useState(false)

  const openCheckout = (options: RazorpayOptions) => {
    // Check if Razorpay SDK is loaded
    if (!window.Razorpay) {
      toast.error('Razorpay SDK not loaded. Please refresh the page.')
      return
    }

    setIsProcessing(true)

    // Create Razorpay instance
    const rzp = new window.Razorpay({
      ...options,
      handler: (response: RazorpayResponse) => {
        setIsProcessing(false)
        options.handler(response)
      },
      modal: {
        ondismiss: () => {
          setIsProcessing(false)
          options.modal?.ondismiss?.()
        },
      },
    })

    // Open checkout
    rzp.open()
  }

  return {
    openCheckout,
    isProcessing,
  }
}
