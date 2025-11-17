# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| Baseline_Priority_Value | 0.201 | 0.743 | 0.853 |
| ML_basic_history_only_class_weights | 0.076 | 1.223 | 0.608 |
| ML_dual_branch_concatenated_class_weights | 0.070 | 1.368 | 0.486 |
| ML_enhanced_combined_class_weights | 0.053 | 1.115 | 0.606 |
| ML_enhanced_files_only_class_weights | 0.046 | 1.144 | 0.584 |
| ML_dual_branch_files_only_class_weights | 0.045 | 1.496 | 0.491 |
| ML_basic_history_only_smote | 0.042 | 1.860 | 0.355 |
| ML_dual_branch_commit_only_class_weights | 0.041 | 1.083 | 0.611 |
| ML_enhanced_concatenated_class_weights | 0.039 | 0.963 | 0.674 |
| ML_dual_branch_combined_class_weights | 0.033 | 1.597 | 0.356 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (39989, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

