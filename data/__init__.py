"""
Data Layer - Repositories
All database operations go through repositories
"""

from .base_repository import BaseRepository
from .user_repository import UserRepository
from .food_repository import FoodRepository
from .water_repository import WaterRepository
from .gym_repository import GymRepository
from .todo_repository import TodoRepository
from .knowledge_repository import KnowledgeRepository
from .sleep_repository import SleepRepository
from .assignment_repository import AssignmentRepository
from .fact_repository import FactRepository
from .integration_repository import IntegrationRepository
from .user_preferences_repository import UserPreferencesRepository
from .nutrition_cache_repository import NutritionCacheRepository
from .food_log_metadata_repository import FoodLogMetadataRepository
from .food_image_upload_repository import FoodImageUploadRepository
from .user_memory_state_repository import UserMemoryStateRepository
from .user_memory_items_repository import UserMemoryItemsRepository
from .user_memory_embeddings_repository import UserMemoryEmbeddingsRepository
from .user_usage_repository import UserUsageRepository
from .usda_repository import USDARepository

__all__ = [
    'BaseRepository',
    'UserRepository',
    'FoodRepository',
    'WaterRepository',
    'GymRepository',
    'TodoRepository',
    'KnowledgeRepository',
    'SleepRepository',
    'AssignmentRepository',
    'FactRepository',
    'IntegrationRepository',
    'UserPreferencesRepository',
    'NutritionCacheRepository',
    'FoodLogMetadataRepository',
    'FoodImageUploadRepository',
    'UserMemoryStateRepository',
    'UserMemoryItemsRepository',
    'UserMemoryEmbeddingsRepository',
    'UserUsageRepository',
    'USDARepository',
]
