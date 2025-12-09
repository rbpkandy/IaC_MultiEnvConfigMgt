from pydantic import BaseModel, Field, validator
from typing import Literal, Optional

#Allowed values
ALLOWED_INSTANCE_TYPES = {"t3.small", "t3.medium", "t3.large", "m5.large"}
ALLOWED_DB_ENGINES = {"postgres", "mysql"}

#Resource schema

class DatabaseConfig(BaseModel):
    engine: Literal["postgres", "mysql"] = Field(..., description="Database engine type")
    backup_retention: int = Field(..., description="Days of backup retention")
    publicly_accessible: bool = Field(..., description="Must be False for Prod")

class ComputeConfig(BaseModel):
    instance_type: str = Field(..., description="AWS Instance type")
    replicas: int = Field(..., description="Number of instances/replicas")

    @validator('instance_type')
    def validate_instance_type(cls, v):
        if v not in ALLOWED_INSTANCE_TYPES:
            raise ValueError(f"Instance type '{v}' is not in allowed list: {ALLOWED_INSTANCE_TYPES}")
        return v

#Main schema config

class EnvironmentConfig(BaseModel):
    #Used by custom validators
    environment: str = Field(..., exclude=True)
    
    database: DatabaseConfig
    api_service: ComputeConfig
    
    #Safety rules
    @validator('database', always=True)
    def validate_prod_database_safety(cls, v, values):
        env = values.get('environment')
        
        #R1: prod databases must not be publicly accessible
        if env == 'prod' and v.publicly_accessible is True:
            raise ValueError("Prod database *must not* be publicly accessible.")
        
        #R2: prod must have sufficient backup retention
        if env == 'prod' and v.backup_retention < 30:
            raise ValueError(f"Prod backup_retention must be >= 30, found {v.backup_retention}.")

        return v
