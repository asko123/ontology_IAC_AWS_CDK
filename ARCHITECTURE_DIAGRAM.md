# Graph RAG Architecture - Mermaid Diagrams

## Complete System Architecture

```mermaid
graph TB
    subgraph "User Layer"
        User[👤 User/Client]
    end

    subgraph "API Layer"
        APIGW[🌐 API Gateway<br/>REST API]
        UploadLambda[⚡ Lambda<br/>Upload Handler]
    end

    subgraph "Storage Layer"
        S3[🪣 S3 Bucket<br/>Documents & Staging]
    end

    subgraph "Event & Orchestration"
        EventBridge[📡 EventBridge<br/>Event Rules]
        StepFunctions[🔄 Step Functions<br/>State Machine]
        DLQ[📮 SQS DLQ<br/>Failed Events]
    end

    subgraph "Processing Layer - VPC"
        subgraph "Lambda Functions"
            DocParser[⚡ Lambda<br/>Document Parser]
            RDFGen[⚡ Lambda<br/>RDF Generator]
            OntologyVal[⚡ Lambda<br/>Ontology Validator<br/>🆕 NEW]
            NeptuneWriter[⚡ Lambda<br/>Neptune Writer]
            EmbedGen[⚡ Lambda<br/>Embedding Generator<br/>SageMaker]
            OSWriter[⚡ Lambda<br/>OpenSearch Writer]
        end
    end

    subgraph "ML Layer"
        SageMaker[🤖 SageMaker Endpoint<br/>Embedding Model<br/>Hugging Face]
    end

    subgraph "Data Stores - VPC"
        Neptune[🔵 Neptune Cluster<br/>Graph Database<br/>RDF/SPARQL]
        OpenSearch[🔍 OpenSearch Domain<br/>Vector Search<br/>k-NN]
    end

    subgraph "Ontology"
        OWL[📋 OWL Ontology<br/>graph-rag-ontology.ttl<br/>🆕 NEW]
    end

    subgraph "Networking"
        VPC[🏢 VPC<br/>10.0.0.0/16]
        PrivateSubnet[🔒 Private Subnets<br/>Neptune, OpenSearch, Lambda]
        PublicSubnet[🌍 Public Subnets<br/>NAT Gateway]
        SG[🛡️ Security Groups<br/>Neptune, OpenSearch, Lambda]
    end

    subgraph "Monitoring"
        CloudWatch[📊 CloudWatch<br/>Logs & Metrics]
        XRay[🔬 X-Ray<br/>Tracing]
    end

    %% User Flow
    User -->|1. Upload Document| APIGW
    APIGW -->|2. Invoke| UploadLambda
    UploadLambda -->|3. Store| S3
    
    %% Event Trigger
    S3 -.->|4. Object Created Event| EventBridge
    EventBridge -->|5. Trigger| StepFunctions
    EventBridge -.->|Failed| DLQ

    %% Processing Pipeline
    StepFunctions -->|6a. Parse| DocParser
    DocParser -->|7. Text & Chunks| RDFGen
    RDFGen -->|8. RDF Triples| OntologyVal
    OntologyVal -->|9. Validate| OWL
    
    %% Parallel Processing
    OntologyVal -->|10a. Valid RDF| NeptuneWriter
    OntologyVal -->|10b. Chunks| EmbedGen
    
    %% Neptune Path
    NeptuneWriter -->|11. Stage RDF| S3
    S3 -->|12. Bulk Load| Neptune
    
    %% Embedding Path
    EmbedGen -->|13. Generate| SageMaker
    SageMaker -->|14. Vectors| EmbedGen
    EmbedGen -->|15. Index| OSWriter
    OSWriter -->|16. Store| OpenSearch

    %% VPC Connections
    DocParser -.->|In| VPC
    RDFGen -.->|In| VPC
    OntologyVal -.->|In| VPC
    NeptuneWriter -.->|In| VPC
    EmbedGen -.->|In| VPC
    OSWriter -.->|In| VPC
    
    Neptune -.->|In| PrivateSubnet
    OpenSearch -.->|In| PrivateSubnet
    
    %% Monitoring
    StepFunctions -.->|Logs| CloudWatch
    DocParser -.->|Logs| CloudWatch
    RDFGen -.->|Logs| CloudWatch
    OntologyVal -.->|Logs| CloudWatch
    NeptuneWriter -.->|Logs| CloudWatch
    EmbedGen -.->|Logs| CloudWatch
    OSWriter -.->|Logs| CloudWatch
    StepFunctions -.->|Traces| XRay

    %% Styling
    classDef awsOrange fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsBlue fill:#3B48CC,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsGreen fill:#3F8624,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsPurple fill:#8C4FFF,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef awsRed fill:#D13212,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef newFeature fill:#00D4AA,stroke:#232F3E,stroke-width:3px,color:#000

    class APIGW,S3 awsOrange
    class Neptune,OpenSearch awsBlue
    class UploadLambda,DocParser,RDFGen,NeptuneWriter,EmbedGen,OSWriter awsGreen
    class StepFunctions,EventBridge awsPurple
    class SageMaker awsRed
    class OntologyVal,OWL newFeature
```

