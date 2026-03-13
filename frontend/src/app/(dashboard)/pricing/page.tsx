'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Check, AlertCircle } from 'lucide-react'
import { usePricingPlans, useUserSubscription } from '@/lib/hooks/use-pricing'
import { usePaymentFlow } from '@/lib/hooks/use-payment'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export default function PricingPage() {
  const [userId] = useState('default_user') // In real app, get from auth context
  const [selectedPlan, setSelectedPlan] = useState<any>(null)
  const [showCheckoutDialog, setShowCheckoutDialog] = useState(false)
  const [userDetails, setUserDetails] = useState({
    name: '',
    email: '',
    phone: '',
  })
  
  // Fetch pricing plans from API
  const { data: plans, isLoading, error } = usePricingPlans()
  
  // Fetch user's current subscription (optional - may not exist)
  const { data: currentSubscription } = useUserSubscription(userId)
  
  // Payment flow
  const { initiatePayment, isProcessing } = usePaymentFlow()

  const handleSelectPlan = (plan: any) => {
    setSelectedPlan(plan)
    setShowCheckoutDialog(true)
  }

  const handleProceedToPayment = async () => {
    if (!selectedPlan) return

    await initiatePayment({
      user_id: userId,
      plan_id: selectedPlan.id,
      plan_name: selectedPlan.name,
      name: userDetails.name,
      email: userDetails.email,
      phone: userDetails.phone,
    })

    setShowCheckoutDialog(false)
  }

  // Check if user is already subscribed to a plan
  const isSubscribedToPlan = (planId: string) => {
    if (!currentSubscription) return false
    return currentSubscription.plan === planId && currentSubscription.status === 'active'
  }

  // Loading state
  if (isLoading) {
    return (
      <AppShell>
        <div className="flex-1 flex items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  // Error state
  if (error) {
    return (
      <AppShell>
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load pricing plans: {error.message}
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </AppShell>
    )
  }

  // No plans available
  if (!plans || plans.length === 0) {
    return (
      <AppShell>
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto text-center">
            <h1 className="text-2xl font-bold mb-4">No Pricing Plans Available</h1>
            <p className="text-muted-foreground">
              Please check back later or contact support.
            </p>
          </div>
        </div>
      </AppShell>
    )
  }

  // Sort plans by price (0, 19, 99)
  const sortedPlans = [...plans].sort((a, b) => a.price - b.price)

  return (
    <AppShell>
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4">Choose Your Plan</h1>
            <p className="text-lg text-muted-foreground">
              Select the perfect plan for your needs
            </p>
            {currentSubscription && (
              <Badge variant="secondary" className="mt-4">
                Current Plan: {currentSubscription.plan.split(':')[1]}
              </Badge>
            )}
          </div>

          {/* Pricing Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {sortedPlans.map((plan) => {
              const isCurrentPlan = isSubscribedToPlan(plan.id)

              return (
                <Card
                  key={plan.id}
                  className={`relative ${
                    plan.popular ? 'border-primary shadow-lg' : ''
                  } ${isCurrentPlan ? 'border-green-500' : ''}`}
                >
                  {plan.popular && (
                    <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">
                      Most Popular
                    </Badge>
                  )}
                  {isCurrentPlan && (
                    <Badge 
                      variant="secondary" 
                      className="absolute -top-3 right-4 bg-green-500 text-white"
                    >
                      Current Plan
                    </Badge>
                  )}
                  
                  <CardHeader>
                    <CardTitle className="text-2xl">{plan.name}</CardTitle>
                    <CardDescription>{plan.description}</CardDescription>
                    <div className="mt-4">
                      <span className="text-4xl font-bold">
                        {plan.currency === 'USD' ? '$' : plan.currency}
                        {plan.price}
                      </span>
                      <span className="text-muted-foreground">/{plan.period}</span>
                    </div>
                    {plan.max_notebooks !== null && (
                      <p className="text-xs text-muted-foreground mt-2">
                        Up to {plan.max_notebooks} notebooks
                      </p>
                    )}
                  </CardHeader>

                  <CardContent>
                    <Button
                      className="w-full mb-6"
                      variant={plan.popular ? 'default' : 'outline'}
                      onClick={() => handleSelectPlan(plan)}
                      disabled={isCurrentPlan || isProcessing}
                    >
                      {isCurrentPlan 
                        ? 'Current Plan' 
                        : isProcessing 
                        ? 'Processing...' 
                        : plan.price === 0 
                        ? 'Get Started' 
                        : 'Subscribe Now'}
                    </Button>

                    <ul className="space-y-3">
                      {plan.features.map((feature, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <Check className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                          <span className="text-sm">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Current Subscription Info */}
          {currentSubscription && (
            <div className="mt-12 max-w-2xl mx-auto">
              <Card>
                <CardHeader>
                  <CardTitle>Your Subscription</CardTitle>
                  <CardDescription>Manage your current subscription</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <Badge variant={currentSubscription.status === 'active' ? 'default' : 'secondary'}>
                      {currentSubscription.status}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Started:</span>
                    <span>{new Date(currentSubscription.start_date).toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Auto-renew:</span>
                    <span>{currentSubscription.auto_renew ? 'Yes' : 'No'}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* FAQ Section */}
          <div className="mt-16 text-center">
            <h2 className="text-2xl font-bold mb-4">Frequently Asked Questions</h2>
            <p className="text-muted-foreground">
              Have questions? Contact us at support@opennotebook.com
            </p>
          </div>
        </div>
      </div>

      {/* Checkout Dialog */}
      <Dialog open={showCheckoutDialog} onOpenChange={setShowCheckoutDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Complete Your Purchase</DialogTitle>
            <DialogDescription>
              Enter your details to proceed with payment
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {selectedPlan && (
              <div className="p-4 bg-muted rounded-lg">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-semibold">{selectedPlan.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {selectedPlan.description}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold">
                      ₹{selectedPlan.price}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      /{selectedPlan.period}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                value={userDetails.name}
                onChange={(e) => setUserDetails({ ...userDetails, name: e.target.value })}
                placeholder="John Doe"
              />
            </div>

            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={userDetails.email}
                onChange={(e) => setUserDetails({ ...userDetails, email: e.target.value })}
                placeholder="john@example.com"
              />
            </div>

            <div>
              <Label htmlFor="phone">Phone Number</Label>
              <Input
                id="phone"
                value={userDetails.phone}
                onChange={(e) => setUserDetails({ ...userDetails, phone: e.target.value })}
                placeholder="+91 9876543210"
              />
            </div>

            <Button
              className="w-full"
              onClick={handleProceedToPayment}
              disabled={
                isProcessing || 
                !userDetails.name || 
                !userDetails.email || 
                !userDetails.phone
              }
            >
              {isProcessing ? 'Processing...' : `Pay ₹${selectedPlan?.price}`}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
              🔒 Secure payment powered by Razorpay
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
