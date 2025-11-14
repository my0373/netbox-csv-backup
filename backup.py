import os
import csv
import yaml
import re
from pathlib import Path
from dotenv import load_dotenv
import pynetbox

# Load environment variables from .env file
load_dotenv()


def get_netbox_endpoint(nb, object_type):
    """
    Map object type from config filename to NetBox API endpoint.
    
    Args:
        nb: pynetbox API instance
        object_type: string like 'regions', 'sites', etc.
    
    Returns:
        NetBox API endpoint object
    """
    # Map common object types to their NetBox API paths
    endpoint_map = {
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
    
    # Try exact match first
    if object_type in endpoint_map:
        return endpoint_map[object_type]
    
    # Try with underscores instead of hyphens
    object_type_underscore = object_type.replace('-', '_')
    if object_type_underscore in endpoint_map:
        return endpoint_map[object_type_underscore]
    
    # Try to find by attribute name (for dynamic discovery)
    # This handles cases like 'device-types' -> nb.dcim.device_types
    parts = object_type.split('-')
    if len(parts) == 2:
        module, resource = parts
        if hasattr(nb, module):
            module_obj = getattr(nb, module)
            resource_attr = resource.replace('-', '_')
            if hasattr(module_obj, resource_attr):
                return getattr(module_obj, resource_attr)
    
    raise ValueError(f"Unknown object type: {object_type}")


def extract_field_value(obj, field):
    """
    Extract a field value from a NetBox object, handling nested objects.
    
    Args:
        obj: NetBox API object
        field: field name to extract
    
    Returns:
        Field value (string or None)
    """
    value = getattr(obj, field, None)
    
    if value is None:
        return ''
    
    # Handle nested objects (region, group, tenant, parent, etc.)
    if hasattr(value, 'name'):
        return value.name
    elif hasattr(value, 'slug'):
        return value.slug
    elif hasattr(value, 'id'):
        return value.id
    
    # Handle lists (like tags)
    if isinstance(value, list):
        if len(value) == 0:
            return ''
        # For tags, extract slug if available, otherwise use string representation
        tag_values = []
        for item in value:
            if hasattr(item, 'slug'):
                tag_values.append(str(item.slug))
            elif hasattr(item, 'name'):
                tag_values.append(str(item.name))
            else:
                tag_values.append(str(item))
        return ','.join(tag_values)
    
    # Handle other types
    return str(value) if value is not None else ''


def backup_from_config(config_path, nb):
    """
    Export NetBox data to CSV based on a YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file
        nb: pynetbox API instance
    """
    # Read the YAML configuration file
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    fields = config.get('fields', [])
    if not fields:
        raise ValueError(f"No fields specified in configuration file: {config_path}")
    
    # Extract object type from filename (e.g., "1-regions.yml" -> "regions")
    filename = config_path.stem  # Gets "1-regions" without extension
    match = re.match(r'\d+-(.+)', filename)
    if not match:
        raise ValueError(f"Invalid config filename format: {config_path.name}. Expected format: 'N-objecttype.yml'")
    
    object_type = match.group(1)
    
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
    output_filename = f"{filename}.csv"
    output_path = Path('output') / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to CSV with proper quoting for fields containing newlines, commas, or quotes
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        # Use QUOTE_ALL to quote all fields, ensuring proper handling of newlines,
        # commas, and quotes. This guarantees all fields are properly enclosed.
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
                value = extract_field_value(obj, field)
                # Ensure the value is a string - QUOTE_ALL will quote everything
                # Convert all values to strings to ensure consistent handling
                if value is None or value == '':
                    row[field] = ''
                else:
                    # Always convert to string and flatten newlines to spaces
                    # so multi-line fields stay on a single CSV line
                    str_value = str(value)
                    # Replace newlines and carriage returns with spaces
                    str_value = str_value.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
                    # Collapse multiple spaces into single space
                    str_value = ' '.join(str_value.split())
                    row[field] = str_value
            
            writer.writerow(row)
    
    print(f"Successfully exported {len(objects)} {object_type} to {output_path}")


def backup_all():
    """
    Iterate over all YAML configuration files in conf/ directory,
    sorted by numerical prefix, and export each to CSV.
    """
    # Get NetBox connection details from environment variables
    netbox_url = os.getenv('NETBOX_URL') or os.getenv('NB_URL')
    netbox_api_key = os.getenv('NETBOX_API_KEY') or os.getenv('NB_API_KEY') or os.getenv('NETBOX_TOKEN')
    
    if not netbox_url:
        raise ValueError("NETBOX_URL or NB_URL environment variable is required")
    if not netbox_api_key:
        raise ValueError("NETBOX_API_KEY, NB_API_KEY, or NETBOX_TOKEN environment variable is required")
    
    # Connect to NetBox
    nb = pynetbox.api(netbox_url, token=netbox_api_key)
    
    # Find all YAML files in conf/ directory
    conf_dir = Path('conf')
    if not conf_dir.exists():
        raise ValueError("conf/ directory does not exist")
    
    config_files = list(conf_dir.glob('*.yml')) + list(conf_dir.glob('*.yaml'))
    
    if not config_files:
        print("No YAML configuration files found in conf/ directory")
        return
    
    # Sort by numerical prefix (the number before the dash)
    def get_sort_key(path):
        match = re.match(r'(\d+)-', path.name)
        if match:
            return int(match.group(1))
        return float('inf')  # Put files without numeric prefix at the end
    
    config_files.sort(key=get_sort_key)
    
    # Process each configuration file
    for config_path in config_files:
        backup_from_config(config_path, nb)


if __name__ == '__main__':
    backup_all()
