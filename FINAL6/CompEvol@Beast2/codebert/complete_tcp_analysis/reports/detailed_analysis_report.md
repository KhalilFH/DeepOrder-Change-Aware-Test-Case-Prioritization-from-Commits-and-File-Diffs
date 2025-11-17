# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| ML_basic_history_only_class_weights | 0.519 | 3.044 | 0.804 |
| ML_dual_branch_concatenated_smote | 0.457 | 3.098 | 0.801 |
| ML_dual_branch_concatenated_class_weights | 0.452 | 3.133 | 0.799 |
| Baseline_Priority_Value | 0.450 | 3.519 | 0.773 |
| ML_enhanced_concatenated_smote | 0.449 | 2.849 | 0.818 |
| ML_dual_branch_commit_only_smote | 0.447 | 2.907 | 0.814 |
| ML_dual_branch_files_only_class_weights | 0.428 | 3.201 | 0.794 |
| ML_basic_history_only_smote | 0.426 | 3.459 | 0.777 |
| ML_enhanced_commit_only_smote | 0.407 | 2.861 | 0.817 |
| ML_enhanced_combined_smote | 0.396 | 3.025 | 0.806 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (8646, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

