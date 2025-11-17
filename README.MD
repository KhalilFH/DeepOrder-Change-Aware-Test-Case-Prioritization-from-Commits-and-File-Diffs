# Deep Learning Test Case Prioritization Framework

A deep learning framework for Test Case Prioritization (TCP) in Continuous Integration using semantic embeddings from commit messages and code changes. Implements three neural architectures with CodeBERT and UniXcoder encoders.

## Architecture Overview

**Model Types:**
- Basic: History-only (7 DeepOrder features)
- Enhanced: Early fusion (history + embeddings)
- Dual-Branch: Late fusion with separate processing

**Encoders:** CodeBERT, UniXcoder (frozen, 768-dim)  
**Validation:** Temporal forward-chaining  
**Metrics:** APFD, APFDc, TTFF, Precision@k, Recall@k  

## Prerequisites

```bash
Python 3.8+
pip install pandas numpy scikit-learn tensorflow transformers torch
pip install bugswarm  # For BugSwarm datasets
```

Set GitHub token:
```bash
export GITHUB_TOKEN='your_token_here'
```

## Dataset Preparation

### TCP-CI Projects

**Step 1: Download TCP-CI Dataset**

Download from Zenodo: https://zenodo.org/records/6415365

Extract the archive. Expected structure:
```
TCP-CI_Dataset/
├── datasets/
│   ├── apache_airavata/
│   ├── apache_curator/
│   ├── apache_rocketmq/
│   ├── CompEvol_Beast2/
│   └── ...
├── travis-torrent/
│   └── data/
└── rtp-torrent/
```

**Step 2: Generate Enhanced Schema**

Convert TCP-CI format to framework-compatible schema:

```bash
python TCP-CI_schema.py \
    --base-path /path/to/TCP-CI_Dataset \
    --project apache_curator \
    --output-dir tcp_datasets_enhanced
```

Or process all projects:
```bash
python TCP-CI_schema.py \
    --base-path /path/to/TCP-CI_Dataset \
    --output-dir tcp_datasets_enhanced
```

This generates CSV files with columns:
- Id, Name, Duration, CalcPrio, LastRun, LastResults, Verdict, Cycle
- CommitMsg, FilesChanged, BuildStartedAt, LocAdded, LocDeleted

### BugSwarm Projects (Traccar)

**Step 1: Extract BugSwarm Data**

```bash
python BugSwarm_harvester.py
```

Menu options:
1. Show projects ranked by failure rate (select Traccar or other high-failure projects)
2. Extract from specific project (enter traccar/traccar)
3. Extract from top 3 projects
4. Quick sample

For Traccar specifically:
```bash
python BugSwarm_harvester.py
# Select option 2
# Enter: traccar/traccar
# Max tests: 25000
```

Output: `traccar_traccar_high_failure_*.csv`

## Feature Engineering

**Step 3: Apply DeepOrder Feature Engineering**

Process either TCP-CI or BugSwarm datasets:

```bash
python OriginalDeepOrder-featureEngineering.py \
    --input tcp_datasets_enhanced/apache_curator_enhanced_tcp_dataset.csv \
    --output data/feature_engineered/apache_curator_processed.csv
```

This script:
- Filters tests with minimum 3 execution history
- Extracts E1, E2, E3 (last 3 outcomes)
- Calculates DIST (distance to last failure)
- Calculates CHANGE_IN_STATUS (transitions)
- Normalizes Duration
- Computes PRIORITY_VALUE (weighted failure score)
- Parses LastRun dates to calculate LastRunFeature

Output columns added:
- E1, E2, E3: Binary execution history
- DIST: Cycles since last failure
- CHANGE_IN_STATUS: Number of status transitions
- DurationFeature: Min-max normalized duration
- LastRunFeature: Normalized time since last run
- PRIORITY_VALUE: DeepOrder priority score

## Embedding Generation

**Step 4: Generate Semantic Embeddings**

