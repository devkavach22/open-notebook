from fastapi import APIRouter, HTTPException
from typing import List

from api.models import (
    PricingPlanCreate,
    PricingPlanUpdate,
    PricingPlanResponse,
    SubscribeRequest,
    SubscriptionResponse,
    SubscriptionStatsResponse,
    ErrorResponse,
)
from api.pricing_service import PricingService
from loguru import logger

router = APIRouter()


@router.get("/pricing/test")
async def test_pricing():
    """Test endpoint to verify pricing router is working"""
    return {"status": "pricing router is working!"}


@router.get("/pricing/plans")
async def get_pricing_plans():
    """Get all active pricing plans"""
    try:
        plans = await PricingService.get_all_plans()
        # Convert to dict and handle datetime serialization
        result = []
        for plan in plans:
            plan_dict = plan.model_dump() if hasattr(plan, 'model_dump') else plan
            # Ensure datetime fields are strings
            for key in ['created', 'updated']:
                if key in plan_dict and hasattr(plan_dict[key], 'isoformat'):
                    plan_dict[key] = plan_dict[key].isoformat()
            result.append(plan_dict)
        return result
    except Exception as e:
        logger.error(f"Error fetching pricing plans: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Failed to fetch pricing plans")


@router.get("/pricing/plans/{plan_id}")
async def get_pricing_plan(plan_id: str):
    """Get a specific pricing plan by ID"""
    try:
        plan = await PricingService.get_plan_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Pricing plan not found")
        
        # Convert to dict and handle datetime serialization
        plan_dict = plan.model_dump() if hasattr(plan, 'model_dump') else plan
        for key in ['created', 'updated']:
            if key in plan_dict and hasattr(plan_dict[key], 'isoformat'):
                plan_dict[key] = plan_dict[key].isoformat()
        
        return plan_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pricing plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pricing plan")


@router.post("/pricing/plans", status_code=201)
async def create_pricing_plan(plan: PricingPlanCreate):
    """Create a new pricing plan (Admin only)"""
    try:
        from open_notebook.domain.pricing import PricingPlan
        
        new_plan = PricingPlan(**plan.model_dump())
        created_plan = await PricingService.create_plan(new_plan)
        
        # Convert to dict and handle datetime serialization
        plan_dict = created_plan.model_dump() if hasattr(created_plan, 'model_dump') else created_plan
        for key in ['created', 'updated']:
            if key in plan_dict and hasattr(plan_dict[key], 'isoformat'):
                plan_dict[key] = plan_dict[key].isoformat()
        
        return plan_dict
    except Exception as e:
        logger.error(f"Error creating pricing plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to create pricing plan")


@router.patch("/pricing/plans/{plan_id}")
async def update_pricing_plan(plan_id: str, updates: PricingPlanUpdate):
    """Update a pricing plan (Admin only)"""
    try:
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        updated_plan = await PricingService.update_plan(plan_id, update_data)
        if not updated_plan:
            raise HTTPException(status_code=404, detail="Pricing plan not found")
        
        # Convert to dict and handle datetime serialization
        plan_dict = updated_plan.model_dump() if hasattr(updated_plan, 'model_dump') else updated_plan
        for key in ['created', 'updated']:
            if key in plan_dict and hasattr(plan_dict[key], 'isoformat'):
                plan_dict[key] = plan_dict[key].isoformat()
        
        return plan_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pricing plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pricing plan")


@router.delete("/pricing/plans/{plan_id}")
async def delete_pricing_plan(plan_id: str):
    """Delete (deactivate) a pricing plan (Admin only)"""
    try:
        success = await PricingService.delete_plan(plan_id)
        if not success:
            raise HTTPException(status_code=404, detail="Pricing plan not found")
        
        return {"message": "Pricing plan deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pricing plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete pricing plan")


@router.post("/pricing/subscribe", status_code=201)
async def subscribe_to_plan(request: SubscribeRequest):
    """Subscribe a user to a pricing plan"""
    try:
        # Verify plan exists
        plan = await PricingService.get_plan_by_id(request.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Pricing plan not found")
        
        # Create subscription
        subscription = await PricingService.subscribe_user(
            request.user_id, 
            request.plan_id
        )
        
        # Convert to dict and handle datetime serialization
        sub_dict = subscription.model_dump() if hasattr(subscription, 'model_dump') else subscription
        for key in ['start_date', 'end_date', 'created', 'updated']:
            if key in sub_dict and hasattr(sub_dict[key], 'isoformat'):
                sub_dict[key] = sub_dict[key].isoformat()
        
        return sub_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing user: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.get("/pricing/subscription/{user_id}")
async def get_user_subscription(user_id: str):
    """Get active subscription for a user"""
    try:
        subscription = await PricingService.get_user_subscription(user_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Convert to dict and handle datetime serialization
        sub_dict = subscription.model_dump() if hasattr(subscription, 'model_dump') else subscription
        for key in ['start_date', 'end_date', 'created', 'updated']:
            if key in sub_dict and hasattr(sub_dict[key], 'isoformat'):
                sub_dict[key] = sub_dict[key].isoformat()
        
        return sub_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subscription for user {user_id}: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")


@router.post("/pricing/subscription/{subscription_id}/cancel")
async def cancel_subscription(subscription_id: str):
    """Cancel a user subscription"""
    try:
        success = await PricingService.cancel_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {"message": "Subscription cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription {subscription_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.get("/pricing/stats")
async def get_subscription_stats():
    """Get subscription statistics (Admin only)"""
    try:
        stats = await PricingService.get_subscription_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching subscription stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")
