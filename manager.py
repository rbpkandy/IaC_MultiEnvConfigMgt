import argparse
import yaml
import json
from pathlib import Path
from pydantic import ValidationError
from schema import EnvironmentConfig 
from typing import Dict, Any

CONFIG_DIR = Path("./configs")
OUTPUT_DIR = Path("./tf_dir")
OUTPUT_DIR.mkdir(exist_ok=True)
ENVIRONMENTS = ['dev', 'staging', 'prod']

def recursive_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge override dictionary into base dictionary."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = recursive_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

def get_config_for_env(env: str) -> Dict[str, Any]:
    """Load and merge base and environment-specific config."""
    base_file = CONFIG_DIR / "base-config.yaml"
    env_file = CONFIG_DIR / f"{env}.yaml"

    if not base_file.exists():
        raise FileNotFoundError(f"Base configuration file not found at {base_file}")

    with open(base_file, 'r') as f:
        base_config = yaml.safe_load(f)
    
    env_config = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_config = yaml.safe_load(f) or {}

    #Merge to base
    final_config = recursive_merge(base_config, env_config)   
    
    #Add environment name for use in custom validators.
    final_config['environment'] = env 
    
    return final_config

def validate_config(env: str, config: Dict[str, Any]) -> bool:
    """Validates the merged configuration using Pydantic."""
    print(f"Validating configuration for **{env.upper()}**...")
    try:
        EnvironmentConfig(**config)
        print(f"Validation successful for **{env.upper()}**.")
        return True
    except ValidationError as e:
        print(f"Validation failed for **{env.upper()}**:")
        #Error output
        for error in e.errors():
            field = " -> ".join(map(str, error['loc']))
            print(f"   - **{field}**: {error['msg']}")
        return False

def generate_tfvars(env: str, config: Dict[str, Any]):
    """Generates a Terraform .tfvars file from the validated config."""
    output_file = OUTPUT_DIR / f"{env}.tfvars"
    
    #Pydantic structure, use its dict conversion, excluding the 'environment' field
    validated_data = EnvironmentConfig(**config).dict(exclude={'environment'})
    
    tfvars_content = []
    
    #Conversion logic: terraform expects variables like resource_field = value
    for resource_name, resource_data in validated_data.items():
        if isinstance(resource_data, dict):
            for field, value in resource_data.items():
                # Handle boolean/string/int formatting for HCL
                if isinstance(value, str):
                    value_str = f'"{value}"'
                elif isinstance(value, bool):
                    value_str = str(value).lower() # true/false
                else:
                    value_str = str(value)
                
                tfvars_content.append(f'{resource_name}_{field} = {value_str}')
        else:
            #Handle top level fields
            tfvars_content.append(f'{resource_name} = {resource_data}')

    with open(output_file, 'w') as f:
        f.write("\n".join(tfvars_content))
    
    print(f"Generated **{output_file}** successfully.")


def run_diff(env1: str, env2: str):
    """Compare the final configuration of two environments."""
    if env1 not in ENVIRONMENTS or env2 not in ENVIRONMENTS:
        print("Invalid environment(s) specified for diff.")
        return
        
    config1 = get_config_for_env(env1)
    config2 = get_config_for_env(env2)
    
    print(f"**DIFF MODE**: Comparing **{env1.upper()}** vs **{env2.upper()}**")
    
    #Use a flat list for diffing for the simplified scope
    
    #Helper to flatten dict for comparison
    def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        items = {}
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, dict):
                items.update(flatten_dict(v, new_key, sep=sep))
            else:
                items[new_key] = v
        return items

    flat1 = flatten_dict(config1)
    flat2 = flatten_dict(config2)
    
    all_keys = sorted(set(list(flat1.keys()) + list(flat2.keys())))
    
    diff_found = False
    for key in all_keys:
        if key == 'environment': #Skip internal tracking field
            continue
            
        val1 = flat1.get(key, '<<<MISSING>>>')
        val2 = flat2.get(key, '<<<MISSING>>>')
        
        if val1 != val2:
            print(f"   - **{key}**: **{env1.upper()}**=`{val1}` | **{env2.upper()}**=`{val2}`")
            diff_found = True
            
    if not diff_found:
        print("   - Configurations are **identical**.")

#CLI 
def main():
    parser = argparse.ArgumentParser(description="Multi-Environment Configuration Management Tool.")
    subparsers = parser.add_subparsers(dest='command', required=True)

    #Validate
    parser_validate = subparsers.add_parser('validate', help='Validate configuration for one or all environments.')
    parser_validate.add_argument('env', nargs='?', choices=ENVIRONMENTS + ['all'], default='all', help='Environment to validate (dev, staging, prod, or all).')

    #Generate
    parser_generate = subparsers.add_parser('generate', help='Generate .tfvars output for a specific environment.')
    parser_generate.add_argument('env', choices=ENVIRONMENTS, help='Environment to generate config for (dev, staging, prod).')
    
    #Diff
    parser_diff = subparsers.add_parser('diff', help='Show differences between two environments.')
    parser_diff.add_argument('env1', choices=ENVIRONMENTS, help='First environment for comparison.')
    parser_diff.add_argument('env2', choices=ENVIRONMENTS, help='Second environment for comparison.')

    args = parser.parse_args()

    if args.command == 'validate':
        envs_to_validate = ENVIRONMENTS if args.env == 'all' else [args.env]
        
        all_valid = True
        for env in envs_to_validate:
            config = get_config_for_env(env)
            if not validate_config(env, config):
                all_valid = False
        
        if all_valid:
            print("\nAll selected configurations passed validation.")
        else:
            print("\nOne or more configurations failed validation. Check logs above.")
            
    elif args.command == 'generate':
        env = args.env
        config = get_config_for_env(env)
        if validate_config(env, config):
            generate_tfvars(env, config)

    elif args.command == 'diff':
        run_diff(args.env1, args.env2)

if __name__ == "__main__":
    #Create the schema.py file first to run the main script
    main()
