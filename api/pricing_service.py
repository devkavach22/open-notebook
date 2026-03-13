from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from loguru import logger

from open_notebook.database.repository import (
    repo_query,
    repo_create,
    db_connection,
    parse_record_ids,
)
from open_notebook.domain.pricing import PricingPlan, UserSubscription


class PricingService:
    """Service for managing pricing plans and subscriptions"""

    @staticmethod
    async def get_all_plans() -> List[PricingPlan]:
        """Get all active pricing plans"""
        try:
            # Try simple query first
            query = "SELECT * FROM pricing_plan;"
            result = await repo_query(query)
            
            logger.info(f"Raw query result type: {type(result)}")
            
            if not result:
                logger.warning("Result is None or empty")
                return []
            
            # The result is directly a list of plans
            plans = result if isinstance(result, list) else []
            logger.info(f"Found {len(plans)} plans")
            
            # Filter active plans
            active_plans = [plan for plan in plans if isinstance(plan, dict) and plan.get("active", True)]
            logger.info(f"Filtered to {len(active_plans)} active plans")
            
            # Convert datetime objects to ISO strings for ALL fields
            for plan in active_plans:
                # Convert all datetime fields to strings
                for key, value in list(plan.items()):
                    if hasattr(value, "isoformat"):
                        plan[key] = value.isoformat()
                    elif isinstance(value, str):
                        pass  # Already a string
            
            return [PricingPlan(**plan) for plan in active_plans]
            
        except Exception as e:
            logger.error(f"Error in get_all_plans: {e}")
            logger.exception(e)
            return []

    @staticmethod
    async def get_plan_by_id(plan_id: str) -> Optional[PricingPlan]:
        """Get a specific pricing plan by ID"""
        from loguru import logger
        
        query = f"""
            SELECT * FROM {plan_id}
        """
        result = await repo_query(query)
        
        logger.info(f"get_plan_by_id result type: {type(result)}, value: {result}")
        
        if not result or len(result) == 0:
            return None
        
        # Handle nested list structure
        plan_data = result[0] if isinstance(result, list) else result
        logger.info(f"After first extraction - type: {type(plan_data)}, value: {plan_data}")
        
        # If still a list, get first element
        if isinstance(plan_data, list) and len(plan_data) > 0:
            plan_data = plan_data[0]
            logger.info(f"After second extraction - type: {type(plan_data)}, value: {plan_data}")
        
        # Ensure we have a dict
        if not isinstance(plan_data, dict):
            logger.error(f"Invalid plan data type: {type(plan_data)}, data: {plan_data}")
            return None
        
        # Convert datetime objects to ISO strings
        for key, value in list(plan_data.items()):
            if hasattr(value, "isoformat"):
                plan_data[key] = value.isoformat()
        
        logger.info(f"Final plan_data: {plan_data}")
        return PricingPlan(**plan_data)

    @staticmethod
    async def create_plan(plan: PricingPlan) -> PricingPlan:
        """Create a new pricing plan"""
        plan_data = plan.model_dump(exclude={"id", "created", "updated"})
        result = await repo_create("pricing_plan", plan_data)
        return PricingPlan(**result)

    @staticmethod
    async def update_plan(plan_id: str, updates: Dict[str, Any]) -> Optional[PricingPlan]:
        """Update a pricing plan"""
        updates["updated"] = datetime.now(timezone.utc)
        
        query = f"""
            UPDATE {plan_id} MERGE $updates
        """
        result = await repo_query(query, {"updates": updates})
        
        if not result or len(result) == 0:
            return None
        
        plan_data = result[0] if isinstance(result, list) else result
        
        # Convert datetime objects to ISO strings
        for key, value in list(plan_data.items()):
            if hasattr(value, "isoformat"):
                plan_data[key] = value.isoformat()
        
        return PricingPlan(**plan_data)

    @staticmethod
    async def delete_plan(plan_id: str) -> bool:
        """Soft delete a pricing plan (set active=false)"""
        query = f"""
            UPDATE {plan_id} SET active = false, updated = time::now()
        """
        result = await repo_query(query)
        return bool(result and len(result) > 0)

    @staticmethod
    async def subscribe_user(user_id: str, plan_id: str) -> UserSubscription:
        """Subscribe a user to a pricing plan"""
        subscription_data = {
            "user_id": user_id,
            "plan": plan_id,
            "status": "active",
            "start_date": datetime.now(timezone.utc),
            "auto_renew": True,
        }
        
        result = await repo_create("user_subscription", subscription_data)
        
        # Handle if result is a list
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        
        # Convert datetime objects to ISO strings
        for key, value in list(result.items()):
            if hasattr(value, "isoformat"):
                result[key] = value.isoformat()
        
        return UserSubscription(**result)

    @staticmethod
    async def get_user_subscription(user_id: str) -> Optional[UserSubscription]:
        """Get active subscription for a user"""
        query = """
            SELECT * FROM user_subscription 
            WHERE user_id = $user_id AND status = 'active'
            ORDER BY created DESC
            LIMIT 1
        """
        result = await repo_query(query, {"user_id": user_id})
        
        if not result or len(result) == 0:
            return None
        
        sub_data = result[0] if isinstance(result, list) else result
        
        # Convert datetime objects to ISO strings
        for key, value in list(sub_data.items()):
            if hasattr(value, "isoformat"):
                sub_data[key] = value.isoformat()
        
        return UserSubscription(**sub_data)

    @staticmethod
    async def cancel_subscription(subscription_id: str) -> bool:
        """Cancel a user subscription"""
        query = f"""
            UPDATE {subscription_id} SET 
                status = 'cancelled',
                end_date = time::now(),
                updated = time::now()
        """
        result = await repo_query(query)
        return bool(result and len(result) > 0)

    @staticmethod
    async def get_subscription_stats() -> Dict[str, Any]:
        """Get subscription statistics"""
        query = """
            SELECT 
                count() as total_subscriptions,
                count(status = 'active') as active_subscriptions,
                count(status = 'cancelled') as cancelled_subscriptions
            FROM user_subscription
        """
        result = await repo_query(query)
        
        if not result or len(result) == 0:
            return {
                "total_subscriptions": 0,
                "active_subscriptions": 0,
                "cancelled_subscriptions": 0,
            }
        
        stats_data = result[0] if isinstance(result, list) else result
        return stats_data
