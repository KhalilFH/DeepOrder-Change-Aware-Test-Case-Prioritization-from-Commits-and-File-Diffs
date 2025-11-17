# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| Baseline_Priority_Value | 0.076 | 4.936 | 0.700 |
| ML_basic_history_only_class_weights | 0.066 | 4.468 | 0.750 |
| ML_dual_branch_combined_class_weights | 0.065 | 5.845 | 0.691 |
| ML_dual_branch_concatenated_class_weights | 0.041 | 3.821 | 0.781 |
| ML_basic_history_only_smote | 0.037 | 4.419 | 0.761 |
| ML_enhanced_combined_smote | 0.036 | 6.561 | 0.651 |
| ML_dual_branch_commit_only_class_weights | 0.035 | 5.271 | 0.712 |
| ML_enhanced_combined_class_weights | 0.034 | 6.297 | 0.673 |
| ML_enhanced_commit_only_class_weights | 0.026 | 7.281 | 0.617 |
| ML_dual_branch_combined_smote | 0.019 | 4.234 | 0.762 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (25272, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

