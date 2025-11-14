import os
import csv
import yaml
import re
import argparse
import sys
import urllib3
from pathlib import Path
from dotenv import load_dotenv
import pynetbox

# Load environment variables from .env file
load_dotenv()

# Constants
VALUE_PREFERRED_FIELDS = ['action_type', 'status']
RELATIONSHIP_NAME_FIELDS = [
    'parent', 'region', 'tenant', 'site', 'location', 'rack',
    'manufacturer', 'device_type', 'device_role', 'role', 'platform',
    'cluster', 'cluster_type', 'cluster_group', 'circuit', 'circuit_type',
    'circuit_provider', 'provider', 'virtual_chassis', 'config_template',
    'fhrp_group', 'l2vpn', 'virtual_circuit', 'vrf', 'group'
]
CABLE_TERMINATION_FIELDS = {
    'side_a_device', 'side_a_type', 'side_a_name', 'side_a_site',
    'side_b_device', 'side_b_type', 'side_b_name', 'side_b_site'
}
WIRELESS_LINK_FIELDS = {
    'device_a', 'interface_a', 'site_a', 'device_b', 'interface_b', 'site_b'
}
ASSIGNED_OBJECT_FIELDS = {'device', 'virtual_machine', 'interface'}


def build_endpoint_map(nb):
    """Build the mapping of object types to NetBox API endpoints."""
    return {
        'tags': nb.extras.tags,
        'data-sources': nb.core.data_sources,
        'webhooks': nb.extras.webhooks,
        'event-rules': nb.extras.event_rules,
        'config-templates': nb.extras.config_templates,
        'export-templates': nb.extras.export_templates,
        'regions': nb.dcim.regions,
        'sites': nb.dcim.sites,
        'site-groups': nb.dcim.site_groups,
        'locations': nb.dcim.locations,
        'racks': nb.dcim.racks,
        'devices': nb.dcim.devices,
        'virtual-chassis': nb.dcim.virtual_chassis,
        'virtual-device-contexts': nb.dcim.virtual_device_contexts,
        'platforms': nb.dcim.platforms,
        'modules': nb.dcim.modules,
        'inventory-item-roles': nb.dcim.inventory_item_roles,
        'inventory-items': nb.dcim.inventory_items,
        'rear-ports': nb.dcim.rear_ports,
        'front-ports': nb.dcim.front_ports,
        'console-ports': nb.dcim.console_ports,
        'console-server-ports': nb.dcim.console_server_ports,
        'power-ports': nb.dcim.power_ports,
        'power-outlets': nb.dcim.power_outlets,
        'power-panels': nb.dcim.power_panels,
        'power-feeds': nb.dcim.power_feeds,
        'module-bays': nb.dcim.module_bays,
        'device-bays': nb.dcim.device_bays,
        'interfaces': nb.dcim.interfaces,
        'mac-addresses': nb.dcim.mac_addresses,
        'cables': nb.dcim.cables,
        'wireless-links': nb.wireless.wireless_links,
        'wireless-lan-groups': nb.wireless.wireless_lan_groups,
        'wireless-lans': nb.wireless.wireless_lans,
        'vpn-tunnel-groups': nb.vpn.tunnel_groups,
        'vpn-tunnels': nb.vpn.tunnels,
        'tunnel-terminations': nb.vpn.tunnel_terminations,
        'l2vpn': nb.vpn.l2vpns,
        'l2vpn-terminations': nb.vpn.l2vpn_terminations,
        'ike-proposals': nb.vpn.ike_proposals,
        'ike-policies': nb.vpn.ike_policies,
        'ipsec-proposals': nb.vpn.ipsec_proposals,
        'ipsec-policies': nb.vpn.ipsec_policies,
        'ipsec-profiles': nb.vpn.ipsec_profiles,
        'cluster-groups': nb.virtualization.cluster_groups,
        'cluster-types': nb.virtualization.cluster_types,
        'clusters': nb.virtualization.clusters,
        'virtual-machines': nb.virtualization.virtual_machines,
        'vm-interfaces': nb.virtualization.interfaces,
        'virtual-disks': nb.virtualization.virtual_disks,
        'manufacturers': nb.dcim.manufacturers,
        'device-types': nb.dcim.device_types,
        'module-type-profiles': nb.dcim.module_type_profiles,
        'module-types': nb.dcim.module_types,
        'device-roles': nb.dcim.device_roles,
        'rack-types': nb.dcim.rack_types,
        'rack-roles': nb.dcim.rack_roles,
        'reservations': nb.dcim.rack_reservations,
        'circuits': nb.circuits.circuits,
        'circuit-providers': nb.circuits.providers,
        'providers': nb.circuits.providers,
        'circuit-provider-accounts': nb.circuits.provider_accounts,
        'circuit-groups': nb.circuits.circuit_groups,
        'circuit-types': nb.circuits.circuit_types,
        'circuit-terminations': nb.circuits.circuit_terminations,
        'provider-networks': nb.circuits.provider_networks,
        'virtual-circuits': nb.circuits.virtual_circuits,
        'virtual-circuit-terminations': nb.circuits.virtual_circuit_terminations,
        'circuit-assignments': nb.circuits.circuit_group_assignments,
        'tenants': nb.tenancy.tenants,
        'tenant-groups': nb.tenancy.tenant_groups,
        'contacts': nb.tenancy.contacts,
        'contact-groups': nb.tenancy.contact_groups,
        'contact-roles': nb.tenancy.contact_roles,
        'contact-assignments': nb.tenancy.contact_assignments,
        'vlan-groups': nb.ipam.vlan_groups,
        'vlans': nb.ipam.vlans,
        'vlan-translation-policies': nb.ipam.vlan_translation_policies,
        'vlan-translation-rules': nb.ipam.vlan_translation_rules,
        'vrfs': nb.ipam.vrfs,
        'route-targets': nb.ipam.route_targets,
        'prefixes': nb.ipam.prefixes,
        'roles': nb.ipam.roles,
        'ip-addresses': nb.ipam.ip_addresses,
        'ip-ranges': nb.ipam.ip_ranges,
        'fhrp-groups': nb.ipam.fhrp_groups,
        'service-templates': nb.ipam.service_templates,
        'services': nb.ipam.services,
        'asns': nb.ipam.asns,
        'asn-ranges': nb.ipam.asn_ranges,
        'rirs': nb.ipam.rirs,
        'aggregates': nb.ipam.aggregates,
    }


