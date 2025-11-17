# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| ML_basic_history_only_class_weights | 0.519 | 3.044 | 0.804 |
| ML_dual_branch_concatenated_class_weights | 0.470 | 2.969 | 0.809 |
| ML_dual_branch_files_only_class_weights | 0.470 | 3.041 | 0.805 |
| ML_enhanced_files_only_class_weights | 0.462 | 2.810 | 0.820 |
| ML_dual_branch_files_only_smote | 0.453 | 3.016 | 0.807 |
| Baseline_Priority_Value | 0.450 | 3.519 | 0.773 |
| ML_dual_branch_commit_only_smote | 0.448 | 2.891 | 0.815 |
| ML_dual_branch_combined_smote | 0.446 | 2.878 | 0.816 |
| ML_dual_branch_commit_only_class_weights | 0.431 | 2.824 | 0.820 |
| ML_basic_history_only_smote | 0.426 | 3.459 | 0.777 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (8646, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

