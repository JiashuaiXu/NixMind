#!/usr/bin/env python3

"""
NixMind - Local AI Agent for NixOS Management

Main entry point for the NixMind system.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nixmind.core.config import Config
from nixmind.core.logger import setup_logging
from nixmind.cli.main import main as cli_main


def main():
    """Main entry point for NixMind."""
    # Load configuration
    config = Config()
    
    # Setup logging
    setup_logging(config.log_level, config.log_file)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting NixMind - Local AI Agent for NixOS")
    
    try:
        # Run the CLI interface
        asyncio.run(cli_main())
    except KeyboardInterrupt:
        logger.info("NixMind interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()