def get_netbox_endpoint(nb, object_type):
    """
    Map object type from config filename to NetBox API endpoint.
    
    Args:
        nb: pynetbox API instance
        object_type: string like 'regions', 'sites', etc.
    
    Returns:
        NetBox API endpoint object
    
    Raises:
        ValueError: If object type cannot be mapped to an endpoint
    """
    endpoint_map = build_endpoint_map(nb)
    
    # Try exact match first
    if object_type in endpoint_map:
        return endpoint_map[object_type]
    
    # Try with underscores instead of hyphens
    object_type_underscore = object_type.replace('-', '_')
    if object_type_underscore in endpoint_map:
        return endpoint_map[object_type_underscore]
    
    # Try to find by attribute name (for dynamic discovery)
    parts = object_type.split('-')
    if len(parts) == 2:
        module, resource = parts
        if hasattr(nb, module):
            module_obj = getattr(nb, module)
            resource_attr = resource.replace('-', '_')
            if hasattr(module_obj, resource_attr):
                return getattr(module_obj, resource_attr)
    
    raise ValueError(f"Unknown object type: {object_type}")


def get_assigned_object(obj):
    """Extract assigned_object from a NetBox object."""
    try:
        if hasattr(obj, 'assigned_object'):
            return getattr(obj, 'assigned_object', None)
        elif hasattr(obj, '__dict__'):
            obj_dict = dict(obj)
            return obj_dict.get('assigned_object')
    except Exception:
        pass
    return None


def extract_from_assigned_object(assigned_obj, field):
    """Extract device/virtual_machine/interface from assigned_object."""
    if not assigned_obj:
        return ''
    
    if isinstance(assigned_obj, dict):
        if field == 'device':
            device = assigned_obj.get('device')
            if device:
                return device.get('name', '') if isinstance(device, dict) else getattr(device, 'name', '')
        elif field == 'virtual_machine':
            vm = assigned_obj.get('virtual_machine')
            if vm:
                return vm.get('name', '') if isinstance(vm, dict) else getattr(vm, 'name', '')
        elif field == 'interface':
            return str(assigned_obj.get('name', ''))
    else:
        # pynetbox object
        if field == 'device':
            device = getattr(assigned_obj, 'device', None)
            return getattr(device, 'name', '') if device and hasattr(device, 'name') else ''
        elif field == 'virtual_machine':
            vm = getattr(assigned_obj, 'virtual_machine', None)
            return getattr(vm, 'name', '') if vm and hasattr(vm, 'name') else ''
        elif field == 'interface':
            return str(getattr(assigned_obj, 'name', ''))
    
    return ''


