from pydantic import BaseModel
from typing import List, Optional

class S3Entity(BaseModel):
    key: str

class S3Object(BaseModel):
    object: S3Entity

class S3Bucket(BaseModel):
    name: str

class S3Data(BaseModel):
    s3: S3Object
    bucket: S3Bucket

class MinioEventRecord(BaseModel):
    eventName: str
    s3: dict  # Using dict for flexibility as structure can vary slightly
    
    @property
    def key(self) -> str:
        return self.s3['object']['key']
        
    @property
    def bucket_name(self) -> str:
        return self.s3['bucket']['name']

class MinioEvent(BaseModel):
    Key: Optional[str] = None # Some test events just send Key
    Records: Optional[List[MinioEventRecord]] = None
