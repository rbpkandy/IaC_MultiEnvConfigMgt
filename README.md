# Multi-Environment Configuration Manager

**Objective:** To manage infrastructure and application configuration across `dev`, `staging`, and `prod` environments using a layered approach, ensuring safety through declarative validation.

## Project Structure
```
├── configs/ 
    |── base-config.yaml # All shared defaults 
    |── dev.yaml # Environment overrides 
    ├── staging.yaml # Environment overrides 
    |── prod.yaml # Environment overrides 
├── tf_dir/ # Output directory for .tfvars files 
├── schema.py # Pydantic models for structure and validation logic 
├── manager.py # Main Python CLI script
|── README.md
```

## How to Run

This tool requires Python 3.8+ and the `pydantic` and `pyyaml` libraries.

### Installation

Install dependencies  
- *pip install pydantic pyyaml*    

Create the configuration directory structure  
- *mkdir -p configs tf_dir*

### Command Examples

#### 1. Validate Configuration

Checks configuration against the schema and governance rules (e.g., prod safety checks).

Validate all environments  
- *python cmanager.py validate all*
   
Validate a specific environment (e.g., prod)  
- *python manager.py validate prod*

#### 2. Generate Output Files

Generates a flat `.tfvars` file for use with Terraform, but only after successful validation.  

Generate configuration file for the dev environment  
- *python manager.py generate dev*    

This creates 'tf_dir/dev.tfvars'

#### 3. Diff Between Environments

Shows line-by-line differences in the final merged configuration between two environments.  

Show what differs between the development and production config  
- *python config_manager.py diff dev prod*