def extract_wireless_link_field(obj, field):
    """Extract wireless link fields (device_a, interface_a, site_a, etc.)."""
    side = 'a' if field.endswith('_a') else 'b'
    interface_attr = f'interface_{side}'
    interface = getattr(obj, interface_attr, None)
    
    if not interface:
        return ''
    
    if field.startswith('device_'):
        device = getattr(interface, 'device', None)
        return getattr(device, 'name', '') if device and hasattr(device, 'name') else ''
    elif field.startswith('interface_'):
        return str(getattr(interface, 'name', ''))
    elif field.startswith('site_'):
        device = getattr(interface, 'device', None)
        if device:
            site = getattr(device, 'site', None)
            return getattr(site, 'name', '') if site and hasattr(site, 'name') else ''
    
    return ''


def extract_cable_termination_field(obj, field):
    """Extract cable termination fields (side_a_device, side_b_name, etc.)."""
    side = 'a' if 'side_a' in field else 'b'
    terminations_attr = f'{side}_terminations'
    terminations = getattr(obj, terminations_attr, [])
    
    if not terminations or len(terminations) == 0:
        return ''
    
    term = terminations[0]
    
    if field.endswith('_device'):
        device = getattr(term, 'device', None)
        return getattr(device, 'name', '') if device and hasattr(device, 'name') else ''
    elif field.endswith('_type'):
        return str(getattr(term, 'type', '')) if getattr(term, 'type', None) else ''
    elif field.endswith('_name'):
        return str(getattr(term, 'name', '')) if getattr(term, 'name', None) else ''
    elif field.endswith('_site'):
        device = getattr(term, 'device', None)
        if device:
            site = getattr(device, 'site', None)
            return getattr(site, 'name', '') if site and hasattr(site, 'name') else ''
    
    return ''


def extract_relationship_name(value):
    """Extract name from a relationship field (parent, region, tenant, etc.)."""
    if isinstance(value, dict):
        return str(value.get('name', value.get('id', '')))
    elif hasattr(value, 'name'):
        return value.name
    elif hasattr(value, 'id'):
        return value.id
    return ''


def extract_record_value(value_dict, field):
    """Extract value from a pynetbox Record object (choice fields like status, action_type)."""
    if field in VALUE_PREFERRED_FIELDS:
        # Prefer 'value' for CSV import compatibility
        return str(value_dict.get('value', '')) or str(value_dict.get('label', ''))
    else:
        # Prefer 'label' for display fields
        return str(value_dict.get('label', '')) or str(value_dict.get('value', '')) or str(list(value_dict.values())[0] if value_dict else '')


def extract_dict_value(value, field):
    """Extract value from a dict (choice fields like status, action_type)."""
    if field in VALUE_PREFERRED_FIELDS:
        return str(value.get('value', '')) or str(value.get('label', ''))
    else:
        return str(value.get('label', '')) or str(value.get('value', '')) or str(list(value.values())[0] if value else '')


def extract_list_value(value):
    """Extract value from a list (like tags)."""
    if not value:
        return ''
    
    tag_values = []
    for item in value:
        if hasattr(item, 'slug'):
            tag_values.append(str(item.slug))
        elif hasattr(item, 'name'):
            tag_values.append(str(item.name))
        else:
            tag_values.append(str(item))
    return ','.join(tag_values)


def extract_nested_object_value(value):
    """Extract value from a nested object (has name, slug, or id)."""
    if hasattr(value, 'name'):
        return value.name
    elif hasattr(value, 'slug'):
        return value.slug
    elif hasattr(value, 'id'):
        return value.id
    return ''


