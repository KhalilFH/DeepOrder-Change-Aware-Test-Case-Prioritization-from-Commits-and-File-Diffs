# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| Baseline_Priority_Value | 0.245 | 1.702 | 0.794 |
| ML_dual_branch_commit_only_class_weights | 0.220 | 6.155 | 0.521 |
| ML_basic_history_only_class_weights | 0.213 | 5.651 | 0.513 |
| ML_basic_history_only_smote | 0.194 | 5.739 | 0.528 |
| ML_dual_branch_files_only_class_weights | 0.187 | 2.214 | 0.746 |
| ML_dual_branch_commit_only_smote | 0.184 | 3.860 | 0.619 |
| ML_dual_branch_concatenated_class_weights | 0.178 | 3.418 | 0.608 |
| ML_dual_branch_files_only_smote | 0.174 | 6.056 | 0.521 |
| ML_dual_branch_concatenated_smote | 0.173 | 5.734 | 0.513 |
| ML_dual_branch_combined_smote | 0.172 | 4.156 | 0.571 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (12718, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