## Upload Pipeline Detail

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant API as 🌐 API Gateway
    participant Upload as ⚡ Upload Lambda
    participant S3 as 🪣 S3 Bucket
    participant EB as 📡 EventBridge
    participant SF as 🔄 Step Functions

    User->>API: POST /upload<br/>{fileName, fileContent, metadata}
    API->>Upload: Invoke with request
    
    Upload->>Upload: Validate file type & size
    Upload->>Upload: Generate document UUID
    Upload->>S3: PutObject<br/>s3://bucket/documents/{uuid}/{file}
    Upload->>S3: Add tags (metadata)
    Upload-->>API: {documentId, s3Key, success}
    API-->>User: Upload confirmation
    
    S3->>EB: Object Created Event
    EB->>SF: Start Execution<br/>{bucket, key, metadata}
    
    Note over SF: Processing pipeline starts
```

## Processing Pipeline (Step Functions)

```mermaid
stateDiagram-v2
    [*] --> ParseDocument
    
    state ParseDocument {
        [*] --> ExtractText
        ExtractText --> SplitChunks
        SplitChunks --> ExtractMetadata
        ExtractMetadata --> [*]
    }
    
    ParseDocument --> GenerateRDF
    
    state GenerateRDF {
        [*] --> CreateTriples
        CreateTriples --> DefineEntities
        DefineEntities --> BuildRelationships
        BuildRelationships --> SerializeRDF
        SerializeRDF --> [*]
    }
    
    GenerateRDF --> ValidateOntology
    
    state ValidateOntology {
        [*] --> QueryOntology
        QueryOntology --> CheckClasses
        CheckClasses --> CheckCardinality
        CheckCardinality --> CheckDomains
        CheckDomains --> ReportViolations
        ReportViolations --> [*]
    }
    
    ValidateOntology --> ValidationCheck
    
    state ValidationCheck <<choice>>
    ValidationCheck --> ParallelProcessing: Valid
    ValidationCheck --> Failed: Violations
    
    state ParallelProcessing {
        state fork_state <<fork>>
        [*] --> fork_state
        
        fork_state --> NeptuneBranch
        fork_state --> EmbeddingBranch
        
        state NeptuneBranch {
            [*] --> StageRDF
            StageRDF --> BulkLoad
            BulkLoad --> PollStatus
            PollStatus --> [*]
        }
        
        state EmbeddingBranch {
            [*] --> GenerateEmbeddings
            GenerateEmbeddings --> CallSageMaker
            CallSageMaker --> IndexOpenSearch
            IndexOpenSearch --> [*]
        }
        
        state join_state <<join>>
        NeptuneBranch --> join_state
        EmbeddingBranch --> join_state
        join_state --> [*]
    }
    
    ParallelProcessing --> Success
    Failed --> [*]
    Success --> [*]
    
    note right of ValidateOntology
        🆕 NEW STEP
        Validates against
        OWL ontology
    end note