def extract_field_value(obj, field):
    """
    Extract a field value from a NetBox object, handling nested objects.
    
    Args:
        obj: NetBox API object
        field: field name to extract
    
    Returns:
        Field value (string)
    """
    # Special handling for assigned_object fields (MAC/IP addresses)
    if field in ASSIGNED_OBJECT_FIELDS:
        assigned_obj = get_assigned_object(obj)
        if assigned_obj:
            result = extract_from_assigned_object(assigned_obj, field)
            if result:
                return result
    
    # Special handling for wireless-link fields
    if field in WIRELESS_LINK_FIELDS and (hasattr(obj, 'interface_a') or hasattr(obj, 'interface_b')):
        result = extract_wireless_link_field(obj, field)
        if result:
            return result
    
    # Special handling for cable termination fields
    if field in CABLE_TERMINATION_FIELDS and (hasattr(obj, 'a_terminations') or hasattr(obj, 'b_terminations')):
        result = extract_cable_termination_field(obj, field)
        if result:
            return result
    
    # Get the base value
    value = getattr(obj, field, None)
    
    if value is None:
        return ''
    
    # Special handling for relationship fields that should export names (not IDs)
    # These must be checked before Record-to-dict conversion
    if field in RELATIONSHIP_NAME_FIELDS:
        result = extract_relationship_name(value)
        if result:
            return result
    
    # Handle pynetbox Record objects (choice fields)
    if hasattr(value, '__class__') and 'Record' in str(type(value)):
        try:
            value_dict = dict(value)
            if isinstance(value_dict, dict):
                return extract_record_value(value_dict, field)
        except Exception:
            pass
    
    # Handle dict values (choice fields)
    if isinstance(value, dict):
        return extract_dict_value(value, field)
    
    # Special handling for action_object in event rules
    if field == 'action_object':
        if isinstance(value, dict):
            return str(value.get('name', value.get('id', '')))
        if hasattr(value, 'name'):
            return value.name
    
    # Handle nested objects
    if hasattr(value, 'name') or hasattr(value, 'slug') or hasattr(value, 'id'):
        result = extract_nested_object_value(value)
        if result:
            return result
    
    # Handle lists (like tags)
    if isinstance(value, list):
        return extract_list_value(value)
    
    # Handle other types
    return str(value) if value is not None else ''


def normalize_string_value(value):
    """Normalize string value for CSV export (flatten newlines, collapse spaces)."""
    if value is None or value == '':
        return ''
    
    str_value = str(value)
    # Replace newlines and carriage returns with spaces
    str_value = str_value.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
    # Collapse multiple spaces into single space
    return ' '.join(str_value.split())


def parse_object_type_from_filename(filename):
    """Extract object type from config filename (e.g., '1-regions.yml' -> 'regions')."""
    match = re.match(r'\d+-(.+)', filename)
    if not match:
        raise ValueError(f"Invalid config filename format: {filename}. Expected format: 'N-objecttype.yml'")
    return match.group(1)


def get_config_sort_key(path):
    """Get sort key for config files (by numerical prefix)."""
    match = re.match(r'(\d+)-', path.name)
    return int(match.group(1)) if match else float('inf')


def normalize_object_types(object_types):
    """Normalize object types (handle both 'tags' and '1-tags' formats)."""
    normalized = set()
    for ot in object_types:
        match = re.match(r'\d+-(.+)', ot)
        normalized.add(match.group(1) if match else ot)
    return normalized


