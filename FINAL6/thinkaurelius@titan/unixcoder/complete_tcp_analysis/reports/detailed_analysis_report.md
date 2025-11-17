# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| Baseline_Priority_Value | 0.245 | 1.702 | 0.794 |
| ML_basic_history_only_class_weights | 0.213 | 5.651 | 0.513 |
| ML_dual_branch_commit_only_class_weights | 0.201 | 6.056 | 0.522 |
| ML_basic_history_only_smote | 0.194 | 5.739 | 0.528 |
| ML_dual_branch_concatenated_class_weights | 0.191 | 4.403 | 0.583 |
| ML_dual_branch_combined_smote | 0.187 | 4.943 | 0.555 |
| ML_dual_branch_files_only_class_weights | 0.185 | 2.520 | 0.702 |
| ML_dual_branch_concatenated_smote | 0.182 | 4.684 | 0.595 |
| ML_dual_branch_combined_class_weights | 0.180 | 5.881 | 0.546 |
| ML_dual_branch_files_only_smote | 0.170 | 5.286 | 0.557 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (12718, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

