"""
Data Layer - Repositories
All database operations go through repositories
"""

from .assignment_repository import AssignmentRepository
from .base_repository import BaseRepository
from .fact_repository import FactRepository
from .food_log_metadata_repository import FoodLogMetadataRepository
from .food_image_upload_repository import FoodImageUploadRepository
from .food_repository import FoodRepository
from .gym_repository import GymRepository
from .integration_repository import IntegrationRepository
from .knowledge_repository import KnowledgeRepository
from .nutrition_cache_repository import NutritionCacheRepository
from .sleep_repository import SleepRepository
from .todo_repository import TodoRepository
from .user_memory_embeddings_repository import UserMemoryEmbeddingsRepository
from .user_memory_items_repository import UserMemoryItemsRepository
from .user_memory_state_repository import UserMemoryStateRepository
from .user_preferences_repository import UserPreferencesRepository
from .user_repository import UserRepository
from .user_usage_repository import UserUsageRepository
from .usda_repository import USDARepository
from .water_repository import WaterRepository

__all__ = [
    'AssignmentRepository',
    'BaseRepository',
    'FactRepository',
    'FoodLogMetadataRepository',
    'FoodImageUploadRepository',
    'FoodRepository',
    'GymRepository',
    'IntegrationRepository',
    'KnowledgeRepository',
    'NutritionCacheRepository',
    'SleepRepository',
    'TodoRepository',
    'UserMemoryEmbeddingsRepository',
    'UserMemoryItemsRepository',
    'UserMemoryStateRepository',
    'UserPreferencesRepository',
    'UserRepository',
    'UserUsageRepository',
    'USDARepository',
    'WaterRepository',
]