```bash
python embedding_generator.py \
    --dataset data/feature_engineered/apache_curator_processed.csv \
    --encoder codebert \
    --embedding-dim 128 \
    --output embeddings/apache_curator/codebert
```

For UniXcoder:
```bash
python embedding_generator.py \
    --dataset data/feature_engineered/apache_curator_processed.csv \
    --encoder unixcoder \
    --embedding-dim 128 \
    --output embeddings/apache_curator/unixcoder
```

This generates three embedding files:
- `commit_only_embeddings.npy`: 128-dim embeddings from CommitMsg
- `files_only_embeddings.npy`: 128-dim embeddings from FilesChanged
- `combined_embeddings.npy`: 128-dim combined embeddings

Process:
1. Load frozen CodeBERT/UniXcoder (768-dim output)
2. Extract semantic features from commit messages and file paths
3. Apply PCA reduction to 128 dimensions
4. Save as .npy files

## Training and Evaluation

**Step 5: Train TCP Models**

Single configuration:
```bash
python train.py \
    --dataset data/feature_engineered/apache_curator_processed.csv \
    --embeddings embeddings/apache_curator/codebert \
    --model-type enhanced \
    --embedding-mode combined \
    --output results/apache_curator_experiment
```

Arguments:
- `--model-type`: basic, enhanced, dual_branch
- `--embedding-mode`: commit_only, files_only, combined
- `--encoder`: Automatically detected from embeddings directory

**Step 6: Comprehensive Evaluation**

Run all configurations:
```bash
python run_experiments.py \
    --project apache_curator \
    --dataset data/feature_engineered/apache_curator_processed.csv \
    --encoders codebert unixcoder \
    --output results/comprehensive_analysis
```

This evaluates:
- 3 architectures × 2 encoders × 3 embedding modes = 18 configurations
- 5 baseline methods (random, duration, recency, historical failure rate, priority value)

Output files:
- `summary.csv`: Per-configuration metrics
- `statistical_tests.csv`: Mann-Whitney U tests, bootstrap CI
- `per_cycle_apfd_matrix.csv`: APFD progression over cycles
- `visualizations/`: Performance plots

## Complete Workflow Example

Process Apache Curator from start to finish:

```bash
# 1. Download TCP-CI from Zenodo and extract

# 2. Generate schema
python TCP-CI_schema.py \
    --base-path /path/to/TCP-CI_Dataset \
    --project apache_curator \
    --output-dir tcp_datasets_enhanced

# 3. Feature engineering
python OriginalDeepOrder-featureEngineering.py \
    --input tcp_datasets_enhanced/apache_curator_enhanced_tcp_dataset.csv \
    --output data/feature_engineered/apache_curator_processed.csv

# 4. Generate embeddings (both encoders)
python embedding_generator.py \
    --dataset data/feature_engineered/apache_curator_processed.csv \
    --encoder codebert \
    --output embeddings/apache_curator/codebert

python embedding_generator.py \
    --dataset data/feature_engineered/apache_curator_processed.csv \
    --encoder unixcoder \
    --output embeddings/apache_curator/unixcoder

# 5. Comprehensive evaluation
python run_experiments.py \
    --project apache_curator \
    --dataset data/feature_engineered/apache_curator_processed.csv \
    --encoders codebert unixcoder \
    --output results/apache_curator_full_analysis
```

## Results Summary

Cross-project performance (6 Java projects evaluated):

| Project            | Failure Rate | Best Config    | APFD   | APFDc  | TTFF  |
|--------------------|--------------|----------------|--------|--------|-------|
| apache/curator     | 0.50%        | UniX-Combined  | 0.6534 | 0.7182 | 112.5 |
| apache/airavata    | 0.12%        | UniX-Combined  | 0.5145 | 0.6124 | 287.0 |
| apache/rocketmq    | 0.61%        | CodeB-Combined | 0.6783 | 0.7341 | 98.0  |
| CompEvol/Beast2    | 5.12%        | CodeB-Combined | 0.8421 | 0.8756 | 23.5  |
| thinkaurelius/titan| 18.96%       | UniX-Combined  | 0.9234 | 0.9412 | 8.2   |
| traccar/traccar    | 18.96%       | CodeB-Files    | 0.9187 | 0.9389 | 9.1   |

