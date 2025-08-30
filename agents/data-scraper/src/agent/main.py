"""
Main entry point for Data Scraper Agent.

This module provides the command-line interface for the Data Scraper Agent,
allowing users to execute scraping jobs, list configurations, and validate setups.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from .data_scraper_agent import DataScraperAgent, DataScraperAgentError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


class DataScraperCLI:
    """
    Command-line interface for Data Scraper Agent.
    """

    def __init__(self):
        """Initialize the CLI."""
        self.agent: Optional[DataScraperAgent] = None

    async def run(self, args: Optional[list] = None) -> int:
        """
        Run the CLI with the given arguments.

        Args:
            args: Command line arguments (uses sys.argv if None)

        Returns:
            int: Exit code
        """
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        try:
            # Initialize agent
            self.agent = DataScraperAgent(
                config_base_path=parsed_args.config_path,
                output_base_path=parsed_args.output_path,
            )

            # Execute command
            if parsed_args.command == "scrape":
                return await self._execute_scrape(parsed_args)
            elif parsed_args.command == "list":
                return await self._execute_list(parsed_args)
            elif parsed_args.command == "validate":
                return await self._execute_validate(parsed_args)
            elif parsed_args.command == "info":
                return await self._execute_info(parsed_args)
            else:
                logger.error(f"Unknown command: {parsed_args.command}")
                return 1

        except Exception as e:
            logger.error(f"CLI execution failed: {e}", exc_info=True)
            return 1

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser."""
        parser = argparse.ArgumentParser(
            description="Data Scraper Agent - Scrape data from APIs using configuration files",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Execute a scraping job
  python -m agent.main scrape --config github-api

  # Execute with job ID and overrides
  python -m agent.main scrape --config github-api --job-id my-job --override '{"rate_limit": {"requests_per_minute": 30}}'

  # List available configurations
  python -m agent.main list

  # Validate a configuration
  python -m agent.main validate --config github-api

  # Get configuration info
  python -m agent.main info --config github-api
            """,
        )

        # Global options
        parser.add_argument(
            "--config-path",
            default="/app/config",
            help="Base path for configuration files (default: /app/config)",
        )
        parser.add_argument(
            "--output-path",
            default="/app/output",
            help="Base path for output files (default: /app/output)",
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose logging"
        )

        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Scrape command
        scrape_parser = subparsers.add_parser("scrape", help="Execute a scraping job")
        scrape_parser.add_argument(
            "--config", "-c", required=True, help="Name of the API configuration to use"
        )
        scrape_parser.add_argument(
            "--job-id",
            "-j",
            help="Job ID for tracking (auto-generated if not provided)",
        )
        scrape_parser.add_argument(
            "--override", "-o", help="JSON string with configuration overrides"
        )

        # List command
        list_parser = subparsers.add_parser(
            "list", help="List available configurations"
        )
        list_parser.add_argument(
            "--format",
            "-f",
            choices=["json", "table", "simple"],
            default="table",
            help="Output format (default: table)",
        )

        # Validate command
        validate_parser = subparsers.add_parser(
            "validate", help="Validate a configuration"
        )
        validate_parser.add_argument(
            "--config",
            "-c",
            required=True,
            help="Name of the configuration to validate",
        )

        # Info command
        info_parser = subparsers.add_parser(
            "info", help="Get configuration information"
        )
        info_parser.add_argument(
            "--config",
            "-c",
            required=True,
            help="Name of the configuration to get info for",
        )

        return parser

    async def _execute_scrape(self, args: argparse.Namespace) -> int:
        """Execute scraping command."""
        try:
            # Parse overrides if provided
            override_params = None
            if args.override:
                try:
                    override_params = json.loads(args.override)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in override parameter: {e}")
                    return 1

            logger.info(f"Starting scraping job for configuration: {args.config}")
            if args.job_id:
                logger.info(f"Job ID: {args.job_id}")
            if override_params:
                logger.info(f"Overrides: {override_params}")

            # Execute scraping job
            if not self.agent:
                logger.error("Agent not initialized")
                return 1

            result = await self.agent.execute_scraping_job(
                config_name=args.config,
                job_id=args.job_id,
                override_params=override_params,
            )

            # Print results
            print("\n" + "=" * 60)
            print("SCRAPING JOB COMPLETED")
            print("=" * 60)
            print(f"Job ID: {result.job_id}")
            print(f"Configuration: {result.config_name}")
            print(f"Status: {result.status}")
            print(f"Duration: {result.duration_seconds:.2f} seconds")
            print(f"Endpoints Scraped: {result.endpoints_scraped}")
            print(f"Records Processed: {result.records_processed}")
            print(f"Data Size: {result.data_size_bytes} bytes")

            if result.output_location:
                print(f"Output File: {result.output_location}")

            if result.error_message:
                print(f"Error: {result.error_message}")

            print("=" * 60)

            return 0 if result.status == "completed" else 1

        except DataScraperAgentError as e:
            logger.error(f"Scraping failed: {e}")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}", exc_info=True)
            return 1

    async def _execute_list(self, args: argparse.Namespace) -> int:
        """Execute list command."""
        try:
            if not self.agent:
                logger.error("Agent not initialized")
                return 1

            configs = await self.agent.list_available_configs()

            if args.format == "json":
                print(json.dumps(configs, indent=2))
            elif args.format == "table":
                self._print_configs_table(configs)
            else:  # simple
                for config in configs:
                    if "error" in config:
                        print(f"{config['name']} (ERROR: {config['error']})")
                    else:
                        print(
                            f"{config['name']} - {config.get('description', 'No description')}"
                        )

            return 0

        except Exception as e:
            logger.error(f"Failed to list configurations: {e}")
            return 1

    async def _execute_validate(self, args: argparse.Namespace) -> int:
        """Execute validate command."""
        try:
            if not self.agent:
                logger.error("Agent not initialized")
                return 1

            result = await self.agent.validate_config(args.config)

            if result["valid"]:
                print(f"✅ Configuration '{args.config}' is valid")
                print(
                    f"   Description: {result['info'].get('description', 'No description')}"
                )
                print(f"   Base URL: {result['info'].get('base_url', 'N/A')}")
                print(f"   Endpoints: {result['info'].get('endpoints_count', 0)}")
                print(
                    f"   Auth Type: {result['info'].get('authentication_type', 'N/A')}"
                )
                return 0
            else:
                print(f"❌ Configuration '{args.config}' is invalid")
                if "error" in result:
                    print(f"   Error: {result['error']}")
                return 1

        except Exception as e:
            logger.error(f"Failed to validate configuration: {e}")
            return 1

    async def _execute_info(self, args: argparse.Namespace) -> int:
        """Execute info command."""
        try:
            if not self.agent:
                logger.error("Agent not initialized")
                return 1

            result = await self.agent.validate_config(args.config)

            if result["valid"]:
                info = result["info"]
                print(f"\nConfiguration: {info['name']}")
                print(f"Description: {info.get('description', 'No description')}")
                print(f"Base URL: {info.get('base_url', 'N/A')}")
                print(f"Endpoints: {info.get('endpoints_count', 0)}")
                print(f"Authentication: {info.get('authentication_type', 'N/A')}")
                print(f"Data Format: {info.get('data_format', 'N/A')}")
                print(f"Enabled: {info.get('enabled', True)}")

                if info.get("schedule"):
                    print(f"Schedule: {info['schedule']}")

                rate_limit = info.get("rate_limit", {})
                if rate_limit:
                    print("Rate Limit:")
                    print(
                        f"  Requests per minute: {rate_limit.get('requests_per_minute', 'N/A')}"
                    )
                    print(
                        f"  Requests per hour: {rate_limit.get('requests_per_hour', 'N/A')}"
                    )
                    print(
                        f"  Delay between requests: {rate_limit.get('delay_between_requests', 'N/A')}s"
                    )

                return 0
            else:
                print(f"❌ Configuration '{args.config}' is invalid")
                if "error" in result:
                    print(f"Error: {result['error']}")
                return 1

        except Exception as e:
            logger.error(f"Failed to get configuration info: {e}")
            return 1

    def _print_configs_table(self, configs: list) -> None:
        """Print configurations in table format."""
        if not configs:
            print("No configurations found.")
            return

        # Find max lengths for formatting
        max_name = max(len(config.get("name", "")) for config in configs)
        max_desc = max(len(config.get("description", "")) for config in configs)
        max_url = max(len(str(config.get("base_url", ""))) for config in configs)

        # Print header
        name_col = f"{'Name':<{max_name}}"
        desc_col = f"{'Description':<{max_desc}}"
        url_col = f"{'Base URL':<{max_url}}"
        header = f"{name_col} | {desc_col} | {url_col} | Endpoints"
        print(header)
        print("-" * (max_name + max_desc + max_url + 20))

        # Print rows
        for config in configs:
            name = config.get("name", "")
            desc = config.get("description", "")
            url = str(config.get("base_url", ""))
            endpoints = config.get("endpoints_count", 0)

            if "error" in config:
                print(
                    f"{name:<{max_name}} | {'ERROR':<{max_desc}} | {'N/A':<{max_url}} | {'N/A'}"
                )
            else:
                print(
                    f"{name:<{max_name}} | {desc:<{max_desc}} | {url:<{max_url}} | {endpoints}"
                )


def main():
    """Main entry point."""
    # Ensure log directory exists
    log_dir = Path("/app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set log level based on environment
    if os.getenv("VERBOSE", "false").lower() == "true":
        logging.getLogger().setLevel(logging.DEBUG)

    # Run CLI
    cli = DataScraperCLI()
    exit_code = asyncio.run(cli.run())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
