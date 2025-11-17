# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| ML_dual_branch_concatenated_smote | 0.183 | 4.138 | 0.768 |
| Baseline_Priority_Value | 0.076 | 4.936 | 0.700 |
| ML_basic_history_only_class_weights | 0.066 | 4.468 | 0.750 |
| ML_enhanced_combined_class_weights | 0.062 | 9.694 | 0.519 |
| ML_dual_branch_combined_class_weights | 0.057 | 3.157 | 0.814 |
| ML_dual_branch_commit_only_smote | 0.052 | 3.932 | 0.781 |
| ML_enhanced_commit_only_class_weights | 0.051 | 8.217 | 0.581 |
| ML_dual_branch_commit_only_class_weights | 0.050 | 5.007 | 0.723 |
| ML_dual_branch_concatenated_class_weights | 0.043 | 7.806 | 0.591 |
| ML_dual_branch_combined_smote | 0.043 | 4.780 | 0.737 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (25272, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

