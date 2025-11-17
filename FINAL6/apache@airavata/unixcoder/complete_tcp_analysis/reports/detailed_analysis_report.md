# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| ML_basic_history_only_class_weights | 0.937 | 0.374 | 0.985 |
| Baseline_Priority_Value | 0.933 | 0.411 | 0.983 |
| ML_dual_branch_files_only_class_weights | 0.933 | 0.713 | 0.971 |
| ML_basic_history_only_smote | 0.932 | 0.389 | 0.984 |
| ML_dual_branch_files_only_smote | 0.916 | 0.420 | 0.983 |
| ML_enhanced_concatenated_smote | 0.914 | 0.411 | 0.983 |
| ML_dual_branch_concatenated_smote | 0.903 | 1.453 | 0.944 |
| ML_enhanced_files_only_smote | 0.898 | 0.411 | 0.983 |
| ML_enhanced_concatenated_class_weights | 0.887 | 0.411 | 0.983 |
| ML_dual_branch_combined_smote | 0.832 | 0.411 | 0.983 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (4364, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

