import os
import csv
import yaml
import re
import argparse
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
    # Special handling for MAC addresses and IP addresses
    # These use assigned_object (generic foreign key) instead of direct device/virtual_machine/interface fields
    assigned_obj = None
    try:
        if hasattr(obj, 'assigned_object'):
            assigned_obj = getattr(obj, 'assigned_object', None)
        elif hasattr(obj, '__dict__'):
            obj_dict = dict(obj)
            if 'assigned_object' in obj_dict:
                assigned_obj = obj_dict['assigned_object']
    except:
        pass
    
    if assigned_obj and field in ['device', 'virtual_machine', 'interface']:
        # assigned_object can be a dict or a pynetbox object
        if isinstance(assigned_obj, dict):
            if field == 'device':
                device = assigned_obj.get('device')
                if device:
                    if isinstance(device, dict):
                        return device.get('name', '')
                    elif hasattr(device, 'name'):
                        return device.name
            elif field == 'virtual_machine':
                # Check if assigned_object is a VM interface
                if 'virtual_machine' in assigned_obj:
                    vm = assigned_obj['virtual_machine']
                    if isinstance(vm, dict):
                        return vm.get('name', '')
                    elif hasattr(vm, 'name'):
                        return vm.name
            elif field == 'interface':
                # Interface name is in assigned_object itself
                if 'name' in assigned_obj:
                    return str(assigned_obj['name'])
        else:
            # It's a pynetbox object
            if field == 'device':
                if hasattr(assigned_obj, 'device') and assigned_obj.device:
                    return assigned_obj.device.name if hasattr(assigned_obj.device, 'name') else str(assigned_obj.device)
            elif field == 'virtual_machine':
                if hasattr(assigned_obj, 'virtual_machine') and assigned_obj.virtual_machine:
                    return assigned_obj.virtual_machine.name if hasattr(assigned_obj.virtual_machine, 'name') else str(assigned_obj.virtual_machine)
            elif field == 'interface':
                if hasattr(assigned_obj, 'name'):
                    return str(assigned_obj.name)
        return ''  # Return empty if assigned_object exists but field not found
    
    # Special handling for wireless-link fields
    # Wireless links use interface_a and interface_b which are objects, not direct device_a/device_b fields
    if hasattr(obj, 'interface_a') or hasattr(obj, 'interface_b'):
        if field == 'device_a':
            if hasattr(obj, 'interface_a') and obj.interface_a:
                if hasattr(obj.interface_a, 'device') and obj.interface_a.device:
                    return obj.interface_a.device.name if hasattr(obj.interface_a.device, 'name') else str(obj.interface_a.device)
            return ''
        elif field == 'interface_a':
            if hasattr(obj, 'interface_a') and obj.interface_a:
                if hasattr(obj.interface_a, 'name'):
                    return str(obj.interface_a.name)
            return ''
        elif field == 'site_a':
            if hasattr(obj, 'interface_a') and obj.interface_a:
                if hasattr(obj.interface_a, 'device') and obj.interface_a.device:
                    device = obj.interface_a.device
                    if hasattr(device, 'site') and device.site:
                        return device.site.name if hasattr(device.site, 'name') else str(device.site)
            return ''
        elif field == 'device_b':
            if hasattr(obj, 'interface_b') and obj.interface_b:
                if hasattr(obj.interface_b, 'device') and obj.interface_b.device:
                    return obj.interface_b.device.name if hasattr(obj.interface_b.device, 'name') else str(obj.interface_b.device)
            return ''
        elif field == 'interface_b':
            if hasattr(obj, 'interface_b') and obj.interface_b:
                if hasattr(obj.interface_b, 'name'):
                    return str(obj.interface_b.name)
            return ''
        elif field == 'site_b':
            if hasattr(obj, 'interface_b') and obj.interface_b:
                if hasattr(obj.interface_b, 'device') and obj.interface_b.device:
                    device = obj.interface_b.device
                    if hasattr(device, 'site') and device.site:
                        return device.site.name if hasattr(device.site, 'name') else str(device.site)
            return ''
    
    # Special handling for cable termination fields
    # Cables use a_terminations and b_terminations (lists) instead of direct fields
    if hasattr(obj, 'a_terminations') or hasattr(obj, 'b_terminations'):
        if field == 'side_a_device':
            terminations = getattr(obj, 'a_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'device') and term.device:
                    return term.device.name if hasattr(term.device, 'name') else str(term.device)
            return ''
        elif field == 'side_a_type':
            terminations = getattr(obj, 'a_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'type'):
                    return str(term.type) if term.type else ''
            return ''
        elif field == 'side_a_name':
            terminations = getattr(obj, 'a_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'name'):
                    return str(term.name) if term.name else ''
            return ''
        elif field == 'side_a_site':
            terminations = getattr(obj, 'a_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'device') and term.device:
                    device = term.device
                    if hasattr(device, 'site') and device.site:
                        return device.site.name if hasattr(device.site, 'name') else str(device.site)
            return ''
        elif field == 'side_b_device':
            terminations = getattr(obj, 'b_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'device') and term.device:
                    return term.device.name if hasattr(term.device, 'name') else str(term.device)
            return ''
        elif field == 'side_b_type':
            terminations = getattr(obj, 'b_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'type'):
                    return str(term.type) if term.type else ''
            return ''
        elif field == 'side_b_name':
            terminations = getattr(obj, 'b_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'name'):
                    return str(term.name) if term.name else ''
            return ''
        elif field == 'side_b_site':
            terminations = getattr(obj, 'b_terminations', [])
            if terminations and len(terminations) > 0:
                term = terminations[0]
                if hasattr(term, 'device') and term.device:
                    device = term.device
                    if hasattr(device, 'site') and device.site:
                        return device.site.name if hasattr(device.site, 'name') else str(device.site)
            return ''
    
    value = getattr(obj, field, None)
    
    if value is None:
        return ''
    
    # Special handling for relationship fields that should export names (not IDs)
    # These must be checked before Record-to-dict conversion
    relationship_name_fields = ['parent', 'region', 'tenant', 'site', 'location', 'rack', 
                                'manufacturer', 'device_type', 'device_role', 'role', 'platform',
                                'cluster', 'cluster_type', 'cluster_group', 'circuit', 'circuit_type',
                                'circuit_provider', 'provider', 'virtual_chassis', 'config_template',
                                'fhrp_group', 'l2vpn', 'virtual_circuit', 'vrf', 'group']
    
    if field in relationship_name_fields:
        # Relationship fields should export names, not IDs
        if isinstance(value, dict):
            if 'name' in value:
                return str(value['name'])
            elif 'id' in value:
                # If we only have ID, try to look it up - but this shouldn't happen
                return str(value['id'])
        elif hasattr(value, 'name'):
            return value.name
        elif hasattr(value, 'id'):
            # Fallback to ID if name not available
            return value.id
    
    # Handle pynetbox Record objects (like action_type, status which are choice fields)
    # These need to be converted to dict to access value/label
    if hasattr(value, '__class__') and 'Record' in str(type(value)):
        try:
            value_dict = dict(value)
            if isinstance(value_dict, dict):
                # Fields that should use 'value' instead of 'label' for CSV import compatibility
                # NetBox CSV import expects values (e.g., 'active', 'connected') not labels (e.g., 'Active', 'Connected')
                value_preferred_fields = ['action_type', 'status']
                
                if field in value_preferred_fields:
                    # Prefer 'value' for fields that need it for CSV import
                    if 'value' in value_dict and value_dict['value']:
                        return str(value_dict['value'])
                    elif 'label' in value_dict and value_dict['label']:
                        return str(value_dict['label'])
                else:
                    # Prefer 'label' for display fields (but most should use value for import)
                    if 'label' in value_dict and value_dict['label']:
                        return str(value_dict['label'])
                    elif 'value' in value_dict and value_dict['value']:
                        return str(value_dict['value'])
                
                if len(value_dict) > 0:
                    return str(list(value_dict.values())[0])
        except:
            pass
    
    # Handle dict values (like status which has {'value': 'connected', 'label': 'Connected'})
    if isinstance(value, dict):
        # Fields that should use 'value' instead of 'label' for CSV import compatibility
        # NetBox CSV import expects values (e.g., 'active', 'connected') not labels (e.g., 'Active', 'Connected')
        value_preferred_fields = ['action_type', 'status']
        
        if field in value_preferred_fields:
            # Prefer 'value' for fields that need it for CSV import
            if 'value' in value and value['value']:
                return str(value['value'])
            elif 'label' in value and value['label']:
                return str(value['label'])
        else:
            # Prefer 'label' for display fields (but most should use value for import)
            if 'label' in value and value['label']:
                return str(value['label'])
            elif 'value' in value and value['value']:
                return str(value['value'])
        
        if len(value) > 0:
            return str(list(value.values())[0])
        return ''
    
    # Handle nested objects (region, group, tenant, parent, etc.)
    # Special handling for action_object in event rules - need to get the name
    if field == 'action_object':
        # action_object can be a dict or a pynetbox Record object
        if isinstance(value, dict):
            # Try to get name from dict
            if 'name' in value:
                return str(value['name'])
            elif 'id' in value:
                # If we only have ID, we'll need to look it up - but for now return ID
                return str(value['id'])
        # Check if it's a Record object with name attribute (this should catch it)
        if hasattr(value, 'name'):
            return value.name
    
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
    
    # Remove 'id' field from fields list if present (we don't export IDs)
    fields = [f for f in fields if f != 'id']
    
    if not fields:
        raise ValueError(f"No fields remaining after removing 'id' from configuration file: {config_path}")
    
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
                # Skip 'id' field if it somehow got through
                if field == 'id':
                    continue
                # For action_object, get the name directly from the Record object
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


def backup_all(object_types=None):
    """
    Iterate over all YAML configuration files in conf/ directory,
    sorted by numerical prefix, and export each to CSV.
    
    Args:
        object_types: Optional list of object types to export (e.g., ['tags', 'regions']).
                     If None, exports all object types.
    """
    # Get NetBox connection details from environment variables
    netbox_url = os.getenv('NETBOX_URL') or os.getenv('NB_URL')
    netbox_api_key = os.getenv('NETBOX_API_KEY') or os.getenv('NB_API_KEY') or os.getenv('NETBOX_TOKEN')
    
    if not netbox_url:
        raise ValueError("NETBOX_URL or NB_URL environment variable is required")
    if not netbox_api_key:
        raise ValueError("NETBOX_API_KEY, NB_API_KEY, or NETBOX_TOKEN environment variable is required")
    
    # Connect to NetBox
    # Disable SSL verification if NETBOX_SSL_VERIFY is set to false
    ssl_verify = os.getenv('NETBOX_SSL_VERIFY', 'true').lower() not in ('false', '0', 'no')
    nb = pynetbox.api(netbox_url, token=netbox_api_key)
    
    # Disable SSL verification if needed
    if not ssl_verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        nb.http_session.verify = False
    
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
    
    # Filter by object types if specified
    if object_types:
        # Normalize object types (handle both 'tags' and '1-tags' formats)
        normalized_types = set()
        for ot in object_types:
            # Remove numeric prefix if present
            match = re.match(r'\d+-(.+)', ot)
            if match:
                normalized_types.add(match.group(1))
            else:
                normalized_types.add(ot)
        
        # Filter config files
        filtered_files = []
        for config_path in config_files:
            filename = config_path.stem
            match = re.match(r'\d+-(.+)', filename)
            if match:
                obj_type = match.group(1)
                if obj_type in normalized_types:
                    filtered_files.append(config_path)
        
        config_files = filtered_files
        
        if not config_files:
            print(f"No configuration files found for object types: {', '.join(object_types)}")
            return
    
    # Process each configuration file
    for config_path in config_files:
        backup_from_config(config_path, nb)


if __name__ == '__main__':
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
    
    # Get available object types from config files
    conf_dir = Path('conf')
    available_types = set()
    if conf_dir.exists():
        for config_file in conf_dir.glob('*.yml'):
            match = re.match(r'\d+-(.+)', config_file.stem)
            if match:
                available_types.add(match.group(1))
        for config_file in conf_dir.glob('*.yaml'):
            match = re.match(r'\d+-(.+)', config_file.stem)
            if match:
                available_types.add(match.group(1))
    
    # Add --type option for specifying multiple types
    parser.add_argument(
        '--type', '--types',
        nargs='+',
        dest='object_types',
        help='Object types to export (e.g., tags regions sites). Can be specified multiple times or space-separated.'
    )
    
    # Add individual flags for each object type
    for obj_type in sorted(available_types):
        # Convert to valid Python identifier (replace hyphens with underscores)
        flag_name = obj_type.replace('-', '_')
        parser.add_argument(
            f'--{flag_name}',
            action='append_const',
            const=obj_type,
            dest='object_types',
            help=f'Export {obj_type}'
        )
    
    args = parser.parse_args()
    
    # Collect all specified object types
    object_types = []
    if args.object_types:
        # args.object_types is a list that may contain lists from --type and values from individual flags
        for ot in args.object_types:
            if isinstance(ot, list):
                object_types.extend(ot)
            else:
                object_types.append(ot)
        # Remove duplicates while preserving order
        seen = set()
        object_types = [x for x in object_types if x and not (x in seen or seen.add(x))]
    
    try:
        backup_all(object_types=object_types if object_types else None)
    except KeyboardInterrupt:
        print("\n\nBackup interrupted by user.")
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import sys
        sys.exit(1)
