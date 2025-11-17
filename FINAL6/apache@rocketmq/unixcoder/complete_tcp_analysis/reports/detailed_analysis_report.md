# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| Baseline_Priority_Value | 0.201 | 0.743 | 0.853 |
| ML_basic_history_only_class_weights | 0.076 | 1.223 | 0.608 |
| ML_dual_branch_files_only_class_weights | 0.073 | 1.426 | 0.568 |
| ML_dual_branch_combined_class_weights | 0.042 | 1.570 | 0.370 |
| ML_basic_history_only_smote | 0.042 | 1.860 | 0.355 |
| ML_dual_branch_concatenated_class_weights | 0.040 | 1.034 | 0.600 |
| ML_enhanced_files_only_class_weights | 0.031 | 1.253 | 0.573 |
| ML_enhanced_commit_only_class_weights | 0.022 | 1.517 | 0.417 |
| ML_dual_branch_combined_smote | 0.012 | 1.685 | 0.407 |
| ML_enhanced_combined_class_weights | 0.008 | 1.457 | 0.451 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (39989, 21)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

