# NetBox Data Backup Script

> [!WARNING]
> The CSV import process has only been tested up to **locations**.  
> Anything beyond this point is currently **untested**.

> [!NOTE]
> **Limitations:** This script does not currently support:
> - Custom fields
> - Custom objects

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

Given a configuration file `conf/7-regions.yml`:

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
- Write the data to `output/7-regions.csv`

## Exportable Object Types

The following table lists all object types that can be exported, along with their command-line flags and output file names:

| # | Object Type | Flag | Output File |
|---|-------------|------|-------------|
| 1 | tags | `--tags` | `output/1-tags.csv` |
| 2 | data-sources | `--data_sources` | `output/2-data-sources.csv` |
| 3 | webhooks | `--webhooks` | `output/3-webhooks.csv` |
| 4 | event-rules | `--event_rules` | `output/4-event-rules.csv` |
| 5 | tenant-groups | `--tenant_groups` | `output/5-tenant-groups.csv` |
| 6 | tenants | `--tenants` | `output/6-tenants.csv` |
| 7 | regions | `--regions` | `output/7-regions.csv` |
| 8 | sites | `--sites` | `output/8-sites.csv` |
| 9 | site-groups | `--site_groups` | `output/9-site-groups.csv` |
| 10 | locations | `--locations` | `output/10-locations.csv` |
| 11 | contact-groups | `--contact_groups` | `output/11-contact-groups.csv` |
| 12 | contact-roles | `--contact_roles` | `output/12-contact-roles.csv` |
| 13 | contacts | `--contacts` | `output/13-contacts.csv` |
| 14 | contact-assignments | `--contact_assignments` | `output/14-contact-assignments.csv` |
| 15 | manufacturers | `--manufacturers` | `output/15-manufacturers.csv` |
| 16 | device-types | `--device_types` | `output/16-device-types.csv` |
| 17 | module-type-profiles | `--module_type_profiles` | `output/17-module-type-profiles.csv` |
| 18 | module-types | `--module_types` | `output/18-module-types.csv` |
| 19 | device-roles | `--device_roles` | `output/19-device-roles.csv` |
| 20 | rack-types | `--rack_types` | `output/20-rack-types.csv` |
| 21 | rack-roles | `--rack_roles` | `output/21-rack-roles.csv` |
| 22 | racks | `--racks` | `output/22-racks.csv` |
| 23 | reservations | `--reservations` | `output/23-reservations.csv` |
| 24 | devices | `--devices` | `output/24-devices.csv` |
| 25 | export-templates | `--export_templates` | `output/25-export-templates.csv` |
| 26 | modules | `--modules` | `output/26-modules.csv` |
| 27 | config-templates | `--config_templates` | `output/27-config-templates.csv` |
| 28 | platforms | `--platforms` | `output/28-platforms.csv` |
| 29 | virtual-chassis | `--virtual_chassis` | `output/29-virtual-chassis.csv` |
| 30 | virtual-device-contexts | `--virtual_device_contexts` | `output/30-virtual-device-contexts.csv` |
| 31 | rirs | `--rirs` | `output/31-rirs.csv` |
| 32 | aggregates | `--aggregates` | `output/32-aggregates.csv` |
| 33 | vrfs | `--vrfs` | `output/33-vrfs.csv` |
| 34 | route-targets | `--route_targets` | `output/34-route-targets.csv` |
| 35 | vlan-groups | `--vlan_groups` | `output/35-vlan-groups.csv` |
| 36 | vlans | `--vlans` | `output/36-vlans.csv` |
| 37 | vlan-translation-policies | `--vlan_translation_policies` | `output/37-vlan-translation-policies.csv` |
| 38 | vlan-translation-rules | `--vlan_translation_rules` | `output/38-vlan-translation-rules.csv` |
| 39 | asns | `--asns` | `output/39-asns.csv` |
| 40 | asn-ranges | `--asn_ranges` | `output/40-asn-ranges.csv` |
| 41 | roles | `--roles` | `output/41-roles.csv` |
| 42 | prefixes | `--prefixes` | `output/42-prefixes.csv` |
| 43 | ip-ranges | `--ip_ranges` | `output/43-ip-ranges.csv` |
| 44 | ip-addresses | `--ip_addresses` | `output/44-ip-addresses.csv` |
| 45 | fhrp-groups | `--fhrp_groups` | `output/45-fhrp-groups.csv` |
| 46 | service-templates | `--service_templates` | `output/46-service-templates.csv` |
| 47 | services | `--services` | `output/47-services.csv` |
| 48 | inventory-item-roles | `--inventory_item_roles` | `output/48-inventory-item-roles.csv` |
| 49 | inventory-items | `--inventory_items` | `output/49-inventory-items.csv` |
| 50 | rear-ports | `--rear_ports` | `output/50-rear-ports.csv` |
| 51 | front-ports | `--front_ports` | `output/51-front-ports.csv` |
| 52 | console-ports | `--console_ports` | `output/52-console-ports.csv` |
| 53 | console-server-ports | `--console_server_ports` | `output/53-console-server-ports.csv` |
| 54 | power-ports | `--power_ports` | `output/54-power-ports.csv` |
| 55 | power-outlets | `--power_outlets` | `output/55-power-outlets.csv` |
| 56 | module-bays | `--module_bays` | `output/56-module-bays.csv` |
| 57 | device-bays | `--device_bays` | `output/57-device-bays.csv` |
| 58 | interfaces | `--interfaces` | `output/58-interfaces.csv` |
| 59 | mac-addresses | `--mac_addresses` | `output/59-mac-addresses.csv` |
| 60 | cables | `--cables` | `output/60-cables.csv` |
| 61 | wireless-links | `--wireless_links` | `output/61-wireless-links.csv` |
| 62 | wireless-lan-groups | `--wireless_lan_groups` | `output/62-wireless-lan-groups.csv` |
| 63 | wireless-lans | `--wireless_lans` | `output/63-wireless-lans.csv` |
| 64 | vpn-tunnel-groups | `--vpn_tunnel_groups` | `output/64-vpn-tunnel-groups.csv` |
| 65 | vpn-tunnels | `--vpn_tunnels` | `output/65-vpn-tunnels.csv` |
| 66 | tunnel-terminations | `--tunnel_terminations` | `output/66-tunnel-terminations.csv` |
| 67 | l2vpn | `--l2vpn` | `output/67-l2vpn.csv` |
| 68 | l2vpn-terminations | `--l2vpn_terminations` | `output/68-l2vpn-terminations.csv` |
| 69 | ike-proposals | `--ike_proposals` | `output/69-ike-proposals.csv` |
| 70 | ike-policies | `--ike_policies` | `output/70-ike-policies.csv` |
| 71 | ipsec-proposals | `--ipsec_proposals` | `output/71-ipsec-proposals.csv` |
| 72 | ipsec-policies | `--ipsec_policies` | `output/72-ipsec-policies.csv` |
| 73 | ipsec-profiles | `--ipsec_profiles` | `output/73-ipsec-profiles.csv` |
| 74 | cluster-groups | `--cluster_groups` | `output/74-cluster-groups.csv` |
| 75 | cluster-types | `--cluster_types` | `output/75-cluster-types.csv` |
| 76 | clusters | `--clusters` | `output/76-clusters.csv` |
| 77 | virtual-machines | `--virtual_machines` | `output/77-virtual-machines.csv` |
| 78 | vm-interfaces | `--vm_interfaces` | `output/78-vm-interfaces.csv` |
| 79 | virtual-disks | `--virtual_disks` | `output/79-virtual-disks.csv` |
| 80 | circuit-providers | `--circuit_providers` | `output/80-circuit-providers.csv` |
| 81 | circuit-provider-accounts | `--circuit_provider_accounts` | `output/81-circuit-provider-accounts.csv` |
| 82 | circuit-groups | `--circuit_groups` | `output/82-circuit-groups.csv` |
| 83 | circuit-types | `--circuit_types` | `output/83-circuit-types.csv` |
| 84 | circuits | `--circuits` | `output/84-circuits.csv` |
| 85 | circuit-terminations | `--circuit_terminations` | `output/85-circuit-terminations.csv` |
| 86 | provider-networks | `--provider_networks` | `output/86-provider-networks.csv` |
| 87 | virtual-circuits | `--virtual_circuits` | `output/87-virtual-circuits.csv` |
| 88 | virtual-circuit-terminations | `--virtual_circuit_terminations` | `output/88-virtual-circuit-terminations.csv` |
| 89 | circuit-assignments | `--circuit_assignments` | `output/89-circuit-assignments.csv` |
| 90 | power-panels | `--power_panels` | `output/90-power-panels.csv` |
| 91 | power-feeds | `--power_feeds` | `output/91-power-feeds.csv` |

