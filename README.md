# NetBox Data Backup Script

This script connects to a NetBox instance and exports data to CSV files based on YAML configuration files. It iterates over all configuration files in the `conf/` directory, retrieves the specified fields from NetBox for each object type, and stores the extracted data in separate CSV files under the `output/` directory.

## Features

- Connects to NetBox using API key authentication
- Reads YAML configuration files that define which fields to export
- Handles nested objects (e.g., parent, region, tenant) and list fields (e.g., tags)
- Flattens multi-line data onto a single line for CSV compatibility
- Properly quotes all CSV fields to handle special characters
- Automatically sorts configuration files by numerical prefix
- Exports all specified fields plus an `id` field as the last column

## Python Dependencies

The script requires the following Python packages:

- `python-dotenv>=1.0.0` - For loading environment variables from `.env` file
- `pynetbox>=6.0.0` - NetBox Python API client
- `pyyaml>=6.0.0` - For parsing YAML configuration files

## Installation

1. Install the dependencies:

```bash
pip install -r requirements.txt
```

Or if using `uv`:

```bash
uv pip install -r requirements.txt
```

2. Create a `.env` file in the project root (see `.env.example` for reference):

```bash
cp .env.example .env
```

3. Edit the `.env` file with your NetBox instance URL and API key.

## Configuration

Configuration files are stored in the `conf/` directory. Each file should be named with a numerical prefix followed by a dash and the object type (e.g., `1-regions.yml`, `2-sites.yml`).

**Note:** The configuration files are believed to be in the correct order for loading data back into a NetBox instance (respecting dependencies between object types), but this ordering has not been fully tested. Use caution when importing the exported CSV files.

Each configuration file should follow this format:

```yaml
fields:
  - name
  - slug
  - description
  - tags
  - id
```

The `id` field will automatically be added as the last field if not already present.

## Usage

### Backup

Run the backup script to export all object types:

```bash
python backup.py
```

Or if using `uv`:

```bash
uv run python backup.py
```

**Export specific object types:**

You can export only specific object types to speed up testing:

```bash
# Using --type option (space-separated)
python backup.py --type tags regions sites

# Using individual flags
python backup.py --tags --regions --sites

# Export a single type
python backup.py --cables
python backup.py --event_rules
```

The script will:
1. Connect to your NetBox instance using credentials from `.env`
2. Read YAML configuration files from `conf/` directory (sorted numerically)
3. Filter to specified object types (if `--type` or individual flags are used)
4. Query NetBox for each object type
5. Export the specified fields to CSV files in `output/` directory
6. Generate one CSV file per configuration file (e.g., `1-regions.yml` → `output/1-regions.csv`)

**Available object types:**

Run `python backup.py --help` to see all available object types and their corresponding flags.

## Output

CSV files are written to the `output/` directory with the same naming convention as the configuration files. All fields are properly quoted to handle special characters and multi-line data is flattened onto a single line.

## Example

Given a configuration file `conf/5-regions.yml`:

```yaml
fields:
  - name
  - slug
  - parent
  - description
  - tags
  - id
```

Running the script will:
- Query NetBox for all regions
- Extract the specified fields
- Write the data to `output/5-regions.csv`

