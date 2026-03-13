import { apiClient } from './client'

export interface PricingPlan {
  id: string
  name: string
  price: number
  currency: string
  period: string
  description: string
  features: string[]
  popular: boolean
  active: boolean
  max_notebooks: number | null
  max_sources: number | null
  created: string
  updated: string
}

export interface Subscription {
  id: string
  user_id: string
  plan: string
  status: string
  start_date: string
  end_date: string | null
  auto_renew: boolean
  created: string
  updated: string
}

export interface SubscriptionStats {
  total_subscriptions: number
  active_subscriptions: number
  cancelled_subscriptions: number
}

export interface SubscribeRequest {
  plan_id: string
  user_id: string
}

/**
 * Get all active pricing plans
 */
export async function getPricingPlans(): Promise<PricingPlan[]> {
  const response = await apiClient.get('/pricing/plans')
  console.log(response,"hhhh");
  
  return response.data
}

/**
 * Get a specific pricing plan by ID
 */
export async function getPricingPlan(planId: string): Promise<PricingPlan> {
  const response = await apiClient.get(`/pricing/plans/${planId}`)
  return response.data
}

/**
 * Subscribe to a pricing plan
 */
export async function subscribeToPlan(data: SubscribeRequest): Promise<Subscription> {
  const response = await apiClient.post('/pricing/subscribe', data)
  return response.data
}

/**
 * Get user's active subscription
 */
export async function getUserSubscription(userId: string): Promise<Subscription | null> {
  try {
    const response = await apiClient.get(`/pricing/subscription/${userId}`)
    return response.data
  } catch (error: any) {
    // Return null if no subscription found (404 is expected)
    if (error?.response?.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * Cancel a subscription
 */
export async function cancelSubscription(subscriptionId: string): Promise<{ message: string }> {
  const response = await apiClient.post(`/pricing/subscription/${subscriptionId}/cancel`)
  return response.data
}

/**
 * Get subscription statistics (admin only)
 */
export async function getSubscriptionStats(): Promise<SubscriptionStats> {
  const response = await apiClient.get('/pricing/stats')
  return response.data
}
