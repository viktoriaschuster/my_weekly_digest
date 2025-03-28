#!/usr/bin/env python3

import sys
import os
import logging
import datetime
import json
import argparse
from pathlib import Path

# Add the src directory to the Python path
base_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(base_dir / "src"))

# Import the scrapers
from scrapers import arxiv_scraper, biorxiv_scraper, blog_scraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("my_weekly_digest")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate research digest for specified time interval.")
    
    # Add interval argument
    parser.add_argument(
        '--interval',
        type=str,
        choices=['weekly', 'biweekly', 'monthly'],
        default='weekly',
        help='Time interval for the digest: weekly (7 days), biweekly (14 days), or monthly (30 days)'
    )
    
    # Add max results arguments
    parser.add_argument(
        '--max-papers',
        type=int,
        default=20,
        help='Maximum number of papers to include per source'
    )
    
    # Add output file option
    parser.add_argument(
        '--output',
        type=str,
        help='Custom output filename (default: digest_YYYYMMDD.json)'
    )
    
    return parser.parse_args()

def main():
    """Run scrapers and generate digest based on command-line arguments."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Determine date range based on interval
    end_date = datetime.datetime.now()
    
    if args.interval == 'weekly':
        days = 7
        interval_name = "Weekly"
    elif args.interval == 'biweekly':
        days = 14
        interval_name = "Biweekly"
    elif args.interval == 'monthly':
        days = 30
        interval_name = "Monthly"
    else:
        logger.error("Invalid interval specified. Use 'weekly', 'biweekly', or 'monthly'.")
        sys.exit(1)
    
    start_date = end_date - datetime.timedelta(days=days)
    
    logger.info(f"Generating {interval_name} Digest")
    logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Run arXiv scraper
    logger.info("Scraping arXiv...")
    arxiv_papers = arxiv_scraper.scrape_arxiv(start_date, end_date, max_results=args.max_papers)
    logger.info(f"Found {len(arxiv_papers)} papers on arXiv")
    
    # Run bioRxiv scraper
    logger.info("Scraping bioRxiv...")
    biorxiv_papers = biorxiv_scraper.scrape_biorxiv(start_date, end_date, max_papers=args.max_papers)
    logger.info(f"Found {len(biorxiv_papers)} papers on bioRxiv")
    
    # Run blog scraper
    logger.info("Scraping research blogs...")
    blog_entries = blog_scraper.scrape_blogs(start_date, end_date, max_entries=args.max_papers)
    logger.info(f"Found {len(blog_entries)} blog entries")
    
    # Combine results
    all_content = arxiv_papers + biorxiv_papers + blog_entries
    logger.info(f"Total content found: {len(all_content)}")
    
    # Save results
    output_dir = base_dir / "data" / "raw"
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine output filename
    if args.output:
        output_file = output_dir / args.output
    else:
        output_file = output_dir / f"{args.interval}_digest_{end_date.strftime('%Y%m%d')}.json"
    
    # Create metadata
    digest_data = {
        "metadata": {
            "interval": args.interval,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "generation_date": end_date.strftime('%Y-%m-%d'),
            "total_entries": len(all_content)
        },
        "entries": all_content
    }
    
    with open(output_file, 'w') as f:
        json.dump(digest_data, f, indent=2)
    
    logger.info(f"Digest saved to {output_file}")
    logger.info("Digest generation completed")

if __name__ == "__main__":
    main()