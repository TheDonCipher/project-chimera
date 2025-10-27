#!/usr/bin/env python3
"""
Database initialization script

Creates all tables and indexes for the Chimera bot.
"""

import sys
from pathlib import Path

# Add bot/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bot" / "src"))

from config import init_config
from database import init_database, init_redis
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Initialize database and Redis"""
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = init_config()
        
        # Initialize database
        logger.info("Initializing database...")
        db_manager = init_database(config.database)
        
        # Verify connection
        if db_manager.health_check():
            logger.info("✓ Database connection verified")
        else:
            logger.error("✗ Database health check failed")
            return 1
        
        # Initialize Redis
        logger.info("Initializing Redis...")
        redis_manager = init_redis(config.redis)
        
        # Verify connection
        if redis_manager.health_check():
            logger.info("✓ Redis connection verified")
        else:
            logger.warning("⚠ Redis connection failed, will use in-memory fallback")
        
        logger.info("Database initialization complete!")
        return 0
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