Key findings:
- Failure rate explains 72% of APFD variance
- Semantic embeddings provide median +0.011 APFD improvement
- UniXcoder requires 10-20× fewer training failures than CodeBERT
- Combined embeddings consistently outperform single-source

## Implementation Details

### Historical Features (7 total)

From OriginalDeepOrder-featureEngineering.py:

1. **Duration**: Min-max normalized execution time
2. **E1, E2, E3**: Last 3 execution outcomes (1=fail, 0=pass)
3. **DIST**: Cycles since last failure (0 if never failed)
4. **CHANGE_IN_STATUS**: Transitions in last 3 executions
5. **LastRunFeature**: Normalized days since last execution

### Semantic Embeddings (128-dim)

From embedding_generator.py:

- Input: CommitMsg and/or FilesChanged columns
- Encoder: Frozen CodeBERT or UniXcoder (768-dim output)
- Reduction: PCA to 128 dimensions
- Modes: commit_only, files_only, combined (concatenated)

### Neural Architectures

From robust_tcp_framework.py:

**Basic (History-only):**
```
Input(7) -> Dense(64) -> BN -> Dropout -> Dense(32) -> Dense(16) -> Sigmoid
```

**Enhanced (Early fusion):**
```
Input(135) -> Dense(128) -> BN -> Dropout -> Dense(64) -> Dense(32) -> Dense(16) -> Sigmoid
```

**Dual-Branch (Late fusion):**
```
History: Input(7) -> Dense(32) -> BN -> Dense(16)
Embedding: Input(128) -> Dense(64) -> BN -> Dense(32) -> Dense(16)
Fusion: Concat -> Dense(32) -> Dense(16) -> Sigmoid
```

Activation: Mish  
Optimizer: Adam (lr=0.001)  
Loss: Binary crossentropy  
Early stopping: 15 epochs patience  

### Temporal Validation

Strict forward-chaining:
- Train/test splits by cycle number
- No cycle overlap
- Embeddings computed using training statistics only
- No test-set leakage

Implemented in `UnifiedAdaptiveSplitter` class.

### Baseline Methods

1. **Random**: Random shuffling
2. **Duration**: Sort by execution time (faster first)
3. **Recency**: Sort by last execution time
4. **Historical Failure Rate**: Sort by failure frequency
5. **Priority Value**: DeepOrder weighted ensemble

## File Structure

```
tcp-framework/
├── TCP-CI_schema.py                     # TCP-CI dataset converter
├── BugSwarm_harvester.py                # BugSwarm data extractor
├── OriginalDeepOrder-featureEngineering.py  # Feature engineering
├── embedding_generator.py               # Semantic embedding pipeline
├── robust_tcp_framework.py              # Core TCP framework
├── train.py                             # Single experiment training
├── run_experiments.py                   # Batch evaluation
├── data/
│   └── feature_engineered/              # Processed datasets
├── embeddings/
│   └── project_name/
│       ├── codebert/
│       └── unixcoder/
└── results/                             # Experimental outputs
```



## References

- TCP-CI Dataset: https://doi.org/10.5281/zenodo.6415365
- BugSwarm: Tomassi et al. (2019). ICSE.
- CodeBERT: Feng et al. (2020). EMNLP.
- UniXcoder: Guo et al. (2022). ACL.
- DeepOrder: Spieker et al. (2017). ICST.


## Contact

Khalil Fekih Hassen  
SnT Luxembourg  
khalil.fekihhassen@medtech.tn

Supervisors: Dr. Ahmed Khanfir, Dr. Michail Papadakis