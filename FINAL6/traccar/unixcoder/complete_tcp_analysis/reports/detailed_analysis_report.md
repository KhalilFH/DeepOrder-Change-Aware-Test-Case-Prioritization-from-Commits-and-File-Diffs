# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| ML_dual_branch_concatenated_class_weights | 1.000 | 1.041 | 0.966 |
| ML_enhanced_concatenated_smote | 1.000 | 1.054 | 0.970 |
| ML_enhanced_concatenated_class_weights | 1.000 | 0.778 | 0.962 |
| ML_enhanced_files_only_class_weights | 1.000 | 0.957 | 0.972 |
| ML_enhanced_files_only_smote | 1.000 | 0.771 | 0.972 |
| ML_dual_branch_files_only_class_weights | 1.000 | 0.945 | 0.971 |
| ML_dual_branch_files_only_smote | 1.000 | 1.015 | 0.971 |
| ML_dual_branch_concatenated_smote | 1.000 | 0.785 | 0.967 |
| ML_enhanced_combined_smote | 1.000 | 1.042 | 0.971 |
| ML_dual_branch_combined_smote | 1.000 | 0.833 | 0.963 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (5468, 24)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

