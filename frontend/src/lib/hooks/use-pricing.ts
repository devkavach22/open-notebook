import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getPricingPlans,
  getPricingPlan,
  subscribeToPlan,
  getUserSubscription,
  cancelSubscription,
  getSubscriptionStats,
  type PricingPlan,
  type Subscription,
  type SubscriptionStats,
  type SubscribeRequest,
} from '@/lib/api/pricing'
import { toast } from 'sonner'

/**
 * Hook to fetch all pricing plans
 */
export function usePricingPlans() {
  return useQuery<PricingPlan[], Error>({
    queryKey: ['pricing-plans'],
    queryFn: getPricingPlans,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to fetch a specific pricing plan
 */
export function usePricingPlan(planId: string) {
  return useQuery<PricingPlan, Error>({
    queryKey: ['pricing-plan', planId],
    queryFn: () => getPricingPlan(planId),
    enabled: !!planId,
  })
}

/**
 * Hook to subscribe to a plan
 */
export function useSubscribeToPlan() {
  const queryClient = useQueryClient()

  return useMutation<Subscription, Error, SubscribeRequest>({
    mutationFn: subscribeToPlan,
    onSuccess: (data) => {
      toast.success('Successfully subscribed to plan!')
      // Invalidate and refetch user subscription
      queryClient.invalidateQueries({ queryKey: ['user-subscription', data.user_id] })
      queryClient.invalidateQueries({ queryKey: ['subscription-stats'] })
    },
    onError: (error) => {
      toast.error(`Failed to subscribe: ${error.message}`)
    },
  })
}

/**
 * Hook to fetch user's subscription
 */
export function useUserSubscription(userId: string) {
  return useQuery<Subscription | null, Error>({
    queryKey: ['user-subscription', userId],
    queryFn: () => getUserSubscription(userId),
    enabled: !!userId,
    retry: false, // Don't retry if user has no subscription
  })
}

/**
 * Hook to cancel subscription
 */
export function useCancelSubscription() {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, string>({
    mutationFn: cancelSubscription,
    onSuccess: () => {
      toast.success('Subscription cancelled successfully')
      // Invalidate all subscription queries
      queryClient.invalidateQueries({ queryKey: ['user-subscription'] })
      queryClient.invalidateQueries({ queryKey: ['subscription-stats'] })
    },
    onError: (error) => {
      toast.error(`Failed to cancel subscription: ${error.message}`)
    },
  })
}

/**
 * Hook to fetch subscription statistics
 */
export function useSubscriptionStats() {
  return useQuery<SubscriptionStats, Error>({
    queryKey: ['subscription-stats'],
    queryFn: getSubscriptionStats,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}