```

## Data Flow with Ontology Validation

```mermaid
graph LR
    subgraph "Input"
        Doc[📄 Document<br/>PDF/DOCX/CSV]
    end

    subgraph "Processing"
        Parse[⚡ Parse<br/>Extract Text]
        RDF[⚡ Generate RDF<br/>Triples]
        Validate[⚡ Validate<br/>🆕 NEW]
        Onto[📋 OWL Ontology<br/>Classes & Rules]
    end

    subgraph "Validation Rules"
        R1[✓ Class Membership]
        R2[✓ Cardinality]
        R3[✓ Domain/Range]
        R4[✓ Required Props]
    end

    subgraph "Output Stores"
        Nep[🔵 Neptune<br/>Graph]
        OS[🔍 OpenSearch<br/>Vectors]
    end

    Doc --> Parse
    Parse --> RDF
    RDF --> Validate
    Validate --> Onto
    Onto --> R1
    Onto --> R2
    Onto --> R3
    Onto --> R4
    
    R1 --> Validate
    R2 --> Validate
    R3 --> Validate
    R4 --> Validate
    
    Validate -->|✅ Pass| Nep
    Validate -->|✅ Pass| OS
    Validate -->|❌ Fail| DLQ[📮 DLQ]

    style Validate fill:#00D4AA,stroke:#232F3E,stroke-width:3px
    style Onto fill:#00D4AA,stroke:#232F3E,stroke-width:3px
```

## VPC Architecture

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC - 10.0.0.0/16"
            subgraph "Availability Zone 1"
                PublicSubnet1[🌍 Public Subnet<br/>10.0.0.0/24]
                PrivateSubnet1[🔒 Private Subnet<br/>10.0.1.0/24]
                
                NAT1[🔀 NAT Gateway]
                
                PublicSubnet1 --> NAT1
                NAT1 --> PrivateSubnet1
            end
            
            subgraph "Availability Zone 2"
                PublicSubnet2[🌍 Public Subnet<br/>10.0.2.0/24]
                PrivateSubnet2[🔒 Private Subnet<br/>10.0.3.0/24]
                
                NAT2[🔀 NAT Gateway]
                
                PublicSubnet2 --> NAT2
                NAT2 --> PrivateSubnet2
            end
            
            subgraph "Private Resources"
                LambdaSG[🛡️ Lambda SG]
                NeptuneSG[🛡️ Neptune SG]
                OSSG[🛡️ OpenSearch SG]
                
                Lambda1[⚡ Lambda Functions]
                Neptune1[🔵 Neptune Primary]
                Neptune2[🔵 Neptune Replica]
                OS1[🔍 OpenSearch Node 1]
                OS2[🔍 OpenSearch Node 2]
                
                Lambda1 -.->|Port 8182| NeptuneSG
                Lambda1 -.->|Port 443| OSSG
                
                NeptuneSG --> Neptune1
                NeptuneSG --> Neptune2
                OSSG --> OS1
                OSSG --> OS2
            end
            
            IGW[🌐 Internet Gateway]
            
            PublicSubnet1 --> IGW
            PublicSubnet2 --> IGW
            
            PrivateSubnet1 --> Lambda1
            PrivateSubnet2 --> Lambda1
            
            PrivateSubnet1 --> Neptune1
            PrivateSubnet2 --> Neptune2
            
            PrivateSubnet1 --> OS1
            PrivateSubnet2 --> OS2
        end
        
        Internet[🌍 Internet]
        Internet --> IGW
    end

    style PrivateSubnet1 fill:#FF6B6B,stroke:#C92A2A
    style PrivateSubnet2 fill:#FF6B6B,stroke:#C92A2A
    style PublicSubnet1 fill:#51CF66,stroke:#2F9E44
    style PublicSubnet2 fill:#51CF66,stroke:#2F9E44
```

## Neptune & OpenSearch Architecture

```mermaid
graph TB
    subgraph "Lambda Functions in VPC"
        L1[⚡ Neptune Writer]
        L2[⚡ OpenSearch Writer]
        L3[⚡ Validator]
    end

    subgraph "Neptune Cluster"
        NepPrimary[🔵 Neptune Primary<br/>db.t3.medium<br/>Write Endpoint]
        NepReplica[🔵 Neptune Replica<br/>db.t3.medium<br/>Read Endpoint]
        
        NepPrimary -->|Replication| NepReplica
        
        NepData[(RDF Triples<br/>Ontology<br/>SPARQL)]
    end

    subgraph "OpenSearch Domain"
        OSNode1[🔍 Node 1<br/>t3.small.search<br/>Data Node]
        OSNode2[🔍 Node 2<br/>t3.small.search<br/>Data Node]
        
        OSNode1 <-->|Cluster Sync| OSNode2
        
        OSData[(Embeddings<br/>k-NN Index<br/>Metadata)]
    end

    subgraph "S3 Staging"
        S3Stage[🪣 S3<br/>neptune-staging/]
    end

    L1 -->|1. Write RDF| S3Stage
    S3Stage -->|2. Bulk Load| NepPrimary
    NepPrimary -->|3. Store| NepData
    
    L3 -->|Query Ontology| NepPrimary
    NepPrimary -->|OWL Rules| L3
    
    L2 -->|Index Vectors| OSNode1
    OSNode1 -->|Store| OSData
    
    style NepData fill:#3B48CC
    style OSData fill:#3B48CC
```