def load_config(config_path):
    """Load and validate YAML configuration file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    fields = config.get('fields', [])
    if not fields:
        raise ValueError(f"No fields specified in configuration file: {config_path}")
    
    # Remove 'id' field from fields list
    fields = [f for f in fields if f != 'id']
    
    if not fields:
        raise ValueError(f"No fields remaining after removing 'id' from configuration file: {config_path}")
    
    return fields


def create_netbox_connection():
    """Create and configure NetBox API connection."""
    netbox_url = os.getenv('NETBOX_URL') or os.getenv('NB_URL')
    netbox_api_key = os.getenv('NETBOX_API_KEY') or os.getenv('NB_API_KEY') or os.getenv('NETBOX_TOKEN')
    
    if not netbox_url:
        raise ValueError("NETBOX_URL or NB_URL environment variable is required")
    if not netbox_api_key:
        raise ValueError("NETBOX_API_KEY, NB_API_KEY, or NETBOX_TOKEN environment variable is required")
    
    nb = pynetbox.api(netbox_url, token=netbox_api_key)
    
    # Disable SSL verification if needed
    ssl_verify = os.getenv('NETBOX_SSL_VERIFY', 'true').lower() not in ('false', '0', 'no')
    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        nb.http_session.verify = False
    
    return nb


def backup_from_config(config_path, nb):
    """
    Export NetBox data to CSV based on a YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file
        nb: pynetbox API instance
    """
    try:
        fields = load_config(config_path)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Extract object type from filename
    try:
        object_type = parse_object_type_from_filename(config_path.stem)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Get the NetBox API endpoint
    try:
        endpoint = get_netbox_endpoint(nb, object_type)
    except ValueError as e:
        print(f"Warning: {e}. Skipping {config_path.name}")
        return
    
    # Get all objects from NetBox
    try:
        objects = list(endpoint.all())
    except Exception as e:
        print(f"Error querying NetBox for {object_type}: {e}. Skipping {config_path.name}")
        return
    
    # Prepare output directory and file
    output_filename = f"{config_path.stem}.csv"
    output_path = Path('output') / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fields,
            quoting=csv.QUOTE_ALL,
            doublequote=True
        )
        writer.writeheader()
        
        for obj in objects:
            row = {}
            for field in fields:
                # Skip 'id' field if it somehow got through
                if field == 'id':
                    continue
                
                # Special handling for action_object
                if field == 'action_object':
                    ao = getattr(obj, 'action_object', None)
                    if ao:
                        if hasattr(ao, 'name'):
                            value = ao.name
                        elif isinstance(ao, dict) and 'name' in ao:
                            value = ao['name']
                        else:
                            value = extract_field_value(obj, field)
                    else:
                        value = ''
                else:
                    value = extract_field_value(obj, field)
                
                row[field] = normalize_string_value(value)
            
            writer.writerow(row)
    
    print(f"Successfully exported {len(objects)} {object_type} to {output_path}")


def find_config_files(conf_dir, object_types=None):
    """Find and filter configuration files."""
    config_files = list(conf_dir.glob('*.yml')) + list(conf_dir.glob('*.yaml'))
    
    if not config_files:
        return []
    
    # Sort by numerical prefix
    config_files.sort(key=get_config_sort_key)
    
    # Filter by object types if specified
    if object_types:
        normalized_types = normalize_object_types(object_types)
        filtered_files = []
        for config_path in config_files:
            try:
                obj_type = parse_object_type_from_filename(config_path.stem)
                if obj_type in normalized_types:
                    filtered_files.append(config_path)
            except ValueError:
                continue
        
        if not filtered_files:
            print(f"No configuration files found for object types: {', '.join(object_types)}")
            return []
        
        return filtered_files
    
    return config_files


def get_available_object_types(conf_dir):
    """Get all available object types from config files."""
    available_types = set()
    for pattern in ['*.yml', '*.yaml']:
        for config_file in conf_dir.glob(pattern):
            try:
                obj_type = parse_object_type_from_filename(config_file.stem)
                available_types.add(obj_type)
            except ValueError:
                continue
    return available_types


def setup_argument_parser(available_types):
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Export NetBox data to CSV files based on YAML configuration files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all object types
  python backup.py
  
  # Export specific object types
  python backup.py --type tags regions sites
  
  # Export using individual flags
  python backup.py --tags --regions --sites
  
  # Export cables only
  python backup.py --cables
        """
    )
    
    # Add --type option
    parser.add_argument(
        '--type', '--types',
        nargs='+',
        dest='object_types',
        help='Object types to export (e.g., tags regions sites). Can be specified multiple times or space-separated.'
    )
    
    # Add individual flags for each object type
    for obj_type in sorted(available_types):
        flag_name = obj_type.replace('-', '_')
        parser.add_argument(
            f'--{flag_name}',
            action='append_const',
            const=obj_type,
            dest='object_types',
            help=f'Export {obj_type}'
        )
    
    return parser


def parse_object_types(args):
    """Parse and normalize object types from command-line arguments."""
    if not args.object_types:
        return None
    
    object_types = []
    for ot in args.object_types:
        if isinstance(ot, list):
            object_types.extend(ot)
        else:
            object_types.append(ot)
    
    # Remove duplicates while preserving order
    seen = set()
    return [x for x in object_types if x and not (x in seen or seen.add(x))]


def backup_all(object_types=None):
    """
    Iterate over all YAML configuration files in conf/ directory,
    sorted by numerical prefix, and export each to CSV.
    
    Args:
        object_types: Optional list of object types to export (e.g., ['tags', 'regions']).
                     If None, exports all object types.
    """
    # Create NetBox connection
    nb = create_netbox_connection()
    
    # Find configuration files
    conf_dir = Path('conf')
    if not conf_dir.exists():
        raise ValueError("conf/ directory does not exist")
    
    config_files = find_config_files(conf_dir, object_types)
    
    if not config_files:
        print("No YAML configuration files found in conf/ directory")
        return
    
    # Process each configuration file
    for config_path in config_files:
        backup_from_config(config_path, nb)


def main():
    """Main entry point."""
    conf_dir = Path('conf')
    available_types = get_available_object_types(conf_dir) if conf_dir.exists() else set()
    
    parser = setup_argument_parser(available_types)
    args = parser.parse_args()
    
    object_types = parse_object_types(args)
    
    try:
        backup_all(object_types=object_types)
    except KeyboardInterrupt:
        print("\n\nBackup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
