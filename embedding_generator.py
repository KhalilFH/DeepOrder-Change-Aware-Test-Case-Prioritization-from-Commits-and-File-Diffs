import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional, Union
import re
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
import warnings
warnings.filterwarnings('ignore')

# Import required models
try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
    print("Using transformers library for advanced models")
except ImportError:
    print("Error: transformers library not available!")
    print("Please install with: pip install transformers torch")
    TRANSFORMERS_AVAILABLE = False
    exit(1)

class SoftwareEngineeringEmbeddingPipeline:
    """
    Comprehensive embedding pipeline specifically designed for Test Case Prioritization
    using software engineering domain knowledge with automatic Ruby/Java project detection.
    """
    
    def __init__(self, 
                 embedding_model_type: str = 'codebert',
                 embedding_dim: int = 128,
                 normalize_features: bool = True,
                 random_seed: int = 42,
                 project_type: str = 'auto'):
        """
        Initialize the SE embedding pipeline
        
        Args:
            embedding_model_type: 'codebert', 'unixcoder', 'codet5', or 'sentence_transformer'
            embedding_dim: Final embedding dimension after reduction
            normalize_features: Whether to normalize final embeddings
            random_seed: Random seed for reproducibility
            project_type: 'auto', 'java', or 'ruby' - auto-detects if 'auto'
        """
        self.embedding_model_type = embedding_model_type
        self.embedding_dim = embedding_dim
        self.normalize_features = normalize_features
        self.random_seed = random_seed
        self.project_type = project_type
        self.detected_project_type = None
        
        # Model components
        self.model = None
        self.tokenizer = None
        self.commit_scaler = None
        self.file_scaler = None
        self.combined_scaler = None
        self.commit_reducer = None
        self.file_reducer = None
        self.combined_reducer = None
        
        # Risk pattern matchers (will be set after project detection)
        self.risk_patterns = None
        self.file_type_patterns = None
        
        # Initialize the embedding model
        self._initialize_embedding_model()
    
    def detect_project_type(self, df: pd.DataFrame) -> str:
        """
        Automatically detect if this is a Ruby or Java project based on file patterns
        """
        if self.project_type != 'auto':
            return self.project_type
        
        print("Auto-detecting project type...")
        
        # Find file column
        file_col = None
        for col in ['changed_files', 'FilesChanged', 'files', 'file_paths', 'LastFiles']:
            if col in df.columns:
                file_col = col
                break
        
        if file_col is None:
            print("No file column found, defaulting to Java patterns")
            return 'java'
        
        # Analyze file patterns in sample
        sample_size = min(1000, len(df))  # Check up to 1000 rows
        sample_df = df.sample(n=sample_size, random_state=self.random_seed) if len(df) > sample_size else df
        
        ruby_indicators = 0
        java_indicators = 0
        
        for _, row in sample_df.iterrows():
            files = row[file_col]
            
            # Parse file list
            if isinstance(files, str):
                if files.startswith('[') and files.endswith(']'):
                    try:
                        import ast
                        file_paths = ast.literal_eval(files)
                    except:
                        file_paths = [f.strip().strip("'\"") for f in files.strip("[]").split(",") if f.strip()]
                else:
                    file_paths = [files]
            elif isinstance(files, list):
                file_paths = files
            else:
                file_paths = []
            
            for file_path in file_paths:
                file_path_str = str(file_path).lower()
                
                # Ruby indicators
                if any(indicator in file_path_str for indicator in [
                    '.rb', 'gemfile', 'rakefile', '/app/', '/config/', '/lib/', 
                    '.erb', '.haml', '.slim', '/spec/', '_spec.rb', '_test.rb',
                    'config.ru', '/db/migrate/', '.feature'
                ]):
                    ruby_indicators += 1
                
                # Java indicators  
                if any(indicator in file_path_str for indicator in [
                    '.java', '.class', 'pom.xml', 'build.gradle', '/src/main/java/',
                    '/src/test/java/', '.jsp', '.war', '.jar', 'web.xml',
                    'application.properties', 'logback.xml'
                ]):
                    java_indicators += 1
        
        # Determine project type
        if ruby_indicators > java_indicators:
            detected_type = 'ruby'
            print(f"✅ Detected Ruby project (Ruby: {ruby_indicators}, Java: {java_indicators})")
        elif java_indicators > ruby_indicators:
            detected_type = 'java'
            print(f"✅ Detected Java project (Java: {java_indicators}, Ruby: {ruby_indicators})")
        else:
            detected_type = 'java'  # Default to Java if unclear
            print(f"⚠️  Unclear project type, defaulting to Java (Java: {java_indicators}, Ruby: {ruby_indicators})")
        
        self.detected_project_type = detected_type
        return detected_type
    
    def _initialize_risk_patterns(self, project_type: str) -> Dict:
        """Initialize risk patterns based on project type"""
        
        # Base patterns that apply to both languages
        base_patterns = {
            'critical_risk': {
                'patterns': [
                    r'\b(critical|urgent|emergency|hotfix|blocker)\b',
                    r'\b(security|vulnerability|exploit|breach)\b',
                    r'\b(crash|failure|fatal|corruption)\b',
                    r'\b(memory leak|deadlock|race condition)\b'
                ],
                'weight': 5.0
            },
            'high_risk': {
                'patterns': [
                    r'\b(fix|bug|defect|issue|error|exception)\b',
                    r'\b(null pointer|npe|stackoverflow|timeout)\b',
                    r'\b(database|transaction|concurrency)\b',
                    r'\b(authentication|authorization|permission)\b'
                ],
                'weight': 3.0
            },
            'medium_risk': {
                'patterns': [
                    r'\b(refactor|restructure|cleanup|optimize)\b',
                    r'\b(update|upgrade|migration|deprecat)\b',
                    r'\b(configuration|config|properties)\b',
                    r'\b(integration|api|interface)\b'
                ],
                'weight': 2.0
            },
            'low_risk': {
                'patterns': [
                    r'\b(test|spec|junit|mock|stub)\b',
                    r'\b(documentation|doc|comment|readme)\b',
                    r'\b(format|style|lint|prettier)\b',
                    r'\b(log|logging|trace|debug)\b'
                ],
                'weight': 1.0
            }
        }
        
        if project_type == 'ruby':
            # Add Ruby-specific patterns
            base_patterns['ruby_critical_risk'] = {
                'patterns': [
                    r'\b(rails|activerecord|activesupport) (upgrade|migration)\b',
                    r'\b(gem|dependency) (update|upgrade|bump)\b',
                    r'\b(database|migration|rollback)\b',
                    r'\b(bundler|gemfile)\b'
                ],
                'weight': 5.0
            }
            base_patterns['ruby_high_risk'] = {
                'patterns': [
                    r'\b(controller|model|service) (refactor|change)\b',
                    r'\b(route|routing) (change|update)\b',
                    r'\b(devise|omniauth|cancan)\b',
                    r'\b(sidekiq|resque|delayed_job|background)\b'
                ],
                'weight': 3.0
            }
            base_patterns['scope_indicators'] = {
                'patterns': [
                    r'\b(rails|activerecord|actionpack|actionview)\b',
                    r'\b(sinatra|grape|hanami)\b',
                    r'\b(rspec|minitest|capybara|cucumber)\b',
                    r'\b(controller|model|service|helper|concern)\b'
                ],
                'weight': 1.5
            }
        else:  # Java
            base_patterns['scope_indicators'] = {
                'patterns': [
                    r'\b(core|engine|kernel|framework)\b',
                    r'\b(service|manager|controller|handler)\b',
                    r'\b(util|helper|common|shared)\b',
                    r'\b(ui|frontend|view|component)\b',
                    r'\b(data|model|entity|schema)\b',
                ],
                'weight': 1.5
            }
        
        return base_patterns
    
    def _initialize_file_type_patterns(self, project_type: str) -> Dict:
        """Initialize file type patterns based on project type"""
        
        if project_type == 'ruby':
            return {
                'core_system': {
                    'patterns': [
                        r'\b(engine|core|kernel|base|application)\b',
                        r'/(app|lib)/.*\.rb$',
                        r'/(config/application|config/environment)\.rb$',
                        r'/app/(controllers|models|services)/.*\.rb$'
                    ],
                    'risk_multiplier': 3.0
                },
                'business_logic': {
                    'patterns': [
                        r'/app/(controllers|models|services|jobs|workers)/.*\.rb$',
                        r'/lib/.*\.rb$',
                        r'/(business|logic|process|workflow)/.*\.rb$'
                    ],
                    'risk_multiplier': 2.5
                },
                'data_layer': {
                    'patterns': [
                        r'/app/models/.*\.rb$',
                        r'/db/(migrate|seeds)/.*\.rb$',
                        r'\.sql$',
                        r'/config/database\.yml$'
                    ],
                    'risk_multiplier': 2.0
                },
                'view_layer': {
                    'patterns': [
                        r'/app/views/.*\.(erb|haml|slim)$',
                        r'/app/assets/.*\.(scss|css|js|coffee)$',
                        r'/app/helpers/.*\.rb$'
                    ],
                    'risk_multiplier': 1.5
                },
                'configuration': {
                    'patterns': [
                        r'/(config|initializers)/.*\.(rb|yml|yaml)$',
                        r'Gemfile$',
                        r'\.env$',
                        r'/config/(routes|application|environment)\.rb$'
                    ],
                    'risk_multiplier': 2.0
                },
                'test_files': {
                    'patterns': [
                        r'/(test|spec)/.*\.rb$',
                        r'_test\.rb$',
                        r'_spec\.rb$',
                        r'/features/.*\.feature$'
                    ],
                    'risk_multiplier': 0.5
                },
                'build_files': {
                    'patterns': [
                        r'Gemfile$',
                        r'Rakefile$',
                        r'Dockerfile$',
                        r'\.github/workflows/.*\.ya?ml$'
                    ],
                    'risk_multiplier': 1.5
                },
                'documentation': {
                    'patterns': [
                        r'\.(md|txt|rst|rdoc)$',
                        r'/docs?/',
                        r'README'
                    ],
                    'risk_multiplier': 0.2
                }
            }
        else:  # Java patterns
            return {
                'core_system': {
                    'patterns': [
                        r'\b(engine|core|kernel|framework|base)\b',
                        r'\.(service|manager|controller|handler)\.',
                        r'/src/main/java/.*(Service|Manager|Controller|Engine)\.java$'
                    ],
                    'risk_multiplier': 3.0
                },
                'business_logic': {
                    'patterns': [
                        r'/src/main/java/.*\.java$',
                        r'\.(business|logic|process|workflow)\.',
                        r'/(service|business|logic)/'
                    ],
                    'risk_multiplier': 2.5
                },
                'data_layer': {
                    'patterns': [
                        r'\.(dao|repository|entity|model)\.',
                        r'/(dao|repository|entity|model)/',
                        r'\.(sql|hql|ddl)$'
                    ],
                    'risk_multiplier': 2.0
                },
                'configuration': {
                    'patterns': [
                        r'\.(properties|config|xml|yml|yaml|json)$',
                        r'/(config|configuration)/',
                        r'/(resources)/'
                    ],
                    'risk_multiplier': 2.0
                },
                'test_files': {
                    'patterns': [
                        r'/src/test/',
                        r'\.(test|spec)\.',
                        r'Test\.java$',
                        r'Spec\.java$'
                    ],
                    'risk_multiplier': 0.5
                },
                'build_files': {
                    'patterns': [
                        r'(pom\.xml|build\.gradle|package\.json)$',
                        r'Makefile$',
                        r'Dockerfile$'
                    ],
                    'risk_multiplier': 1.5
                },
                'documentation': {
                    'patterns': [
                        r'\.(md|txt|rst|doc)$',
                        r'/docs?/',
                        r'README'
                    ],
                    'risk_multiplier': 0.2
                }
            }
    
    def create_file_description(self, path_str: str, project_type: str) -> str:
        """Create meaningful descriptions based on project type"""
        
        parts = path_str.replace('\\', '/').split('/')
        filename = parts[-1]
        
        if project_type == 'ruby':
            # Ruby-specific file type detection
            if '/test/' in path_str or '/spec/' in path_str or filename.endswith(('_test.rb', '_spec.rb')):
                return f"test file {filename}"
            elif '/app/controllers/' in path_str:
                return f"controller {filename}"
            elif '/app/models/' in path_str:
                return f"model {filename}"
            elif '/app/services/' in path_str:
                return f"service {filename}"
            elif '/app/views/' in path_str:
                return f"view template {filename}"
            elif '/db/migrate/' in path_str:
                return f"database migration {filename}"
            elif filename == 'Gemfile' or filename == 'Gemfile.lock':
                return f"gem dependency {filename}"
            elif filename == 'Rakefile':
                return "rake tasks"
            elif '/config/' in path_str:
                return f"configuration {filename}"
            elif filename.endswith('.rb'):
                return f"ruby source {filename}"
            elif filename.endswith(('.yml', '.yaml')):
                return f"yaml config {filename}"
            elif filename.endswith(('.erb', '.haml', '.slim')):
                return f"template {filename}"
            else:
                return f"file {filename}"
        else:  # Java
            if any(test_word in filename.lower() for test_word in ['test', 'spec']):
                return f"test file {filename}"
            elif filename.endswith('.java'):
                return f"java source {filename}"
            elif filename.endswith(('.xml', '.properties', '.yml', '.yaml')):
                return f"configuration {filename}"
            else:
                return f"file {filename}"
    
    def _initialize_embedding_model(self):
        """Initialize the appropriate embedding model"""
        
        if not TRANSFORMERS_AVAILABLE:
            print("Error: transformers library is required!")
            exit(1)
        
        model_configs = {
            'codebert': {
                'model_name': 'microsoft/codebert-base',
                'description': 'Pre-trained on code and natural language'
            },
            'unixcoder': {
                'model_name': 'microsoft/unixcoder-base',
                'description': 'Unified pre-trained model for code understanding'
            },
            'codet5': {
                'model_name': 'Salesforce/codet5-base',
                'description': 'Code-aware encoder-decoder model'
            },
            'graphcodebert': {
                'model_name': 'microsoft/graphcodebert-base',
                'description': 'Graph-based code representation'
            }
        }
        
        if self.embedding_model_type not in model_configs:
            print(f"Unknown model type {self.embedding_model_type}, using codebert")
            self.embedding_model_type = 'codebert'
        
        config = model_configs[self.embedding_model_type]
        print(f"Loading {self.embedding_model_type}: {config['description']}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(config['model_name'])
            self.model = AutoModel.from_pretrained(config['model_name'])
            self.model.eval()  # Set to evaluation mode
            print(f"Successfully loaded {config['model_name']}")
        except Exception as e:
            print(f"Failed to load {config['model_name']}: {e}")
            print("Please check your internet connection and try again.")
            exit(1)
    
    def extract_commit_risk_features(self, commit_messages: List[str]) -> np.ndarray:
        """Extract risk-based features from commit messages"""
        
        features = []
        
        for msg in commit_messages:
            if not isinstance(msg, str):
                msg = str(msg) if msg is not None else ""
            
            msg_lower = msg.lower()
            msg_features = {}
            
            # Risk level scoring
            total_risk_score = 0.0
            for risk_level, config in self.risk_patterns.items():
                if risk_level == 'scope_indicators':
                    continue
                    
                level_score = 0.0
                for pattern in config['patterns']:
                    matches = len(re.findall(pattern, msg_lower))
                    level_score += matches * config['weight']
                
                msg_features[f'{risk_level}_score'] = level_score
                total_risk_score += level_score
            
            msg_features['total_risk_score'] = total_risk_score
            
            # Scope indicators
            scope_score = 0.0
            for pattern in self.risk_patterns['scope_indicators']['patterns']:
                matches = len(re.findall(pattern, msg_lower))
                scope_score += matches * self.risk_patterns['scope_indicators']['weight']
            msg_features['scope_score'] = scope_score
            
            # Structural features
            msg_features['message_length'] = len(msg)
            msg_features['word_count'] = len(msg.split())
            msg_features['has_numbers'] = 1.0 if re.search(r'\d', msg) else 0.0
            msg_features['has_special_chars'] = 1.0 if re.search(r'[#@$%&*]', msg) else 0.0
            msg_features['has_file_extensions'] = 1.0 if re.search(r'\.\w{2,4}\b', msg) else 0.0
            
            # Conventional commit detection
            conventional_patterns = {
                'feat': r'^feat(\(.+\))?:',
                'fix': r'^fix(\(.+\))?:',
                'docs': r'^docs(\(.+\))?:',
                'style': r'^style(\(.+\))?:',
                'refactor': r'^refactor(\(.+\))?:',
                'test': r'^test(\(.+\))?:',
                'chore': r'^chore(\(.+\))?:'
            }
            
            for conv_type, pattern in conventional_patterns.items():
                msg_features[f'is_{conv_type}'] = 1.0 if re.search(pattern, msg_lower) else 0.0
            
            features.append(list(msg_features.values()))
        
        return np.array(features, dtype=np.float32)
    
    def extract_file_structural_features(self, file_lists: List[Union[str, List[str]]]) -> np.ndarray:
        """Extract structural features from file paths"""
        
        features = []
        
        for files in file_lists:
            # Parse file list
            if isinstance(files, str):
                if files.startswith('[') and files.endswith(']'):
                    try:
                        import ast
                        file_paths = ast.literal_eval(files)
                    except:
                        file_paths = [f.strip().strip("'\"") for f in files.strip("[]").split(",") if f.strip()]
                else:
                    file_paths = [files]
            elif isinstance(files, list):
                file_paths = files
            else:
                file_paths = []
            
            if not file_paths:
                # Fixed number of features for empty file lists
                features.append([0.0] * (4 + len(self.file_type_patterns) * 2 + 4))
                continue
            
            file_features = {}
            
            # Basic statistics
            file_features['num_files'] = len(file_paths)
            file_features['avg_path_length'] = np.mean([len(str(p)) for p in file_paths])
            file_features['max_path_depth'] = max([len(str(p).split('/')) for p in file_paths], default=0)
            file_features['unique_directories'] = len(set(['/'.join(str(p).split('/')[:-1]) for p in file_paths if '/' in str(p)]))
            
            # File type analysis
            type_counts = {file_type: 0 for file_type in self.file_type_patterns.keys()}
            total_risk_score = 0.0
            
            for file_path in file_paths:
                file_path_str = str(file_path).lower()
                
                # Classify file type
                for file_type, config in self.file_type_patterns.items():
                    for pattern in config['patterns']:
                        if re.search(pattern, file_path_str):
                            type_counts[file_type] += 1
                            total_risk_score += config['risk_multiplier']
                            break
            
            # Convert counts to ratios and features (ensure consistent order)
            total_files = len(file_paths)
            
            # Add features in a fixed order to ensure consistency
            feature_values = [
                file_features['num_files'],
                file_features['avg_path_length'], 
                file_features['max_path_depth'],
                file_features['unique_directories']
            ]
            
            # File type ratios and counts in consistent order
            for file_type in sorted(self.file_type_patterns.keys()):
                count = type_counts.get(file_type, 0)
                feature_values.append(count / total_files)  # ratio
                feature_values.append(float(count))  # count
            
            # Risk scores
            feature_values.append(total_risk_score / total_files)  # avg_file_risk
            feature_values.append(total_risk_score)  # total_file_risk
            
            # Extension diversity
            extensions = set()
            for file_path in file_paths:
                if '.' in str(file_path):
                    ext = str(file_path).split('.')[-1].lower()
                    extensions.add(ext)
            
            feature_values.append(float(len(extensions)))  # extension_diversity
            feature_values.append(1.0 if len(extensions) > 1 else 0.0)  # is_multi_language
            
            features.append(feature_values)
        
        return np.array(features, dtype=np.float32)
    
    def encode_text_with_model(self, texts: List[str], max_length: int = 512) -> np.ndarray:
        """Encode texts using the selected model"""
        
        # Use transformers library
        embeddings = []
        batch_size = 16  # Smaller batch size to avoid memory issues
        
        print(f"Processing {len(texts)} texts in batches of {batch_size}...")
        
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                if i % (batch_size * 10) == 0:  # Progress update every 10 batches
                    print(f"  Processed {i}/{len(texts)} texts...")
                
                # Tokenize
                inputs = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=max_length,
                    return_tensors='pt'
                )
                
                # Get embeddings
                outputs = self.model(**inputs)
                
                # Use [CLS] token embedding or mean pooling
                if hasattr(outputs, 'last_hidden_state'):
                    # Mean pooling over sequence length
                    attention_mask = inputs['attention_mask']
                    token_embeddings = outputs.last_hidden_state
                    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                    batch_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                else:
                    # Use pooler output if available
                    batch_embeddings = outputs.pooler_output
                
                embeddings.append(batch_embeddings.numpy())
        
        print(f"  Completed processing {len(texts)} texts.")
        return np.vstack(embeddings)
    
    def create_commit_embeddings(self, df: pd.DataFrame) -> np.ndarray:
        """Create comprehensive commit message embeddings"""
        
        print("Creating commit message embeddings...")
        
        # Find commit message column
        commit_col = None
        for col in ['commit_message', 'CommitMsg', 'commit_msg', 'message','CommitMessage']:
            if col in df.columns:
                commit_col = col
                break
        
        if commit_col is None:
            print("No commit message column found, returning zeros")
            return np.zeros((len(df), self.embedding_dim))
        
        commit_messages = df[commit_col].fillna('').astype(str).tolist()
        
        # 1. Semantic embeddings from model
        print("Generating semantic embeddings...")
        semantic_embeddings = self.encode_text_with_model(commit_messages)
        
        # 2. Risk-based features
        print("Extracting risk features...")
        risk_features = self.extract_commit_risk_features(commit_messages)
        
        # 3. Combine embeddings
        combined_features = np.hstack([semantic_embeddings, risk_features])
        
        # 4. Reduce dimensionality if needed
        if combined_features.shape[1] > self.embedding_dim:
            if self.commit_reducer is None:
                self.commit_reducer = PCA(n_components=self.embedding_dim, random_state=self.random_seed)
            combined_features = self.commit_reducer.fit_transform(combined_features)
        
        # 5. Scale features
        if self.commit_scaler is None:
            self.commit_scaler = StandardScaler() if self.normalize_features else MinMaxScaler()
        
        final_embeddings = self.commit_scaler.fit_transform(combined_features)
        
        print(f"Commit embeddings shape: {final_embeddings.shape}")
        return final_embeddings
    
    def create_file_embeddings(self, df: pd.DataFrame) -> np.ndarray:
        """Create comprehensive file path embeddings"""
        
        print("Creating file path embeddings...")
        
        # Find file column
        file_col = None
        for col in ['changed_files', 'FilesChanged', 'files', 'file_paths','LastFiles']:
            if col in df.columns:
                file_col = col
                break
        
        if file_col is None:
            print("No file column found, returning zeros")
            return np.zeros((len(df), self.embedding_dim))
        
        file_lists = df[file_col].tolist()
        
        # 1. Structural features
        print("Extracting file structural features...")
        structural_features = self.extract_file_structural_features(file_lists)
        
        # 2. Create textual representations for semantic embedding
        print("Creating file text representations...")
        file_texts = []
        for files in file_lists:
            if isinstance(files, str):
                if files.startswith('['):
                    try:
                        import ast
                        file_paths = ast.literal_eval(files)
                    except:
                        file_paths = [f.strip().strip("'\"") for f in files.strip("[]").split(",") if f.strip()]
                else:
                    file_paths = [files]
            elif isinstance(files, list):
                file_paths = files
            else:
                file_paths = []
            
            # Create meaningful text representation
            if file_paths:
                # Extract key components
                directories = set()
                filenames = set()
                extensions = set()
                
                for path in file_paths:
                    path_str = str(path)
                    parts = path_str.replace('\\', '/').split('/')
                    
                    # Get directory components
                    if len(parts) > 1:
                        directories.update(parts[:-1])
                    
                    # Get filename
                    filename = parts[-1]
                    filenames.add(filename)
                    
                    # Get extension
                    if '.' in filename:
                        ext = filename.split('.')[-1]
                        extensions.add(ext)
                
                # Create descriptive text
                text_parts = []
                if directories:
                    text_parts.append(" ".join(sorted(directories)))
                if extensions:
                    text_parts.append(" ".join([f"extension_{ext}" for ext in sorted(extensions)]))
                
                file_text = " ".join(text_parts)
            else:
                file_text = ""
            
            file_texts.append(file_text)
        
        # 3. Get semantic embeddings for file representations
        print("Generating file semantic embeddings...")
        semantic_embeddings = self.encode_text_with_model(file_texts)
        
        # 4. Combine structural and semantic features
        combined_features = np.hstack([structural_features, semantic_embeddings])
        
        # 5. Reduce dimensionality if needed
        if combined_features.shape[1] > self.embedding_dim:
            if self.file_reducer is None:
                self.file_reducer = PCA(n_components=self.embedding_dim, random_state=self.random_seed)
            combined_features = self.file_reducer.fit_transform(combined_features)
        
        # 6. Scale features
        if self.file_scaler is None:
            self.file_scaler = StandardScaler() if self.normalize_features else MinMaxScaler()
        
        final_embeddings = self.file_scaler.fit_transform(combined_features)
        
        print(f"File embeddings shape: {final_embeddings.shape}")
        return final_embeddings
    
    def create_combined_embeddings(self, df: pd.DataFrame) -> np.ndarray:
        """Create embeddings from commit message + file paths combined"""
        
        print("Creating combined (commit + file) embeddings...")
        
        # Find columns
        commit_col = None
        for col in ['commit_message', 'CommitMsg', 'commit_msg', 'message','CommitMessage']:
            if col in df.columns:
                commit_col = col
                break
        
        file_col = None
        for col in ['changed_files', 'FilesChanged', 'files', 'file_paths','LastFiles']:
            if col in df.columns:
                file_col = col
                break
        
        if commit_col is None and file_col is None:
            print("No commit or file columns found, returning zeros")
            return np.zeros((len(df), self.embedding_dim))
        
        # Create combined text representations
        combined_texts = []
        
        for idx, row in df.iterrows():
            text_parts = []
            
            # Add commit message
            if commit_col and pd.notna(row[commit_col]):
                commit_msg = str(row[commit_col]).strip()
                if commit_msg:
                    text_parts.append(commit_msg)
            
            # Add file information
            if file_col and pd.notna(row[file_col]):
                files = row[file_col]
                
                # Parse file list
                if isinstance(files, str):
                    if files.startswith('['):
                        try:
                            import ast
                            file_paths = ast.literal_eval(files)
                        except:
                            file_paths = [f.strip().strip("'\"") for f in files.strip("[]").split(",") if f.strip()]
                    else:
                        file_paths = [files]
                elif isinstance(files, list):
                    file_paths = files
                else:
                    file_paths = []
                
                if file_paths:
                    # Create file description using project-specific logic
                    file_descriptions = []
                    for path in file_paths[:10]:  # Limit to avoid too long texts
                        description = self.create_file_description(str(path), self.detected_project_type)
                        file_descriptions.append(description)
                    
                    if file_descriptions:
                        text_parts.append("modifies " + ", ".join(file_descriptions))
            
            combined_text = " ".join(text_parts) if text_parts else ""
            combined_texts.append(combined_text)
        
        # Get semantic embeddings
        print("Generating combined semantic embeddings...")
        semantic_embeddings = self.encode_text_with_model(combined_texts)
        
        # Extract risk features from combined text
        print("Extracting combined risk features...")
        risk_features = self.extract_commit_risk_features(combined_texts)
        
        # Combine features
        combined_features = np.hstack([semantic_embeddings, risk_features])
        
        # Reduce dimensionality if needed
        if combined_features.shape[1] > self.embedding_dim:
            if self.combined_reducer is None:
                self.combined_reducer = PCA(n_components=self.embedding_dim, random_state=self.random_seed)
            combined_features = self.combined_reducer.fit_transform(combined_features)
        
        # Scale features
        if self.combined_scaler is None:
            self.combined_scaler = StandardScaler() if self.normalize_features else MinMaxScaler()
        
        final_embeddings = self.combined_scaler.fit_transform(combined_features)
        
        print(f"Combined embeddings shape: {final_embeddings.shape}")
        return final_embeddings
    
    def get_embedding_options(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Generate all three embedding options for comparison with auto-detection"""
        
        print("Generating all embedding options with auto-detection...")
        print(f"Dataset shape: {df.shape}")
        
        # Auto-detect project type first
        detected_type = self.detect_project_type(df)
        
        # Initialize patterns based on detected type
        self.risk_patterns = self._initialize_risk_patterns(detected_type)
        self.file_type_patterns = self._initialize_file_type_patterns(detected_type)
        
        print(f"🎯 Using {detected_type.upper()} patterns for embedding generation")
        
        options = {}
        
        # Option 1: Commit message only
        print("\n" + "="*50)
        print("OPTION 1: COMMIT MESSAGE EMBEDDINGS")
        print("="*50)
        options['commit_only'] = self.create_commit_embeddings(df)
        
        # Option 2: File paths only
        print("\n" + "="*50)
        print("OPTION 2: FILE PATH EMBEDDINGS")
        print("="*50)
        options['files_only'] = self.create_file_embeddings(df)
        
        # Option 3: Combined commit + files
        print("\n" + "="*50)
        print("OPTION 3: COMBINED COMMIT + FILE EMBEDDINGS")
        print("="*50)
        options['combined'] = self.create_combined_embeddings(df)
        
        print("\n" + "="*50)
        print("EMBEDDING GENERATION COMPLETE")
        print("="*50)
        
        for option_name, embeddings in options.items():
            print(f"{option_name}: {embeddings.shape}")
        
        return options
    
    def save_embeddings(self, embeddings_dict: Dict[str, np.ndarray], output_dir: str = "embeddings"):
        """Save embeddings to disk with project type info"""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save project type info
        with open(f"{output_dir}/project_info.txt", "w") as f:
            f.write(f"detected_project_type: {self.detected_project_type}\n")
            f.write(f"embedding_model_type: {self.embedding_model_type}\n")
            f.write(f"embedding_dim: {self.embedding_dim}\n")
        
        for option_name, embeddings in embeddings_dict.items():
            filename = f"{output_dir}/{option_name}_embeddings.npy"
            np.save(filename, embeddings)
            print(f"Saved {option_name} embeddings to {filename}")
        
        print(f"💾 Saved project info to {output_dir}/project_info.txt")
    
    def load_embeddings(self, output_dir: str = "embeddings") -> Dict[str, np.ndarray]:
        """Load embeddings from disk"""
        import os
        
        embeddings = {}
        option_names = ['commit_only', 'files_only', 'combined']
        
        # Load project info if available
        info_file = f"{output_dir}/project_info.txt"
        if os.path.exists(info_file):
            with open(info_file, "r") as f:
                for line in f:
                    if line.startswith("detected_project_type:"):
                        self.detected_project_type = line.split(":")[1].strip()
                        print(f"📁 Loaded project type: {self.detected_project_type}")
        
        for option_name in option_names:
            filename = f"{output_dir}/{option_name}_embeddings.npy"
            if os.path.exists(filename):
                embeddings[option_name] = np.load(filename)
                print(f"✅ Loaded {option_name} embeddings from {filename}")
            else:
                print(f"❌ File not found: {filename}")
        
        return embeddings


# Example usage and testing
def test_embedding_pipeline(df: pd.DataFrame, model_type: str = 'codebert', project_type: str = 'auto'):
    """Test the adaptive embedding pipeline"""
    
    print(f"Testing Adaptive SE Embedding Pipeline")
    print(f"Model: {model_type}, Project Detection: {project_type}")
    print("="*60)
    
    # Initialize pipeline with auto-detection
    pipeline = SoftwareEngineeringEmbeddingPipeline(
        embedding_model_type=model_type,
        embedding_dim=128,
        normalize_features=True,
        random_seed=42,
        project_type=project_type  # 'auto' for detection, 'ruby'/'java' for manual
    )
    
    # Generate all embedding options (will auto-detect project type)
    embeddings = pipeline.get_embedding_options(df)
    
    # Save embeddings with project info
    pipeline.save_embeddings(embeddings, output_dir=f"adaptive_embeddings_{pipeline.detected_project_type}")
    
    # Print summary
    print(f"\n🎯 PROJECT TYPE: {pipeline.detected_project_type.upper()}")
    print("\nEMBEDDING SUMMARY:")
    print("-" * 40)
    for option_name, embedding_matrix in embeddings.items():
        print(f"{option_name.upper()}:")
        print(f"  Shape: {embedding_matrix.shape}")
        print(f"  Mean: {embedding_matrix.mean():.4f}")
        print(f"  Std: {embedding_matrix.std():.4f}")
        print(f"  Range: [{embedding_matrix.min():.4f}, {embedding_matrix.max():.4f}]")
        print()
    
    return embeddings, pipeline.detected_project_type


if __name__ == "__main__":
    # Example usage - works for both Ruby and Java projects!
    
    # Load your dataset (Ruby or Java)
    dataset_path = "/kaggle/input/thinkaurelius-titan/thinkaureliustitan_processed_rails_dataset_fixed.csv"  # Replace with your dataset path
    df = pd.read_csv(dataset_path)

    print(f"Dataset loaded: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    # Create adaptive pipeline that auto-detects project type
    pipeline = SoftwareEngineeringEmbeddingPipeline(
        embedding_model_type='codebert',  # Good for both Ruby and Java
        embedding_dim=128,
        normalize_features=True,
        random_seed=42,
        project_type='auto'  # 🔍 AUTO-DETECT! Change to 'ruby' or 'java' to force
    )

    # Generate embeddings - will automatically detect Ruby vs Java
    print("\n🚀 Generating adaptive embeddings...")
    embeddings = pipeline.get_embedding_options(df)

    # Save embeddings with project type info
    output_dir = f"adaptive_embeddings_{pipeline.detected_project_type}"
    pipeline.save_embeddings(embeddings, output_dir=output_dir)

    # Print results
    print(f"\n🎯 DETECTED PROJECT TYPE: {pipeline.detected_project_type.upper()}")
    print("\n📊 EMBEDDING RESULTS:")
    print("="*50)
    for option_name, embedding_matrix in embeddings.items():
        print(f"{option_name.upper()}:")
        print(f"  Shape: {embedding_matrix.shape}")
        print(f"  Mean: {embedding_matrix.mean():.4f}")
        print(f"  Std: {embedding_matrix.std():.4f}")
        print()

    # Your embeddings are ready!
    commit_embeddings = embeddings['commit_only']      # Commit messages only
    file_embeddings = embeddings['files_only']         # File paths only  
    combined_embeddings = embeddings['combined']       # Combined commit + files

    print(f"✅ Ready for {pipeline.detected_project_type.upper()} Test Case Prioritization!")
    print(f"🔧 Patterns optimized for {pipeline.detected_project_type} project structure")
        
    print("\n🎉 Adaptive embedding pipeline ready for Ruby AND Java projects!")