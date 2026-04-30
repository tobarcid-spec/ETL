# ETL Project Structure

This repository contains ETL scripts for various platforms used in media digital operations.

## Configuration

Database configuration is centralized in `config/config.py`. All scripts import `DB_CONFIG` from there.

To modify database credentials, edit `config/config.py`.

## Folder Structure

- `config/` - Centralized configuration files
- `c13/` - Scripts related to Canal 13 (C13) platform
- `t13/` - Scripts related to T13 platform
- `mango/` - Scripts for Mango API integrations
- `rudo/` - Scripts for Rudo video platform
- `facebook/` - Facebook-related ETL scripts
- `youtube/` - YouTube API integrations
- `tiktok/` - TikTok data scraping scripts
- `mercadolibre/` - MercadoLibre API scripts
- `rrss/` - Social media analysis scripts
- `flow/` - Workflow and payment scripts
- `general/` - General utility scripts
- `data/` - Data files and outputs
- `docs/` - Documentation

## Running Scripts

All scripts should be run from the project root directory (`c:\procesos\ETL`).

Example:
```
python youtube/youtube_playslist_auto.py
```
- `youtube/` - Scripts for YouTube API and playlist management
- `tiktok/` - Scripts for TikTok scraping and data extraction
- `facebook/` - Scripts for Facebook video and live imports
- `flow/` - Scripts for Flow payment platform
- `13go/` - Scripts for 13GO content synchronization
- `rrss/` - Scripts for social media (RRSS) data processing and sentiment analysis
- `mercadolibre/` - Scripts for MercadoLibre API integrations
- `data/` - Data files, reports, logs, and downloaded content
- `docs/` - Documentation, SQL queries, and analysis files
- `general/` - General utility scripts

## Getting Started

Refer to `docs/ANALISIS_COMPLETO_ARCHIVOS_PYTHON.md` for detailed information about each script.

## Requirements

- Python 3.x
- MySQL database access
- API keys for respective platforms (see docs for details)