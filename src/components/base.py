"""
Base component interface for all UI components.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseComponent(ABC):
    """Base class for all UI components."""
    
    def __init__(self, app_context):
        """
        Initialize component with application context.
        
        Args:
            app_context: Application context containing services and configuration
        """
        self.app_context = app_context
        self.config = app_context.config if app_context else None
    
    @abstractmethod
    def render(self, **kwargs) -> Optional[Any]:
        """
        Render the component.
        
        Args:
            **kwargs: Component-specific render arguments
            
        Returns:
            Component-specific return value or None
        """
        pass
    
    def get_service(self, service_name: str):
        """
        Get a service from the application context.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        if self.app_context:
            return self.app_context.get_service(service_name)
        return None