## Ontology Structure (OWL Classes)

```mermaid
classDiagram
    class Document {
        +hasId: string [1]
        +hasFileName: string [1]
        +hasTextLength: integer
        +createdAt: dateTime [1]
        +hasChunk() [1..*]
        +hasKeyword() [0..*]
        +hasAuthor() [0..1]
        +hasType() [0..*]
    }

    class TextChunk {
        +hasChunkId: integer [1]
        +hasText: string [1]
        +hasStartPosition: integer [1]
        +hasEndPosition: integer
        +hasLength: integer
        +partOf() [1]
        +mentions() [0..*]
        +hasEmbedding() [0..1]
    }

    class Entity {
        +hasValue: string [1]
        +hasConfidenceScore: decimal
        +relatedTo() [0..*]
        +coOccursWith() [0..*]
    }

    class Person {
        <<Entity>>
        +hasName: string
    }

    class Organization {
        <<Entity>>
    }

    class Keyword {
        +hasValue: string [1]
    }

    class Author {
        +hasName: string [1]
    }

    class Embedding {
        +hasVector: string [1]
        +hasDimensions: integer [1]
        +generatedBy: string [1]
    }

    class Policy {
        <<Document>>
    }

    class Standard {
        <<Document>>
    }

    Document "1" --> "1..*" TextChunk : hasChunk
    Document "1" --> "0..*" Keyword : hasKeyword
    Document "1" --> "0..1" Author : hasAuthor
    TextChunk "1" --> "0..*" Entity : mentions
    TextChunk "1" --> "0..1" Embedding : hasEmbedding
    Entity <--> Entity : coOccursWith
    Entity <--> Entity : relatedTo
    Person --|> Entity
    Organization --|> Entity
    Policy --|> Document
    Standard --|> Document

    note for Document "🆕 NEW: OWL Ontology\nCardinality: [min..max]\n[1] = exactly one\n[1..*] = one or more\n[0..*] = zero or more"
```

## SageMaker Embedding Flow

```mermaid
graph LR
    subgraph "Text Processing"
        Chunks[📝 Text Chunks<br/>From Document]
    end

    subgraph "Lambda Function"
        EmbedLambda[⚡ Embedding Generator<br/>Lambda]
        
        Batch[Batch Chunks]
        Invoke[Invoke Endpoint]
        Collect[Collect Vectors]
    end

    subgraph "SageMaker"
        Endpoint[🤖 SageMaker Endpoint<br/>ml.m5.large]
        Model[🤗 Hugging Face Model<br/>all-mpnet-base-v2<br/>768 dimensions]
        
        Endpoint --> Model
    end

    subgraph "Vector Storage"
        Vectors[📊 Embeddings<br/>768-dim vectors]
    end

    Chunks --> EmbedLambda
    EmbedLambda --> Batch
    Batch --> Invoke
    Invoke -->|HTTP POST| Endpoint
    Model -->|JSON Response| Invoke
    Invoke --> Collect
    Collect --> Vectors

    style Model fill:#FF9900
    style Endpoint fill:#D13212
```

## Cost Breakdown

```mermaid
pie title Monthly Cost Distribution (~$259/month)
    "Neptune (db.t3.medium)" : 70
    "OpenSearch (2x t3.small)" : 60
    "SageMaker (ml.m5.large)" : 84
    "NAT Gateway" : 35
    "Lambda & Other" : 10
```

## Query Pipeline (Future)

```mermaid
graph TB
    subgraph "User Query"
        UserQ[👤 User Query<br/>"What are security policies?"]
    end

    subgraph "Query Processing"
        API2[🌐 API Gateway<br/>POST /query]
        QueryLambda[⚡ Query Lambda]
        EmbedQ[Generate Query<br/>Embedding]
    end

    subgraph "Retrieval"
        OSQuery[🔍 OpenSearch<br/>k-NN Search]
        NepQuery[🔵 Neptune<br/>Graph Traversal]
    end

    subgraph "ML Generation"
        SageMakerLLM[🤖 SageMaker<br/>LLM Endpoint]
        Context[📝 Enriched Context]
    end

    subgraph "Response"
        Answer[💬 Generated Answer<br/>with Citations]
    end

    UserQ --> API2
    API2 --> QueryLambda
    QueryLambda --> EmbedQ
    EmbedQ -->|Vector| OSQuery
    OSQuery -->|Top-k Chunks| Context
    QueryLambda -->|Document IDs| NepQuery
    NepQuery -->|Related Entities<br/>& Relationships| Context
    Context --> SageMakerLLM
    SageMakerLLM --> Answer
    Answer --> UserQ

    style QueryLambda fill:#00D4AA,stroke:#232F3E,stroke-width:2px
    style Context fill:#FFD93D,stroke:#232F3E,stroke-width:2px
```

## Legend

```mermaid
graph LR
    subgraph "AWS Services"
        API[🌐 API Gateway]
        Lambda[⚡ Lambda]
        S3[🪣 S3]
        EB[📡 EventBridge]
        SF[🔄 Step Functions]
        Nep[🔵 Neptune]
        OS[🔍 OpenSearch]
        SM[🤖 SageMaker]
        SQS[📮 SQS]
        CW[📊 CloudWatch]
    end

    subgraph "Features"
        New[🆕 NEW FEATURE<br/>Ontology Validation]
        Existing[Existing Feature]
    end

    subgraph "Data Flow"
        A -->|Synchronous| B
        C -.->|Asynchronous| D
    end

    style New fill:#00D4AA,stroke:#232F3E,stroke-width:3px
    style Existing fill:#FF9900,stroke:#232F3E,stroke-width:2px
```

## Deployment Stages

```mermaid
timeline
    title Deployment & Setup Timeline
    
    section Prerequisites
        Install Node.js : AWS CLI
                       : CDK CLI
    
    section SageMaker Setup
        Deploy Endpoint : Create Model
                       : Configure Instance
                       : Test Endpoint
                       : ~10 minutes
    
    section CDK Deployment
        Bootstrap : cdk bootstrap
        
        Deploy Networking : VPC
                         : Subnets
                         : Security Groups
                         : ~10 minutes
        
        Deploy Storage : S3 Bucket
                      : Lifecycle Policies
                      : ~2 minutes
        
        Deploy Data Stores : Neptune Cluster
                          : OpenSearch Domain
                          : ~25 minutes
        
        Deploy Processing : Lambda Functions
                         : Ontology Validator
                         : ~5 minutes
        
        Deploy Orchestration : Step Functions
                            : EventBridge Rules
                            : ~3 minutes
        
        Deploy API : API Gateway
                  : Upload Handler
                  : ~2 minutes
    
    section Post-Deployment
        Load Ontology : Upload to S3
                     : Bulk Load to Neptune
        
        Test Pipeline : Upload Document
                     : Monitor Execution
                     : Verify Results
        
        Total Time : ~50-60 minutes
```

---

## How to Use These Diagrams

### In GitHub/GitLab
These Mermaid diagrams will render automatically in:
- README.md
- Wiki pages
- Issues/PRs

### In Documentation Sites
- **Docusaurus**: Supports Mermaid via plugin
- **MkDocs**: Use `mkdocs-mermaid2-plugin`
- **Sphinx**: Use `sphinxcontrib-mermaid`

### Export as Images
Use [Mermaid Live Editor](https://mermaid.live/):
1. Copy diagram code
2. Paste in editor
3. Export as PNG/SVG

### In VS Code
Install extension: `Markdown Preview Mermaid Support`

---

## Diagram Index

1. **Complete System Architecture** - Full end-to-end flow
2. **Upload Pipeline Detail** - Sequence diagram of upload
3. **Processing Pipeline** - State machine visualization
4. **Data Flow with Ontology** - Validation flow (🆕 NEW)
5. **VPC Architecture** - Network layout
6. **Neptune & OpenSearch** - Data store architecture
7. **Ontology Structure** - OWL class diagram (🆕 NEW)
8. **SageMaker Embedding** - ML pipeline
9. **Cost Breakdown** - Monthly costs
10. **Query Pipeline** - Future RAG retrieval
11. **Deployment Timeline** - Setup stages

